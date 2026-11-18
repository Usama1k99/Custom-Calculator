import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
import sys

from src.core.updater import is_connected_to_internet, VersionCheckWorker, BuildsFetchWorker
from src.ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)

class TestUpdaterOffline(unittest.TestCase):

    def test_is_connected_to_internet_success(self):
        # Online mock
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value = unittest.mock.MagicMock()
            self.assertTrue(is_connected_to_internet())

    def test_is_connected_to_internet_failure(self):
        # Offline mock
        with patch("socket.create_connection", side_effect=OSError("Network unreachable")):
            self.assertFalse(is_connected_to_internet())

    def test_version_check_worker_offline(self):
        with patch("src.core.updater.is_connected_to_internet", return_value=False):
            worker = VersionCheckWorker()
            results = []
            worker.checkCompleted.connect(lambda avail, info: results.append((avail, info)))
            worker.run()
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0][0])
            self.assertTrue(results[0][1].get("is_offline"))

    def test_builds_fetch_worker_offline(self):
        with patch("src.core.updater.is_connected_to_internet", return_value=False):
            worker = BuildsFetchWorker()
            results = []
            worker.buildsFetched.connect(lambda rels: results.append(rels))
            worker.run()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0], [])

    def test_rate_limit_atom_fallback(self):
        from src.core.updater import fetch_all_releases
        import urllib.error

        atom_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Custom Calculator v0.7.0</title>
    <updated>2026-11-18T14:36:53Z</updated>
    <link href="https://github.com/Usama1k99/Custom-Calculator/releases/tag/v0.7.0"/>
    <content>Release notes</content>
  </entry>
</feed>"""

        def mock_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "api.github.com" in url:
                raise urllib.error.HTTPError(url, 403, "rate limit exceeded", {}, None)
            elif "releases.atom" in url:
                class MockResp:
                    def read(self):
                        return atom_xml
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        pass
                return MockResp()
            raise urllib.error.URLError("Not found")

        with patch("src.core.updater.is_connected_to_internet", return_value=True), \
             patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            rels = fetch_all_releases()
            self.assertEqual(len(rels), 1)
            self.assertEqual(rels[0]["tag_name"], "v0.7.0")

    def test_all_remote_fail_catalog_fallback(self):
        from src.core.updater import fetch_all_releases
        import urllib.error

        with patch("src.core.updater.is_connected_to_internet", return_value=True), \
             patch("src.core.updater.urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 403, "rate limit", {}, None)):
            rels = fetch_all_releases()
            # Falls back to OFFICIAL_KNOWN_RELEASES
            self.assertGreaterEqual(len(rels), 3)
            tags = [r["tag_name"] for r in rels]
            self.assertIn("v0.7.0", tags)
            self.assertIn("v0.6.0", tags)
            self.assertIn("v0.5.0", tags)

if __name__ == "__main__":
    unittest.main()
