"""
Update Manager for Custom-Calculator.
Handles GitHub releases lookup, live commit build detection, release binary download,
and detached process self-update.
Zero external dependencies (uses standard library urllib and subprocess).
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from src.version import APP_VERSION, BUILD_COMMIT, GITHUB_API_URL


def parse_semver(v_str: str) -> tuple:
    """Parses a version string like 'v0.2.1', '0.2.0', or '0.2.2-alpha' into a comparable tuple."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(v_str))
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))
    return (0, 0, 0)


def is_license_entry(item: Dict[str, Any]) -> bool:
    """Checks whether a release or commit is a license-related entry."""
    tag = str(item.get("tag_name", "")).lower()
    name = str(item.get("name", "")).lower()
    body = str(item.get("body", "")).lower()
    commit_info = item.get("commit", {})
    msg = str(commit_info.get("message", "")).lower() if isinstance(commit_info, dict) else ""
    text = f"{tag} {name} {body} {msg}"
    if "license" in text or "licence" in text:
        return True
    if msg.strip() in ("initial commit", "license", "licence"):
        return True
    return False


class VersionCheckWorker(QThread):
    checkCompleted = pyqtSignal(bool, dict)  # (update_available, latest_release_info)

    def run(self):
        # 1. Primary check: GitHub Releases API
        try:
            req = urllib.request.Request(
                f"{GITHUB_API_URL}/releases",
                headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    valid_rels = [r for r in data if not is_license_entry(r)]
                    if valid_rels:
                        latest = valid_rels[0]
                        tag = latest.get("tag_name", "").lstrip("v")
                        if parse_semver(tag) > parse_semver(APP_VERSION):
                            self.checkCompleted.emit(True, latest)
                            return
                        sha = latest.get("target_commitish", "")[:7]
                        if sha and sha != BUILD_COMMIT and not BUILD_COMMIT.startswith(sha):
                            self.checkCompleted.emit(True, latest)
                            return
        except Exception:
            pass

        # 2. Live fallback check: GitHub Commits API
        try:
            req = urllib.request.Request(
                f"{GITHUB_API_URL}/commits?per_page=30",
                headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    valid_commits = [c for c in data if not is_license_entry(c)]
                    if valid_commits:
                        latest_c = valid_commits[0]
                        msg = latest_c.get("commit", {}).get("message", "")
                        first_line = msg.splitlines()[0] if msg else ""
                        m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", first_line)
                        tag_ver = m.group(1) if m else ""
                        sha = latest_c.get("sha", "")[:7]

                        is_newer = False
                        if tag_ver and parse_semver(tag_ver) > parse_semver(APP_VERSION):
                            is_newer = True
                        elif sha and sha != BUILD_COMMIT and not BUILD_COMMIT.startswith(sha):
                            is_newer = True

                        if is_newer:
                            synth = {
                                "tag_name": f"v{tag_ver}" if tag_ver else f"Commit {sha}",
                                "name": first_line,
                                "body": msg,
                                "published_at": latest_c.get("commit", {}).get("committer", {}).get("date", ""),
                                "target_commitish": sha,
                                "html_url": latest_c.get("html_url", ""),
                                "assets": [],
                                "is_commit_build": True
                            }
                            self.checkCompleted.emit(True, synth)
                            return
        except Exception:
            pass

        self.checkCompleted.emit(False, {})


class BinaryDownloadWorker(QThread):
    progress = pyqtSignal(int)       # percentage
    finished = pyqtSignal(bool, str) # success, file_path_or_error

    def __init__(self, download_url: str, output_path: str):
        super().__init__()
        self.download_url = download_url
        self.output_path = output_path

    def run(self):
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "CustomCalculator-Updater"}
            )
            with urllib.request.urlopen(req, timeout=30.0) as response, open(self.output_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        self.progress.emit(pct)

            self.finished.emit(True, self.output_path)
        except Exception as e:
            self.finished.emit(False, str(e))


def fetch_all_releases() -> List[Dict[str, Any]]:
    """
    Synchronously fetches all releases from GitHub for the build browser.
    Falls back to and merges GitHub commits so builds are visible live even
    before standalone binaries or formal GitHub Releases are tagged.
    Excludes any license-related commits or releases.
    """
    releases: List[Dict[str, Any]] = []
    seen_versions = set()

    # 1. Primary: GitHub Releases
    try:
        req = urllib.request.Request(
            f"{GITHUB_API_URL}/releases?per_page=30",
            headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                for rel in data:
                    if is_license_entry(rel):
                        continue
                    tag = rel.get("tag_name", "").lstrip("v")
                    if tag:
                        seen_versions.add(tag)
                    rel["is_commit_build"] = False
                    releases.append(rel)
    except Exception:
        pass

    # 2. Live Commits fallback / supplemental
    try:
        req = urllib.request.Request(
            f"{GITHUB_API_URL}/commits?per_page=30",
            headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                for c in data:
                    if is_license_entry(c):
                        continue
                    msg = c.get("commit", {}).get("message", "")
                    first_line = msg.splitlines()[0] if msg else ""
                    m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", first_line)
                    tag_ver = m.group(1) if m else ""
                    sha = c.get("sha", "")[:7]

                    # If this version is already covered by a formal release, skip duplicating
                    if tag_ver and tag_ver in seen_versions:
                        continue
                    if tag_ver:
                        seen_versions.add(tag_ver)

                    synth_rel = {
                        "tag_name": f"v{tag_ver}" if tag_ver else f"Commit {sha}",
                        "name": first_line,
                        "body": msg,
                        "published_at": c.get("commit", {}).get("committer", {}).get("date", ""),
                        "target_commitish": sha,
                        "html_url": c.get("html_url", ""),
                        "assets": [],
                        "is_commit_build": True
                    }
                    releases.append(synth_rel)
    except Exception:
        pass

    return releases


class BuildsFetchWorker(QThread):
    buildsFetched = pyqtSignal(list)

    def run(self):
        releases = fetch_all_releases()
        self.buildsFetched.emit(releases)


def apply_update_and_restart(new_exe_path: str):
    """
    Bypasses Windows file locking by spawning a detached batch script
    that replaces the active binary and restarts it.
    """
    current_exe = sys.executable

    # If running from source (python main.py), don't replace python.exe!
    if not getattr(sys, "frozen", False):
        print(f"[Dev Mode] Downloaded update to: {new_exe_path}")
        return

    batch_content = f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    batch_path = Path(tempfile.gettempdir()) / "custom_calc_update.bat"
    with open(batch_path, "w") as f:
        f.write(batch_content)

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", str(batch_path)],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True
    )
    sys.exit(0)
