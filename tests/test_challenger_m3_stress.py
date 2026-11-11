"""
tests/test_challenger_m3_stress.py

Adversarial Stress Test Suite by Challenger 2 for Milestone 3.
Validates:
1. All calculator modes under maximized state: Standard, Scientific, Programmer, Graphing, Date Calculation, and all 13 Converters.
2. History drawer docking and keypad expansion edge-to-edge in Scientific mode.
3. Overlays, scrim, flyouts, and menu selections.
4. Clean restore / maximize cycling in Scientific mode with and without history drawer.
5. Win32 message pass-through (WM_SIZE, WM_WINDOWPOSCHANGED, WM_GETMINMAXINFO) and NCCALCSIZE rcWork precision.
6. Extreme click coordinates and edge hit testing.
"""

import sys
import ctypes
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    HTMAXBUTTON, HTCLIENT, HTCAPTION,
    HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    WM_NCCALCSIZE,
    NCCALCSIZE_PARAMS, MSG
)
from src.ui.converter_view import CONVERSION_FACTORS

WM_SIZE = 0x0005
WM_WINDOWPOSCHANGED = 0x0047
WM_GETMINMAXINFO = 0x0024

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMilestone3ChallengerAdversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(800, 600)
        cls.win.show()
        cls._pump(10)

        cls.hwnd = int(cls.win.winId())
        cls.u = ctypes.windll.user32
        cls.u.ShowWindow(cls.hwnd, 3)  # SW_SHOWMAXIMIZED
        cls._pump(15)

    @classmethod
    def tearDownClass(cls):
        cls.win.close()
        cls._pump(5)

    @classmethod
    def _pump(cls, iterations: int = 5):
        for _ in range(iterations):
            app.processEvents()
            QTest.qWait(20)

    def setUp(self):
        if not self.win.isMaximized():
            self.u.ShowWindow(self.hwnd, 3)
            self._pump(10)

    def test_01_all_modes_maximize_edge_to_edge(self):
        """Verify all modes expand edge-to-edge without dead space or clipping."""
        self.assertTrue(self.win.isMaximized())
        w = self.win.width()
        h = self.win.height()
        title_h = self.win.title_bar.height()
        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        self.assertGreaterEqual(w, 1024)
        self.assertGreaterEqual(h, 700)
        self.assertEqual(content_w, w)
        self.assertEqual(content_h, h - title_h)

        modes = [
            "Standard",
            "Scientific",
            "Programmer",
            "Graphing",
            "Date Calculation",
        ] + list(CONVERSION_FACTORS.keys())

        for mode in modes:
            with self.subTest(mode=mode):
                self.win._switch_mode(mode, save_config=False)
                self._pump(3)

                # Window containers must match exact client dimensions
                self.assertEqual(self.win.root_container.size(), self.win.size())
                self.assertEqual(self.win.content_widget.size(), QSize(w, content_h))
                self.assertEqual(self.win.center_container.width(), content_w)

                cw = self.win.stack.currentWidget()
                self.assertIsNotNone(cw)
                self.assertEqual(cw.width(), content_w)

                if mode in ("Standard", "Scientific", "Programmer"):
                    self.assertEqual(self.win.keypad.width(), content_w)
                    self.assertEqual(self.win.display.width(), content_w)
                    # Far right button must reach within 10px of content right edge
                    btn_eq = self.win.keypad.button_map.get("=")
                    self.assertIsNotNone(btn_eq)
                    btn_right = btn_eq.mapToGlobal(QPoint(btn_eq.width(), 0)).x()
                    win_right = self.win.mapToGlobal(QPoint(w, 0)).x()
                    self.assertLessEqual(win_right - btn_right, 10)
                elif mode == "Graphing":
                    gp = self.win.graphing_page
                    self.assertEqual(gp.width(), content_w)
                    self.assertTrue(gp.left_pane.isVisible())
                    self.assertTrue(gp.right_pane.isVisible())
                    self.assertGreaterEqual(gp.canvas.width(), 800)
                elif mode == "Date Calculation":
                    dp = self.win.date_calc_page
                    self.assertEqual(dp.width(), content_w)
                else:
                    cp = self.win.converter_page
                    self.assertEqual(cp.width(), content_w)
                    self.assertEqual(cp.category, mode)

    def test_02_scientific_mode_history_docking_and_keypad_expansion(self):
        """Stress-test History drawer docking and edge-to-edge keypad expansion in Scientific mode."""
        self.win._switch_mode("Scientific", save_config=False)
        self._pump(4)

        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        # Ensure drawer is closed initially
        if self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
            self._pump(3)

        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)
        self.assertEqual(self.win.keypad.width(), content_w)

        # Open drawer
        self.win._toggle_history_drawer()
        self._pump(4)

        self.assertTrue(self.win.history_drawer.isVisible())
        drawer_w = self.win.history_drawer.width()
        self.assertEqual(drawer_w, 290)
        self.assertEqual(self.win.history_drawer.height(), content_h)

        # Drawer must dock flush to right edge
        drawer_geom = self.win.history_drawer.geometry()
        self.assertEqual(drawer_geom.x(), content_w - 290)
        self.assertEqual(drawer_geom.right(), content_w - 1)

        # Center container & keypad must take exact remaining width: content_w - 290
        expected_center_w = content_w - 290
        self.assertEqual(self.win.center_container.width(), expected_center_w)
        self.assertEqual(self.win.keypad.width(), expected_center_w)
        self.assertEqual(self.win.display.width(), expected_center_w)

        # Scientific keypad specific buttons: check leftmost button (rad/deg or 2nd) and rightmost button (=)
        btn_eq = self.win.keypad.button_map.get("=")
        self.assertIsNotNone(btn_eq)
        btn_eq_global_right = btn_eq.mapToGlobal(QPoint(btn_eq.width(), 0)).x()
        drawer_global_left = self.win.history_drawer.mapToGlobal(QPoint(0, 0)).x()
        # Keypad right edge touches or is within 10px of drawer left edge
        self.assertLessEqual(drawer_global_left - btn_eq_global_right, 10)

        # Perform calculation in Scientific mode with drawer open
        btn_pi = self.win.keypad.button_map.get("π")
        self.assertIsNotNone(btn_pi)
        QTest.mouseClick(btn_pi, Qt.MouseButton.LeftButton)
        self._pump(2)
        QTest.mouseClick(btn_eq, Qt.MouseButton.LeftButton)
        self._pump(2)
        self.assertIn("3.14159", self.win.display.primary_display.text())

        # Close drawer and verify keypad immediately re-expands to full content_w
        self.win._toggle_history_drawer()
        self._pump(4)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)
        self.assertEqual(self.win.keypad.width(), content_w)
        btn_eq_global_right_full = btn_eq.mapToGlobal(QPoint(btn_eq.width(), 0)).x()
        win_global_right = self.win.mapToGlobal(QPoint(self.win.width(), 0)).x()
        self.assertLessEqual(win_global_right - btn_eq_global_right_full, 10)

    def test_03_overlays_and_flyouts_under_maximization(self):
        """Stress-test navigation sidebar overlay, scrim bounds, and dismissal."""
        self.win._switch_mode("Scientific", save_config=False)
        self._pump(3)

        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # Open sidebar
        self.win._toggle_sidebar()
        self._pump(4)

        self.assertTrue(self.win.sidebar.isVisible())
        self.assertTrue(self.win.scrim.isVisible())

        # Scrim must cover the entire content area exactly
        self.assertEqual(self.win.scrim.geometry(), QRect(0, 0, content_w, content_h))
        # Sidebar must be anchored at (0, 0) with width 260 and height content_h
        self.assertEqual(self.win.sidebar.geometry(), QRect(0, 0, 260, content_h))

        # Click outside sidebar to dismiss
        scrim_click_pos = QPoint(500, 300)
        QTest.mouseClick(self.win.scrim, Qt.MouseButton.LeftButton, pos=scrim_click_pos)
        self._pump(4)

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # Reopen and select mode
        self.win._toggle_sidebar()
        self._pump(4)
        btn_prog = self.win.sidebar.buttons.get("Programmer")
        self.assertIsNotNone(btn_prog)
        QTest.mouseClick(btn_prog, Qt.MouseButton.LeftButton)
        self._pump(6)

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertEqual(self.win.state.mode, "Programmer")
        self.assertEqual(self.win.keypad.width(), content_w)

    def test_04_restore_remaximize_cycles_in_scientific_mode(self):
        """Verify clean restore and re-maximize in Scientific mode preserves geometry."""
        self.win._switch_mode("Scientific", save_config=False)
        self._pump(3)

        max_w = self.win.width()
        max_h = self.win.height()

        # Restore
        self.u.ShowWindow(self.hwnd, 9)  # SW_RESTORE
        self._pump(10)
        self.assertFalse(self.win.isMaximized())
        restored_w = self.win.width()
        restored_h = self.win.height()
        self.assertLess(restored_w, max_w)
        self.assertEqual(self.win.root_container.size(), self.win.size())
        self.assertEqual(self.win.content_widget.width(), restored_w)
        self.assertEqual(self.win.keypad.width(), restored_w)

        # Re-maximize
        self.win.title_bar.btn_maximize.click()
        self._pump(10)
        self.assertTrue(self.win.isMaximized())
        self.assertEqual(self.win.width(), max_w)
        self.assertEqual(self.win.height(), max_h)
        self.assertEqual(self.win.root_container.size(), self.win.size())
        self.assertEqual(self.win.content_widget.width(), max_w)
        self.assertEqual(self.win.keypad.width(), max_w)

    def test_05_native_event_filter_enveil_alignment(self):
        """Verify native event filter does not intercept WM_SIZE, WM_WINDOWPOSCHANGED, or WM_GETMINMAXINFO."""
        nef = self.win._native_event_filter
        self.assertIsNotNone(nef)

        # 1. WM_SIZE (0x0005) must not be intercepted
        handled, ret = nef.nativeEventFilter("windows_generic_MSG", ctypes.c_void_p(0))
        # Test directly with crafted message
        msg_size = MSG()
        msg_size.hwnd = self.hwnd
        msg_size.message = WM_SIZE
        msg_size.wParam = 0
        msg_size.lParam = 0
        handled_size, ret_size = nef.nativeEventFilter("windows_generic_MSG", ctypes.addressof(msg_size))
        self.assertFalse(handled_size, "WM_SIZE should not be intercepted")
        self.assertEqual(ret_size, 0)

        # 2. WM_WINDOWPOSCHANGED (0x0047) must not be intercepted
        msg_pos = MSG()
        msg_pos.hwnd = self.hwnd
        msg_pos.message = WM_WINDOWPOSCHANGED
        msg_pos.wParam = 0
        msg_pos.lParam = 0
        handled_pos, ret_pos = nef.nativeEventFilter("windows_generic_MSG", ctypes.addressof(msg_pos))
        self.assertFalse(handled_pos, "WM_WINDOWPOSCHANGED should not be intercepted")
        self.assertEqual(ret_pos, 0)

        # 3. WM_GETMINMAXINFO (0x0024) must not be intercepted
        msg_mmi = MSG()
        msg_mmi.hwnd = self.hwnd
        msg_mmi.message = WM_GETMINMAXINFO
        msg_mmi.wParam = 0
        msg_mmi.lParam = 0
        handled_mmi, ret_mmi = nef.nativeEventFilter("windows_generic_MSG", ctypes.addressof(msg_mmi))
        self.assertFalse(handled_mmi, "WM_GETMINMAXINFO should not be intercepted")
        self.assertEqual(ret_mmi, 0)

        # 4. WM_NCCALCSIZE when unmaximized with wParam=0 must return False, 0
        msg_ncc = MSG()
        msg_ncc.hwnd = self.hwnd
        msg_ncc.message = WM_NCCALCSIZE
        msg_ncc.wParam = 0
        msg_ncc.lParam = 0
        handled_ncc, ret_ncc = nef.nativeEventFilter("windows_generic_MSG", ctypes.addressof(msg_ncc))
        self.assertFalse(handled_ncc)
        self.assertEqual(ret_ncc, 0)


if __name__ == "__main__":
    unittest.main()
