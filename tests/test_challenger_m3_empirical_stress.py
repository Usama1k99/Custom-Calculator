"""
Challenger 1 Empirical Verification and Adversarial Stress Harness for Milestone 3.

Exhaustively verifies:
1. Rapid consecutive maximize and restore toggles (50 cycles) for zero coordinate creep and zero dimension drift.
2. Pass-through and sizing constraints of WM_GETMINMAXINFO, WM_SIZE, WM_WINDOWPOSCHANGED, and WM_WINDOWPOSCHANGING.
3. Multi-monitor coordinate alignment and 8px border containment under diverse geometries.
4. Stress toggling across multiple calculator modes (Scientific, Programmer, History Drawer open).
5. Non-client button state hygiene (hover, press, killfocus, capturechanged, activate, dblclk).
"""

import sys
import os
import time
import ctypes
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    RECT, MONITORINFO, MINMAXINFO, NCCALCSIZE_PARAMS, MSG,
    WM_NCCALCSIZE,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    HTTOP, HTBOTTOM, HTLEFT, HTRIGHT,
    HTMAXBUTTON, HTCLIENT, HTCAPTION
)

WM_SIZE = 0x0005
WM_ACTIVATE = 0x0006
WM_KILLFOCUS = 0x0008
WM_GETMINMAXINFO = 0x0024
WM_WINDOWPOSCHANGING = 0x0046
WM_WINDOWPOSCHANGED = 0x0047
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_CAPTURECHANGED = 0x0215
WM_NCMOUSELEAVE = 0x02A2

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestChallengerM3EmpiricalStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(400, 600)
        cls.win.show()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls.win, "_native_event_filter") and cls.win._native_event_filter:
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeNativeEventFilter(cls.win._native_event_filter)
            cls.win._native_event_filter = None
        cls.win.close()
        app.processEvents()

    def setUp(self):
        self.win._switch_mode("Standard", save_config=False)
        if sys.platform == "win32":
            hwnd = int(self.win.winId())
            if ctypes.windll.user32.IsZoomed(ctypes.c_void_p(hwnd)) or self.win.isMaximized():
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                self.win.showNormal()
        elif self.win.isMaximized():
            self.win.showNormal()

        if hasattr(self.win, "history_drawer") and self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
        if hasattr(self.win, "sidebar") and self.win.sidebar.isVisible():
            self.win._toggle_sidebar()

        self.win.resize(400, 600)
        self.win.move(100, 100)
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

    # -------------------------------------------------------------------------
    # 1. 50 CYCLES RAPID MAXIMIZE / RESTORE TOGGLE STRESS & DRIFT TEST
    # -------------------------------------------------------------------------
    def test_01_fifty_cycles_rapid_toggle_zero_creep_and_drift(self):
        """Perform 50 rapid maximize/restore toggles to detect any coordinate creep or dimension drift."""
        initial_w = self.win.width()
        initial_h = self.win.height()
        initial_x = self.win.x()
        initial_y = self.win.y()

        self.assertEqual(initial_w, 400)
        self.assertEqual(initial_h, 600)

        for cycle in range(50):
            # Maximize
            self.win.title_bar.btn_maximize.click()
            for _ in range(2):
                app.processEvents()
                QTest.qWait(5)

            is_max = self.win.isMaximized()
            if sys.platform == "win32":
                is_max = is_max or bool(ctypes.windll.user32.IsZoomed(int(self.win.winId())))
            self.assertTrue(is_max, f"Failed to maximize on cycle {cycle}")
            self.assertEqual(self.win.root_container.size(), self.win.size())

            # Restore
            self.win.title_bar.btn_maximize.click()
            for _ in range(2):
                app.processEvents()
                QTest.qWait(5)

            self.assertFalse(self.win.isMaximized(), f"Failed to restore on cycle {cycle}")
            self.assertEqual(self.win.root_container.size(), self.win.size())

        final_w = self.win.width()
        final_h = self.win.height()
        final_x = self.win.x()
        final_y = self.win.y()

        # Zero dimension drift
        self.assertEqual(final_w, initial_w, f"Width drifted from {initial_w} to {final_w}")
        self.assertEqual(final_h, initial_h, f"Height drifted from {initial_h} to {final_h}")

        # Zero coordinate creep
        self.assertEqual(final_x, initial_x, f"X-position crept from {initial_x} to {final_x}")
        self.assertEqual(final_y, initial_y, f"Y-position crept from {initial_y} to {final_y}")

        # Config integrity
        self.assertEqual(self.win.config.get("window_width"), 400)
        self.assertEqual(self.win.config.get("window_height"), 600)

    # -------------------------------------------------------------------------
    # 2. MESSAGE PASS-THROUGH: WM_GETMINMAXINFO, WM_SIZE, WM_WINDOWPOSCHANGED
    # -------------------------------------------------------------------------
    def test_02_message_passthrough_wm_getminmaxinfo_and_size_and_poschanged(self):
        """Empirically assert WM_GETMINMAXINFO, WM_SIZE, and WM_WINDOWPOSCHANGED are not intercepted."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        # 2.1 WM_GETMINMAXINFO must pass through unintercepted (handled=False, ret=0)
        mmi = MINMAXINFO()
        msg_mmi = MSG()
        msg_mmi.hwnd = filt.hwnd
        msg_mmi.message = WM_GETMINMAXINFO
        msg_mmi.wParam = 0
        msg_mmi.lParam = ctypes.addressof(mmi)

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_mmi))
        self.assertFalse(handled, "WM_GETMINMAXINFO must not be intercepted by WinNativeEventFilter")
        self.assertEqual(ret, 0)

        # 2.2 WM_SIZE (0x0005) must pass through unintercepted
        msg_size = MSG()
        msg_size.hwnd = filt.hwnd
        msg_size.message = WM_SIZE
        msg_size.wParam = 0
        msg_size.lParam = (600 << 16) | 400

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_size))
        self.assertFalse(handled, "WM_SIZE must not be intercepted by WinNativeEventFilter")
        self.assertEqual(ret, 0)

        # 2.3 WM_WINDOWPOSCHANGED (0x0047) must pass through unintercepted
        msg_wpc = MSG()
        msg_wpc.hwnd = filt.hwnd
        msg_wpc.message = WM_WINDOWPOSCHANGED
        msg_wpc.wParam = 0
        msg_wpc.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_wpc))
        self.assertFalse(handled, "WM_WINDOWPOSCHANGED must not be intercepted by WinNativeEventFilter")
        self.assertEqual(ret, 0)

        # 2.4 WM_WINDOWPOSCHANGING (0x0046) must pass through unintercepted
        msg_wpg = MSG()
        msg_wpg.hwnd = filt.hwnd
        msg_wpg.message = WM_WINDOWPOSCHANGING
        msg_wpg.wParam = 0
        msg_wpg.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_wpg))
        self.assertFalse(handled, "WM_WINDOWPOSCHANGING must not be intercepted by WinNativeEventFilter")
        self.assertEqual(ret, 0)

    # -------------------------------------------------------------------------
    # 3. MULTI-MONITOR WM_NCCALCSIZE COORDINATE ALIGNMENT
    # -------------------------------------------------------------------------
    def test_03_multimonitor_wm_nccalcsize_coordinate_alignment(self):
        """Empirically test WM_NCCALCSIZE boundary clamping across multi-monitor setups."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        from src.ui.native_window import user32

        test_layouts = [
            # description, rcMonitor, rcWork, incoming_rgrc0, expected_rgrc0
            (
                "Secondary Left Monitor with Bottom Taskbar",
                RECT(-1920, 0, 0, 1080),
                RECT(-1920, 0, 0, 1032),
                RECT(-1928, -8, 8, 1040),
                (-1920, 0, 0, 1032)
            ),
            (
                "Secondary Right Monitor with Left Taskbar",
                RECT(1920, 0, 3840, 1080),
                RECT(1980, 0, 3840, 1080),
                RECT(1912, -8, 3848, 1040),
                (1980, 0, 3840, 1080)
            ),
            (
                "Secondary Top Monitor with Top Taskbar",
                RECT(0, -1080, 1920, 0),
                RECT(0, -1040, 1920, 0),
                RECT(-8, -1088, 1928, 8),
                (0, -1040, 1920, 0)
            ),
            (
                "Secondary Bottom Monitor with Right Taskbar",
                RECT(0, 1080, 1920, 2160),
                RECT(0, 1080, 1860, 2160),
                RECT(-8, 1072, 1928, 2168),
                (0, 1080, 1860, 2160)
            ),
            (
                "Triple Monitor Setup - Far Left (-3840 to -1920)",
                RECT(-3840, 0, -1920, 1200),
                RECT(-3840, 0, -1920, 1152),
                RECT(-3848, -8, -1912, 1160),
                (-3840, 0, -1920, 1152)
            ),
            (
                "Primary 4K UHD Monitor (3840x2160)",
                RECT(0, 0, 3840, 2160),
                RECT(0, 0, 3840, 2088),
                RECT(-8, -8, 3848, 2096),
                (0, 0, 3840, 2088)
            )
        ]

        for desc, rc_mon, rc_work, in_rect, exp_rect in test_layouts:
            with self.subTest(scenario=desc):
                fake_hmon = 0xABCDEF01

                def mock_get_monitor_info(hmon, mi_ptr):
                    mi = ctypes.cast(mi_ptr, ctypes.POINTER(MONITORINFO)).contents
                    mi.rcMonitor.left = rc_mon.left
                    mi.rcMonitor.top = rc_mon.top
                    mi.rcMonitor.right = rc_mon.right
                    mi.rcMonitor.bottom = rc_mon.bottom
                    mi.rcWork.left = rc_work.left
                    mi.rcWork.top = rc_work.top
                    mi.rcWork.right = rc_work.right
                    mi.rcWork.bottom = rc_work.bottom
                    return 1

                params = NCCALCSIZE_PARAMS()
                params.rgrc[0].left = in_rect.left
                params.rgrc[0].top = in_rect.top
                params.rgrc[0].right = in_rect.right
                params.rgrc[0].bottom = in_rect.bottom

                msg = MSG()
                msg.hwnd = filt.hwnd
                msg.message = WM_NCCALCSIZE
                msg.wParam = 1
                msg.lParam = ctypes.addressof(params)

                with patch.object(user32, "IsZoomed", return_value=1), \
                     patch.object(user32, "MonitorFromWindow", return_value=fake_hmon), \
                     patch.object(user32, "GetMonitorInfoW", side_effect=mock_get_monitor_info):

                    handled, ret = filt.nativeEventFilter(
                        b"windows_generic_MSG", ctypes.addressof(msg)
                    )

                    self.assertTrue(handled)
                    self.assertEqual(ret, 0)
                    result_rect = (
                        params.rgrc[0].left,
                        params.rgrc[0].top,
                        params.rgrc[0].right,
                        params.rgrc[0].bottom
                    )
                    self.assertEqual(result_rect, exp_rect)

    # -------------------------------------------------------------------------
    # 4. STRESS TOGGLING IN DIFFERENT CALCULATOR MODES
    # -------------------------------------------------------------------------
    def test_04_stress_toggle_with_history_drawer_and_scientific_mode(self):
        """Stress toggle maximize/restore 20 times in Scientific mode with History Drawer open."""
        self.win._switch_mode("Scientific", save_config=False)
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()

        initial_size = self.win.size()

        for cycle in range(20):
            self.win.title_bar.btn_maximize.click()
            for _ in range(2):
                app.processEvents()
                QTest.qWait(5)

            is_max = self.win.isMaximized()
            if sys.platform == "win32":
                is_max = is_max or bool(ctypes.windll.user32.IsZoomed(int(self.win.winId())))
            self.assertTrue(is_max, f"Failed to maximize on cycle {cycle} with history drawer open")

            # Check that drawer + center container fill the entire window exactly
            w = self.win.width()
            self.assertEqual(self.win.history_drawer.width() + self.win.center_container.width(), w)

            self.win.title_bar.btn_maximize.click()
            for _ in range(2):
                app.processEvents()
                QTest.qWait(5)

            self.assertFalse(self.win.isMaximized())

        self.assertEqual(self.win.size(), initial_size)

        # Close history drawer
        self.win._toggle_history_drawer()

    # -------------------------------------------------------------------------
    # 5. NON-CLIENT BUTTON STATE HYGIENE & EVENTS
    # -------------------------------------------------------------------------
    def test_05_nc_button_interaction_and_focus_loss_hygiene(self):
        """Verify non-client button states (hover, press, killfocus, capturechanged, activate)."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        # 5.1 WM_NCLBUTTONDOWN on HTMAXBUTTON sets pressed flag
        msg_down = MSG()
        msg_down.hwnd = filt.hwnd
        msg_down.message = WM_NCLBUTTONDOWN
        msg_down.wParam = HTMAXBUTTON
        msg_down.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_down))
        self.assertTrue(handled)
        self.assertEqual(ret, 0)
        self.assertTrue(getattr(self.win, "_btn_maximize_pressed", False))

        # 5.2 WM_KILLFOCUS resets pressed and hover flags
        self.win._btn_maximize_hovered = True
        msg_kf = MSG()
        msg_kf.hwnd = filt.hwnd
        msg_kf.message = WM_KILLFOCUS
        msg_kf.wParam = 0
        msg_kf.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_kf))
        self.assertFalse(handled)
        self.assertFalse(getattr(self.win, "_btn_maximize_pressed", False))
        self.assertFalse(getattr(self.win, "_btn_maximize_hovered", False))

        # 5.3 WM_CAPTURECHANGED resets pressed and hover flags
        self.win._btn_maximize_pressed = True
        self.win._btn_maximize_hovered = True
        msg_cc = MSG()
        msg_cc.hwnd = filt.hwnd
        msg_cc.message = WM_CAPTURECHANGED
        msg_cc.wParam = 0
        msg_cc.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_cc))
        self.assertFalse(handled)
        self.assertFalse(getattr(self.win, "_btn_maximize_pressed", False))
        self.assertFalse(getattr(self.win, "_btn_maximize_hovered", False))

        # 5.4 WM_ACTIVATE resets pressed and hover flags
        self.win._btn_maximize_pressed = True
        self.win._btn_maximize_hovered = True
        msg_act = MSG()
        msg_act.hwnd = filt.hwnd
        msg_act.message = WM_ACTIVATE
        msg_act.wParam = 0
        msg_act.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_act))
        self.assertFalse(handled)
        self.assertFalse(getattr(self.win, "_btn_maximize_pressed", False))
        self.assertFalse(getattr(self.win, "_btn_maximize_hovered", False))

        # 5.5 WM_NCLBUTTONUP without prior press does NOT toggle maximize
        is_max_before = self.win.isMaximized()
        self.win._btn_maximize_pressed = False
        msg_up = MSG()
        msg_up.hwnd = filt.hwnd
        msg_up.message = WM_NCLBUTTONUP
        msg_up.wParam = HTMAXBUTTON
        msg_up.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_up))
        self.assertFalse(handled)
        self.assertEqual(self.win.isMaximized(), is_max_before)

        # 5.6 WM_NCLBUTTONUP with prior press DOES toggle maximize synchronously
        self.win._btn_maximize_pressed = True
        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_up))
        self.assertTrue(handled)
        self.assertEqual(ret, 0)
        self.assertNotEqual(self.win.isMaximized(), is_max_before)
        self.assertFalse(getattr(self.win, "_btn_maximize_pressed", False))

        # 5.7 WM_NCLBUTTONDBLCLK on HTCAPTION toggles maximize synchronously
        current_state = self.win.isMaximized()
        msg_dbl = MSG()
        msg_dbl.hwnd = filt.hwnd
        msg_dbl.message = WM_NCLBUTTONDBLCLK
        msg_dbl.wParam = HTCAPTION
        msg_dbl.lParam = 0

        handled, ret = filt.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg_dbl))
        self.assertTrue(handled)
        self.assertEqual(ret, 0)
        self.assertNotEqual(self.win.isMaximized(), current_state)


if __name__ == "__main__":
    unittest.main()
