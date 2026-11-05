"""
Update Manager for Custom-Calculator.
Handles GitHub releases lookup, release binary download, and detached process self-update.
Zero external dependencies (uses standard library urllib and subprocess).
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from src.version import APP_VERSION, BUILD_COMMIT, GITHUB_API_URL


class VersionCheckWorker(QThread):
    checkCompleted = pyqtSignal(bool, dict)  # (update_available, latest_release_info)

    def run(self):
        try:
            req = urllib.request.Request(
                f"{GITHUB_API_URL}/releases",
                headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                    tag = latest.get("tag_name", "").lstrip("v")
                    # Compare version
                    if tag and tag != APP_VERSION:
                        self.checkCompleted.emit(True, latest)
                        return
                    # Or check commit
                    sha = latest.get("target_commitish", "")[:7]
                    if sha and sha != BUILD_COMMIT and not BUILD_COMMIT.startswith(sha):
                        self.checkCompleted.emit(True, latest)
                        return
        except Exception:
            pass

        self.checkCompleted.emit(False, {})


class BinaryDownloadWorker(QThread):
    progress = pyqtSignal(int)      # percentage
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


def is_license_entry(item: Dict[str, Any]) -> bool:
    """Checks whether a release or commit is a license-related entry."""
    tag = str(item.get("tag_name", "")).lower()
    name = str(item.get("name", "")).lower()
    body = str(item.get("body", "")).lower()
    commit_info = item.get("commit", {})
    msg = str(commit_info.get("message", "")).lower() if isinstance(commit_info, dict) else ""
    text = f"{tag} {name} {body} {msg}"
    return "license" in text or "licence" in text


def fetch_all_releases() -> List[Dict[str, Any]]:
    """
    Synchronously fetches all releases from GitHub for the build browser.
    Excludes any license-related commits or releases.
    """
    releases: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(
            f"{GITHUB_API_URL}/releases?per_page=30",
            headers={"User-Agent": f"CustomCalculator/{APP_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                releases = [rel for rel in data if not is_license_entry(rel)]
    except Exception:
        pass
    return releases


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

