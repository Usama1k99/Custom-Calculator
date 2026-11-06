"""
Direct GitHub Release Publisher.
Publishes a compiled standalone CustomCalculator.exe binary to GitHub Releases API.

Usage:
    python scripts/publish_release.py [GITHUB_TOKEN]
"""

import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error
from src.version import APP_VERSION, GITHUB_REPO, GITHUB_API_URL


def is_major_minor_release(version: str) -> bool:
    """Checks if the version is a major/minor release (last number / patch is 0)."""
    parts = version.lstrip("v").split(".")
    if len(parts) >= 3:
        return parts[2] == "0"
    return False


def publish(token: str) -> bool:
    if not is_major_minor_release(APP_VERSION):
        print(f"Skipping GitHub Release creation for patch version v{APP_VERSION}. Releases are only created for major/minor updates (*.*.0).")
        return True

    exe_path = Path("dist/CustomCalculator.exe")
    if not exe_path.exists():
        print("dist/CustomCalculator.exe not found! Please build the executable before publishing.")
        return False

    tag_name = f"v{APP_VERSION}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"CustomCalculator-ReleasePublisher/{APP_VERSION}"
    }

    # 1. Create or get existing release
    release_id = None
    upload_url = None
    try:
        req = urllib.request.Request(
            f"{GITHUB_API_URL}/releases/tags/{tag_name}",
            headers=headers
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            release_id = data.get("id")
            upload_url = data.get("upload_url", "").split("{")[0]
            print(f"Found existing GitHub Release {tag_name} (ID: {release_id}).")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Creating new GitHub Release for {tag_name}...")
            create_payload = json.dumps({
                "tag_name": tag_name,
                "name": f"Custom Calculator {tag_name}",
                "body": f"Official standalone release binary for Custom Calculator {tag_name}.\n\nDownload `CustomCalculator.exe` below to run immediately on Windows with zero setup.",
                "draft": False,
                "prerelease": False
            }).encode("utf-8")
            create_req = urllib.request.Request(
                f"{GITHUB_API_URL}/releases",
                data=create_payload,
                headers={**headers, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(create_req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                release_id = data.get("id")
                upload_url = data.get("upload_url", "").split("{")[0]
                print(f"Successfully created GitHub Release {tag_name} (ID: {release_id})!")
        else:
            print(f"Failed to query GitHub Releases API: {e}")
            return False

    if not upload_url:
        print("Could not obtain upload URL from GitHub Releases API.")
        return False

    # 2. Upload CustomCalculator.exe asset
    print(f"Uploading {exe_path} ({exe_path.stat().st_size // (1024 * 1024)} MB) to GitHub Release...")
    upload_target = f"{upload_url}?name=CustomCalculator.exe"
    file_bytes = exe_path.read_bytes()

    upload_req = urllib.request.Request(
        upload_target,
        data=file_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.microsoft.portable-executable",
            "Content-Length": str(len(file_bytes)),
            "User-Agent": f"CustomCalculator-ReleasePublisher/{APP_VERSION}"
        }
    )

    try:
        with urllib.request.urlopen(upload_req) as resp:
            asset_data = json.loads(resp.read().decode("utf-8"))
            print(f"Upload successful! Asset URL: {asset_data.get('browser_download_url')}")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print("Asset 'CustomCalculator.exe' is already uploaded to this release.")
            return True
        print(f"Failed to upload asset: {e}")
        return False


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not token:
        print("Usage: python scripts/publish_release.py <GITHUB_TOKEN>")
        print("Alternatively, set the GITHUB_TOKEN environment variable.")
        sys.exit(1)
    success = publish(token)
    sys.exit(0 if success else 1)
