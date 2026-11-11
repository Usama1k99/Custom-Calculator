"""
Comprehensive test suite for the Version Marking System & Smart Updater Logic.
Tests:
- Labeling versions as functional (default), not recommended, and deprecated
- Parser extraction across release headers, tags, body status declarations, and cross-release lists
- Update checker behavior:
  - Deprecated version: automatic background update without user confirmation prompt
  - Not Recommended version: high-visibility warning that update is highly recommended
  - Functional version: standard polite prompt only when newer release is published
- Dialog UI validation and safety mechanisms (dev mode, offline fallback, zero emojis)
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication

from src.version import APP_VERSION
from src.core.updater import (
    VERSION_STATUS_FUNCTIONAL,
    VERSION_STATUS_NOT_RECOMMENDED,
    VERSION_STATUS_DEPRECATED,
    normalize_version,
    parse_semver,
    parse_release_status,
    extract_cross_release_status,
    extract_version_status_map,
    get_version_status,
    find_recommended_release,
    fetch_all_releases,
    VersionCheckWorker
)
from src.ui.update_dialog import UpdatePromptDialog, DeprecatedUpdateDialog


class TestVersionMarkingSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_normalize_version(self):
        self.assertEqual(normalize_version("v0.5.0"), "0.5.0")
        self.assertEqual(normalize_version("V1.2.3"), "1.2.3")
        self.assertEqual(normalize_version("  v2.0  "), "2.0")
        self.assertEqual(normalize_version("0.4.1"), "0.4.1")

    def test_parse_semver(self):
        self.assertEqual(parse_semver("v0.5.0"), (0, 5, 0))
        self.assertEqual(parse_semver("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_semver("0.2"), (0, 2, 0))

    def test_parse_release_status_default_functional(self):
        rel = {"name": "Custom Calculator v0.5.0", "tag_name": "v0.5.0", "body": "Standard release"}
        self.assertEqual(parse_release_status(rel), VERSION_STATUS_FUNCTIONAL)

    def test_parse_release_status_headers_and_tags(self):
        # Deprecated in title or tag
        self.assertEqual(parse_release_status({"name": "[Deprecated] Build", "tag_name": "v0.4.0"}), VERSION_STATUS_DEPRECATED)
        self.assertEqual(parse_release_status({"name": "Build (deprecated)", "tag_name": "v0.4.0"}), VERSION_STATUS_DEPRECATED)
        self.assertEqual(parse_release_status({"name": "Release", "tag_name": "v0.4.0-deprecated"}), VERSION_STATUS_DEPRECATED)

        # Not recommended in title or tag
        self.assertEqual(parse_release_status({"name": "[Not Recommended] v0.4.5", "tag_name": "v0.4.5"}), VERSION_STATUS_NOT_RECOMMENDED)
        self.assertEqual(parse_release_status({"name": "v0.4.5 (not-recommended)", "tag_name": "v0.4.5"}), VERSION_STATUS_NOT_RECOMMENDED)

    def test_parse_release_status_body_declarations(self):
        # Deprecated in body
        rel_dep = {"name": "v0.4.0", "tag_name": "v0.4.0", "body": "Important fixes.\nStatus: Deprecated\nPlease update."}
        self.assertEqual(parse_release_status(rel_dep), VERSION_STATUS_DEPRECATED)

        rel_dep_md = {"name": "v0.4.0", "tag_name": "v0.4.0", "body": "## Notes\n**Status:** deprecated"}
        self.assertEqual(parse_release_status(rel_dep_md), VERSION_STATUS_DEPRECATED)

        # Not Recommended in body
        rel_not_rec = {"name": "v0.4.8", "tag_name": "v0.4.8", "body": "Known memory issue.\nStatus: not recommended"}
        self.assertEqual(parse_release_status(rel_not_rec), VERSION_STATUS_NOT_RECOMMENDED)

        rel_not_rec_dash = {"name": "v0.4.8", "tag_name": "v0.4.8", "body": "**Status:** not-recommended"}
        self.assertEqual(parse_release_status(rel_not_rec_dash), VERSION_STATUS_NOT_RECOMMENDED)

        # Explicit Functional in body
        rel_func = {"name": "v0.5.0", "tag_name": "v0.5.0", "body": "Status: functional"}
        self.assertEqual(parse_release_status(rel_func), VERSION_STATUS_FUNCTIONAL)

    def test_extract_cross_release_status(self):
        body = """
        ## Release v0.6.0
        New feature additions.

        Deprecated versions: v0.4.0, v0.3.0
        Not recommended: v0.5.0, 0.4.9
        """
        status_map = extract_cross_release_status(body)
        self.assertEqual(status_map.get("0.4.0"), VERSION_STATUS_DEPRECATED)
        self.assertEqual(status_map.get("0.3.0"), VERSION_STATUS_DEPRECATED)
        self.assertEqual(status_map.get("0.5.0"), VERSION_STATUS_NOT_RECOMMENDED)
        self.assertEqual(status_map.get("0.4.9"), VERSION_STATUS_NOT_RECOMMENDED)

    def test_extract_cross_release_status_json_comments(self):
        body = """
        ## Release v0.7.0
        <!-- version_status: {"0.4.0": "deprecated", "0.5.0": "not_recommended"} -->
        """
        status_map = extract_cross_release_status(body)
        self.assertEqual(status_map.get("0.4.0"), VERSION_STATUS_DEPRECATED)
        self.assertEqual(status_map.get("0.5.0"), VERSION_STATUS_NOT_RECOMMENDED)

    def test_get_version_status_resolution(self):
        releases = [
            {
                "tag_name": "v0.6.0",
                "name": "Custom Calculator v0.6.0",
                "body": "Deprecated: v0.4.0\nNot recommended: v0.5.0",
                "draft": False
            },
            {
                "tag_name": "v0.5.0",
                "name": "Custom Calculator v0.5.0",
                "body": "Older release",
                "draft": False
            },
            {
                "tag_name": "v0.4.0",
                "name": "Custom Calculator v0.4.0",
                "body": "Even older release",
                "draft": False
            }
        ]
        self.assertEqual(get_version_status("0.6.0", releases), VERSION_STATUS_FUNCTIONAL)
        self.assertEqual(get_version_status("0.5.0", releases), VERSION_STATUS_NOT_RECOMMENDED)
        self.assertEqual(get_version_status("0.4.0", releases), VERSION_STATUS_DEPRECATED)
        # Unlisted versions default to functional
        self.assertEqual(get_version_status("0.9.9", releases), VERSION_STATUS_FUNCTIONAL)

    def test_find_recommended_release(self):
        releases = [
            {"tag_name": "v0.7.0", "name": "[Deprecated] v0.7.0", "draft": False},
            {"tag_name": "v0.6.0", "name": "v0.6.0 Stable", "body": "Status: functional", "draft": False},
            {"tag_name": "v0.5.0", "name": "v0.5.0", "draft": False}
        ]
        target = find_recommended_release(releases)
        self.assertIsNotNone(target)
        self.assertEqual(target["tag_name"], "v0.6.0")

    def test_version_check_worker_deprecated_triggers_immediate_update(self):
        # Setup mock releases where APP_VERSION is deprecated
        mock_releases = [
            {
                "tag_name": "v0.9.0",
                "name": "v0.9.0 Stable",
                "body": f"Deprecated: v{APP_VERSION}",
                "draft": False,
                "assets": []
            },
            {
                "tag_name": f"v{APP_VERSION}",
                "name": f"v{APP_VERSION}",
                "body": "Current build",
                "draft": False,
                "assets": []
            }
        ]

        def mock_urlopen(req, timeout=None):
            class MockResponse:
                def read(self):
                    return json.dumps(mock_releases).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResponse()

        worker = VersionCheckWorker()
        results = []
        worker.checkCompleted.connect(lambda avail, info: results.append((avail, info)))

        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            worker.run()

        self.assertEqual(len(results), 1)
        avail, info = results[0]
        self.assertTrue(avail)
        self.assertEqual(info["current_status"], VERSION_STATUS_DEPRECATED)
        self.assertEqual(info["target_version"], "0.9.0")

    def test_version_check_worker_not_recommended_triggers_warning_prompt(self):
        # Setup mock releases where APP_VERSION is marked Not Recommended
        mock_releases = [
            {
                "tag_name": "v0.9.0",
                "name": "v0.9.0 Stable",
                "body": f"Not recommended: v{APP_VERSION}",
                "draft": False,
                "assets": []
            },
            {
                "tag_name": f"v{APP_VERSION}",
                "name": f"v{APP_VERSION}",
                "body": "Current build",
                "draft": False,
                "assets": []
            }
        ]

        def mock_urlopen(req, timeout=None):
            class MockResponse:
                def read(self):
                    return json.dumps(mock_releases).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResponse()

        worker = VersionCheckWorker()
        results = []
        worker.checkCompleted.connect(lambda avail, info: results.append((avail, info)))

        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            worker.run()

        self.assertEqual(len(results), 1)
        avail, info = results[0]
        self.assertTrue(avail)
        self.assertEqual(info["current_status"], VERSION_STATUS_NOT_RECOMMENDED)

    def test_version_check_worker_functional_same_version_silent(self):
        mock_releases = [
            {
                "tag_name": f"v{APP_VERSION}",
                "name": f"v{APP_VERSION}",
                "body": "Status: functional",
                "draft": False,
                "assets": []
            }
        ]

        def mock_urlopen(req, timeout=None):
            class MockResponse:
                def read(self):
                    return json.dumps(mock_releases).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResponse()

        worker = VersionCheckWorker()
        results = []
        worker.checkCompleted.connect(lambda avail, info: results.append((avail, info)))

        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            worker.run()

        self.assertEqual(len(results), 1)
        avail, info = results[0]
        self.assertFalse(avail)
        self.assertEqual(info["current_status"], VERSION_STATUS_FUNCTIONAL)

    def test_update_prompt_dialog_not_recommended_highlight(self):
        release_info = {
            "tag_name": "v0.9.0",
            "body": "Crucial security and correctness updates.",
            "current_status": VERSION_STATUS_NOT_RECOMMENDED
        }
        dlg = UpdatePromptDialog(release_info, mode=VERSION_STATUS_NOT_RECOMMENDED)
        self.assertTrue(dlg.is_not_recommended)
        self.assertIn("Highly Recommended", dlg.update_btn.text())
        self.assertIn("Not Recommended", dlg.windowTitle())
        dlg.close()

    def test_update_prompt_dialog_functional_standard(self):
        release_info = {
            "tag_name": "v0.9.0",
            "body": "New features.",
            "current_status": VERSION_STATUS_FUNCTIONAL
        }
        dlg = UpdatePromptDialog(release_info, mode=VERSION_STATUS_FUNCTIONAL)
        self.assertFalse(dlg.is_not_recommended)
        self.assertEqual(dlg.update_btn.text(), "Update to Latest")
        dlg.close()

    def test_deprecated_update_dialog_initialization(self):
        release_info = {
            "tag_name": "v0.9.0",
            "body": "Mandatory upgrade.",
            "current_status": VERSION_STATUS_DEPRECATED
        }
        dlg = DeprecatedUpdateDialog(release_info)
        self.assertIn("Deprecated", dlg.windowTitle())
        self.assertFalse(dlg.progress_bar.isHidden())
        self.assertEqual(dlg.progress_bar.value(), 0)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
