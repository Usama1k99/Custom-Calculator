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

if __name__ == "__main__":
    unittest.main()
