"""
tests/test_challenger_m4_adversarial.py

Empirical Challenger M4 Adversarial Stress Harness.
Adversarially tests and stress-tests:
1. Live physical dual-monitor coordinate containment and zero-leakage assertions:
   - Primary monitor (0, 0, 1920, 1080), work area (0, 0, 1920, 1032)
   - Secondary monitor with negative coordinates (-1920, 0, 0, 1080), work area (-1920, 0, 0, 1032)
   - Moving and maximizing across boundaries
   - Strict assertion that client rect does not exceed work area by even 1 pixel
   - Strict assertion that right edge <= 0 and close button top-right is at (-1, 0) on secondary display
2. Simulated multi-monitor matrix (12 layout permutations) for WM_NCCALCSIZE boundary clamping:
   - Left negative coordinates, right positive coordinates, top negative Y, bottom positive Y
   - Mismatched 4K resolutions and custom taskbar configurations (left/right/top/bottom)
   - Exact clamping of 8px sizing border overhang to rcWork with zero pixel spillover
3. Windows Acrylic AccentPolicy drop shadow bleed prevention:
   - Assertion that AccentFlags == 0 on maximize (eliminates drop shadow bleed)
   - Assertion that AccentFlags contains drop shadow flags (0x20 | 0x40 | 0x80 | 0x100) when restored
   - Proper DWM backdrop handling on Windows 11 Build >= 22621
4. Adversarial edge cases:
   - Boundary straddling, wParam=0, unmaximized state, null handles, nchittest perimeter probing
5. Zero emoji verification across codebase.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    RECT, MONITORINFO, NCCALCSIZE_PARAMS, MSG,
    WM_NCCALCSIZE, WM_NCHITTEST,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    HTTOP, HTBOTTOM, HTLEFT, HTRIGHT,
    HTMAXBUTTON, HTCLIENT, HTCAPTION,
    MONITOR_DEFAULTTONEAREST
)
from src.ui.window_effects import (
    apply_window_blur, ACCENT_POLICY, WINCOMPATTRDATA,
    DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_TRANSIENTWINDOW, DWMSBT_MAINWINDOW
)

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMultiMonitorLiveAdversarial(unittest.TestCase):
    """Live physical multi-monitor stress harness."""

    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(380, 560)
        cls.win.show()
        cls.hwnd = int(cls.win.winId()) if sys.platform == "win32" else 0
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

        self.win.resize(380, 560)
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(15)

    def _get_secondary_screen(self):
        screens = QGuiApplication.screens()
        for s in screens:
            if s.geometry().x() < 0:
                return s
        return None

    def _get_primary_screen(self):
        screens = QGuiApplication.screens()
        for s in screens:
            if s.geometry().x() == 0:
                return s
        return screens[0] if screens else None

    # 1. PRIMARY MONITOR MAXIMIZE CONTAINMENT
    def test_01_primary_monitor_exact_containment_and_zero_leakage(self):
        """Verify client rect strictly equals primary work area without 1px spillover."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific test")

        pri_screen = self._get_primary_screen()
        self.assertIsNotNone(pri_screen, "Primary screen must exist")
        pri_work = pri_screen.availableGeometry()

        # Move to primary monitor and maximize
        self.win.move(pri_work.x() + 200, pri_work.y() + 150)
        app.processEvents()
        self.win.showMaximized()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        hwnd = wintypes.HWND(self.hwnd)
        self.assertTrue(bool(ctypes.windll.user32.IsZoomed(hwnd)))

        pt_tl = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
        client_rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        client_w = client_rect.right - client_rect.left
        client_h = client_rect.bottom - client_rect.top
        client_right = pt_tl.x + client_w
        client_bottom = pt_tl.y + client_h

        # Assert exact alignment to primary work area
        self.assertEqual(pt_tl.x, pri_work.x(), f"Left {pt_tl.x} must equal work area {pri_work.x()}")
        self.assertEqual(pt_tl.y, pri_work.y(), f"Top {pt_tl.y} must equal work area {pri_work.y()}")
        self.assertEqual(client_right, pri_work.x() + pri_work.width(), "Right edge must match primary work area")
        self.assertEqual(client_bottom, pri_work.y() + pri_work.height(), "Bottom edge must match primary work area")

        # Zero leakage onto secondary display (all X coordinates must be >= 0)
        self.assertGreaterEqual(pt_tl.x, 0, "Primary client left must not bleed into negative X coordinates")

        # Close button top-right corner check
        btn_close = self.win.title_bar.btn_close
        btn_tr = btn_close.mapToGlobal(btn_close.rect().topRight())
        self.assertEqual(btn_tr.x(), pri_work.width() - 1, f"Close button right must be at {pri_work.width() - 1}")
        self.assertEqual(btn_tr.y(), 0, "Close button top must be at 0")

    # 2. SECONDARY MONITOR (NEGATIVE COORDS) CONTAINMENT & ZERO LEAKAGE
    def test_02_secondary_monitor_negative_coordinates_zero_leakage(self):
        """Stress-test secondary monitor (-1920..0): assert right edge <= 0 and close button at (-1, 0)."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific test")

        sec_screen = self._get_secondary_screen()
        if sec_screen is None:
            self.skipTest("Physical secondary monitor with negative coordinates not attached")

        sec_work = sec_screen.availableGeometry()

        # Move to secondary monitor and maximize
        self.win.move(sec_work.x() + 300, sec_work.y() + 200)
        app.processEvents()
        self.win.showMaximized()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        hwnd = wintypes.HWND(self.hwnd)
        self.assertTrue(bool(ctypes.windll.user32.IsZoomed(hwnd)))

        pt_tl = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
        client_rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        client_w = client_rect.right - client_rect.left
        client_h = client_rect.bottom - client_rect.top
        client_right = pt_tl.x + client_w
        client_bottom = pt_tl.y + client_h

        # Strict containment assertions
        self.assertEqual(pt_tl.x, sec_work.x(), f"Left edge must equal secondary work area {sec_work.x()}")
        self.assertEqual(pt_tl.y, sec_work.y(), f"Top edge must equal secondary work area {sec_work.y()}")
        self.assertEqual(client_right, sec_work.x() + sec_work.width(), f"Right edge must equal {sec_work.x() + sec_work.width()}")
        self.assertEqual(client_bottom, sec_work.y() + sec_work.height(), f"Bottom edge must equal {sec_work.y() + sec_work.height()}")

        # Key requirement: right edge <= 0
        self.assertLessEqual(client_right, 0, f"Client right edge {client_right} leaked onto primary monitor (must be <= 0)!")

        # Key requirement: close button top-right is at (-1, 0)
        btn_close = self.win.title_bar.btn_close
        btn_tr = btn_close.mapToGlobal(btn_close.rect().topRight())
        self.assertEqual(btn_tr.x(), -1, f"Close button leaked! Expected x=-1, got {btn_tr.x()}")
        self.assertEqual(btn_tr.y(), 0, f"Close button top must be 0, got {btn_tr.y()}")

        # Assert no single pixel exceeds work area
        self.assertGreaterEqual(pt_tl.x, sec_work.left(), "Client rect exceeds left boundary")
        self.assertLessEqual(client_right, sec_work.right() + 1, "Client rect exceeds right boundary")
        self.assertGreaterEqual(pt_tl.y, sec_work.top(), "Client rect exceeds top boundary")
        self.assertLessEqual(client_bottom, sec_work.bottom() + 1, "Client rect exceeds bottom boundary")

    # 3. MOVING AND MAXIMIZING ACROSS BOUNDARIES (CROSS-MONITOR TRANSITION)
    def test_03_cross_boundary_maximize_and_reposition(self):
        """Simulate moving window across boundaries while maximized and verify dynamic clamping."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific test")

        sec_screen = self._get_secondary_screen()
        if sec_screen is None:
            self.skipTest("Secondary screen required")

        sec_work = sec_screen.availableGeometry()
        pri_screen = self._get_primary_screen()
        pri_work = pri_screen.availableGeometry()

        hwnd = wintypes.HWND(self.hwnd)

        # 1. Start on Primary, maximized
        self.win.move(pri_work.x() + 100, pri_work.y() + 100)
        self.win.showMaximized()
        for _ in range(3):
            app.processEvents()
            QTest.qWait(15)

        # 2. Simulate OS moving maximized window to secondary monitor (e.g. Win+Shift+Left)
        # We invoke SetWindowPos to simulate native repositioning to secondary monitor
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0,
            sec_work.x() - 8, sec_work.y() - 8,
            sec_work.width() + 16, sec_work.height() + 16,
            0x0004 | 0x0020  # SWP_NOZORDER | SWP_FRAMECHANGED
        )
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        pt_tl = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
        client_rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        client_w = client_rect.right - client_rect.left
        client_right = pt_tl.x + client_w

        self.assertEqual(pt_tl.x, sec_work.x(), "Must snap to secondary left")
        self.assertLessEqual(client_right, 0, "Must not leak past right edge 0")

        # 3. Simulate OS moving maximized window back to primary monitor (e.g. Win+Shift+Right)
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0,
            pri_work.x() - 8, pri_work.y() - 8,
            pri_work.width() + 16, pri_work.height() + 16,
            0x0004 | 0x0020
        )
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        pt_tl2 = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt_tl2))
        self.assertEqual(pt_tl2.x, pri_work.x(), "Must snap back to primary left")

    # 4. STRADDLING BOUNDARY AND MAXIMIZING
    def test_04_straddling_boundary_maximize(self):
        """Position window straddling boundary (half on secondary, half on primary) and maximize."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific test")

        sec_screen = self._get_secondary_screen()
        if sec_screen is None:
            self.skipTest("Secondary screen required")

        sec_work = sec_screen.availableGeometry()

        # Place window straddling x=0: left=-250, width=380 -> right=+130 (majority on secondary)
        self.win.showNormal()
        self.win.setGeometry(-250, 300, 380, 560)
        for _ in range(3):
            app.processEvents()
            QTest.qWait(15)

        self.win.showMaximized()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        hwnd = wintypes.HWND(self.hwnd)
        pt_tl = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
        client_rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        client_right = pt_tl.x + (client_rect.right - client_rect.left)

        # Majority was on secondary, so it must maximize onto secondary monitor
        self.assertEqual(pt_tl.x, sec_work.x())
        self.assertLessEqual(client_right, 0, "No leak allowed into primary monitor")

    # 5. RESTORE ON SECONDARY MONITOR PRESERVES SECONDARY PLACEMENT
    def test_05_restore_on_secondary_monitor_preserves_bounds(self):
        """Maximize on secondary, restore, verify restored window remains in secondary monitor."""
        if sys.platform != "win32":
            self.skipTest("Win32 specific test")

        sec_screen = self._get_secondary_screen()
        if sec_screen is None:
            self.skipTest("Secondary screen required")

        sec_work = sec_screen.availableGeometry()

        self.win.showNormal()
        self.win.setGeometry(sec_work.x() + 400, sec_work.y() + 200, 380, 560)
        for _ in range(3):
            app.processEvents()
            QTest.qWait(15)

        self.win.showMaximized()
        for _ in range(3):
            app.processEvents()
            QTest.qWait(15)

        # Restore
        self.win.showNormal()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(20)

        geom = self.win.geometry()
        self.assertLess(geom.right(), 0, "Restored window must remain inside secondary monitor")
        self.assertGreaterEqual(geom.left(), sec_work.left(), "Restored window must not exceed left edge")
        self.assertEqual(geom.width(), 380, "Restored width must be exactly 380")
        self.assertEqual(geom.height(), 560, "Restored height must be exactly 560")


class TestWMNcCalcSizeBoundaryMatrix(unittest.TestCase):
    """Exhaustive simulation of 12 multi-monitor layout configurations against WM_NCCALCSIZE."""

    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.show()
        app.processEvents()
        cls.filt = getattr(cls.win, "_native_event_filter", None)
        if cls.filt:
            cls.filt.hwnd = int(cls.win.winId())

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls.win, "_native_event_filter") and cls.win._native_event_filter:
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeNativeEventFilter(cls.win._native_event_filter)
            cls.win._native_event_filter = None
        cls.win.close()
        app.processEvents()

    def test_01_matrix_all_monitor_permutations(self):
        """Test WM_NCCALCSIZE coordinate clamping across 12 diverse monitor configurations."""
        if self.filt is None or sys.platform != "win32":
            self.skipTest("Win32 native event filter required")

        from src.ui.native_window import user32

        scenarios = [
            (
                "1. Left Secondary 1080p (-1920..0)",
                RECT(-1920, 0, 0, 1080), RECT(-1920, 0, 0, 1032),
                RECT(-1928, -8, 8, 1040), (-1920, 0, 0, 1032)
            ),
            (
                "2. Primary 1080p (0..1920)",
                RECT(0, 0, 1920, 1080), RECT(0, 0, 1920, 1032),
                RECT(-8, -8, 1928, 1040), (0, 0, 1920, 1032)
            ),
            (
                "3. Right Secondary 1080p (1920..3840)",
                RECT(1920, 0, 3840, 1080), RECT(1920, 0, 3840, 1032),
                RECT(1912, -8, 3848, 1040), (1920, 0, 3840, 1032)
            ),
            (
                "4. Top Secondary (0, -1080, 1920, 0)",
                RECT(0, -1080, 1920, 0), RECT(0, -1080, 1920, -48),
                RECT(-8, -1088, 1928, -40), (0, -1080, 1920, -48)
            ),
            (
                "5. Bottom Secondary (0, 1080, 1920, 2160)",
                RECT(0, 1080, 1920, 2160), RECT(0, 1080, 1920, 2112),
                RECT(-8, 1072, 1928, 2120), (0, 1080, 1920, 2112)
            ),
            (
                "6. 4K Left Secondary (-3840, 0, 0, 2160)",
                RECT(-3840, 0, 0, 2160), RECT(-3840, 0, 0, 2088),
                RECT(-3848, -8, 8, 2096), (-3840, 0, 0, 2088)
            ),
            (
                "7. 4K Right Secondary (1920, 0, 5760, 2160)",
                RECT(1920, 0, 5760, 2160), RECT(1920, 0, 5760, 2088),
                RECT(1912, -8, 5768, 2096), (1920, 0, 5760, 2088)
            ),
            (
                "8. Mismatched 720p Left (-1280, 0, 0, 720)",
                RECT(-1280, 0, 0, 720), RECT(-1280, 0, 0, 680),
                RECT(-1288, -8, 8, 688), (-1280, 0, 0, 680)
            ),
            (
                "9. Taskbar on Left (Secondary) (-1920, 0, 0, 1080)",
                RECT(-1920, 0, 0, 1080), RECT(-1872, 0, 0, 1080),
                RECT(-1928, -8, 8, 1088), (-1872, 0, 0, 1080)
            ),
            (
                "10. Taskbar on Right (Secondary) (-1920, 0, 0, 1080)",
                RECT(-1920, 0, 0, 1080), RECT(-1920, 0, -48, 1080),
                RECT(-1928, -8, 8, 1088), (-1920, 0, -48, 1080)
            ),
            (
                "11. Taskbar on Top (Secondary) (-1920, 0, 0, 1080)",
                RECT(-1920, 0, 0, 1080), RECT(-1920, 48, 0, 1080),
                RECT(-1928, 40, 8, 1088), (-1920, 48, 0, 1080)
            ),
            (
                "12. Far-Left Triple Monitor (-3840..-1920)",
                RECT(-3840, 0, -1920, 1080), RECT(-3840, 0, -1920, 1032),
                RECT(-3848, -8, -1912, 1040), (-3840, 0, -1920, 1032)
            ),
        ]

        fake_hmon = 0x99999999

        for desc, rc_mon, rc_work, proposed_rect, exp_rect in scenarios:
            with self.subTest(scenario=desc):
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
                params.rgrc[0].left = proposed_rect.left
                params.rgrc[0].top = proposed_rect.top
                params.rgrc[0].right = proposed_rect.right
                params.rgrc[0].bottom = proposed_rect.bottom

                msg = MSG()
                msg.hwnd = self.filt.hwnd
                msg.message = WM_NCCALCSIZE
                msg.wParam = 1
                msg.lParam = ctypes.addressof(params)

                with patch.object(user32, "IsZoomed", return_value=1), \
                     patch.object(user32, "MonitorFromRect", return_value=fake_hmon), \
                     patch.object(user32, "GetMonitorInfoW", side_effect=mock_get_monitor_info):

                    handled, ret = self.filt.nativeEventFilter(
                        b"windows_generic_MSG", ctypes.addressof(msg)
                    )

                    self.assertTrue(handled)
                    self.assertEqual(ret, 0)

                    actual_rect = (
                        params.rgrc[0].left,
                        params.rgrc[0].top,
                        params.rgrc[0].right,
                        params.rgrc[0].bottom
                    )
                    self.assertEqual(
                        actual_rect, exp_rect,
                        f"Spillover or mismatch in {desc}: expected {exp_rect}, got {actual_rect}"
                    )


class TestAccentFlagsAndDropShadowBleed(unittest.TestCase):
    """Verifies that drop shadows and acrylic borders are suppressed on maximize."""

    def test_01_accent_flags_zero_when_maximized_windows_10(self):
        """Assert AccentFlags == 0 when maximized under Windows 10 SetWindowCompositionAttribute."""
        fake_ver = MagicMock()
        fake_ver.build = 19045
        fake_ver.major = 10
        fake_ver.minor = 0

        captured_accents = []

        def mock_set_comp(hwnd, p_data):
            data = ctypes.cast(p_data, ctypes.POINTER(WINCOMPATTRDATA)).contents
            if data.Attribute == 19:
                accent = ctypes.cast(data.Data, ctypes.POINTER(ACCENT_POLICY)).contents
                captured_accents.append(accent.AccentFlags)
            return 1

        with patch("sys.getwindowsversion", return_value=fake_ver), \
             patch.object(ctypes.windll.user32, "SetWindowCompositionAttribute", side_effect=mock_set_comp):

            # Maximized: AccentFlags must be 0
            apply_window_blur(0x1234, is_maximized=True)
            self.assertEqual(len(captured_accents), 1)
            self.assertEqual(
                captured_accents[0], 0,
                f"AccentFlags must be 0 on maximize to eliminate shadow bleed, got {hex(captured_accents[0])}"
            )

            # Restored: AccentFlags must include shadows & borders
            apply_window_blur(0x1234, is_maximized=False)
            self.assertEqual(len(captured_accents), 2)
            expected_flags = 0x20 | 0x40 | 0x80 | 0x100
            self.assertEqual(
                captured_accents[1], expected_flags,
                f"AccentFlags must be {hex(expected_flags)} on restore, got {hex(captured_accents[1])}"
            )

    def test_02_windows_11_modern_composition_no_legacy_conflict(self):
        """Assert Windows 11 Build >= 22621 uses modern DWM backdrop and bypasses legacy acrylic."""
        fake_ver = MagicMock()
        fake_ver.build = 22621
        fake_ver.major = 10
        fake_ver.minor = 0

        mock_set_comp = MagicMock(return_value=1)
        mock_dwm_attr = MagicMock(return_value=0)  # S_OK

        with patch("sys.getwindowsversion", return_value=fake_ver), \
             patch.object(ctypes.windll.dwmapi, "DwmSetWindowAttribute", mock_dwm_attr), \
             patch.object(ctypes.windll.user32, "SetWindowCompositionAttribute", mock_set_comp):

            success = apply_window_blur(0x1234, is_maximized=True)
            self.assertTrue(success)

            # Modern DWM backdrop applied
            self.assertGreaterEqual(mock_dwm_attr.call_count, 1)

            # Legacy SetWindowCompositionAttribute MUST NOT be called (prevents viewport freeze)
            mock_set_comp.assert_not_called()


class TestAdversarialEdgeCases(unittest.TestCase):
    """Stress-test error handling, boundary conditions, and invalid inputs."""

    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.show()
        app.processEvents()
        cls.filt = getattr(cls.win, "_native_event_filter", None)
        if cls.filt:
            cls.filt.hwnd = int(cls.win.winId())

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls.win, "_native_event_filter") and cls.win._native_event_filter:
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeNativeEventFilter(cls.win._native_event_filter)
            cls.win._native_event_filter = None
        cls.win.close()
        app.processEvents()

    def test_01_wm_nccalcsize_fallback_to_monitor_from_window(self):
        """When MonitorFromRect returns 0, verify fallback to MonitorFromWindow."""
        if self.filt is None or sys.platform != "win32":
            self.skipTest("Win32 required")

        from src.ui.native_window import user32

        fallback_hmon = 0x55555555
        target_work = (-1920, 0, 0, 1032)

        def mock_get_info(hmon, mi_ptr):
            mi = ctypes.cast(mi_ptr, ctypes.POINTER(MONITORINFO)).contents
            mi.rcWork.left = target_work[0]
            mi.rcWork.top = target_work[1]
            mi.rcWork.right = target_work[2]
            mi.rcWork.bottom = target_work[3]
            return 1

        params = NCCALCSIZE_PARAMS()
        params.rgrc[0].left = -1928
        params.rgrc[0].top = -8
        params.rgrc[0].right = 8
        params.rgrc[0].bottom = 1040

        msg = MSG()
        msg.hwnd = self.filt.hwnd
        msg.message = WM_NCCALCSIZE
        msg.wParam = 1
        msg.lParam = ctypes.addressof(params)

        # MonitorFromRect fails (returns 0), MonitorFromWindow succeeds
        with patch.object(user32, "IsZoomed", return_value=1), \
             patch.object(user32, "MonitorFromRect", return_value=0), \
             patch.object(user32, "MonitorFromWindow", return_value=fallback_hmon), \
             patch.object(user32, "GetMonitorInfoW", side_effect=mock_get_info):

            handled, ret = self.filt.nativeEventFilter(
                b"windows_generic_MSG", ctypes.addressof(msg)
            )

            self.assertTrue(handled)
            self.assertEqual(ret, 0)
            self.assertEqual(
                (params.rgrc[0].left, params.rgrc[0].top, params.rgrc[0].right, params.rgrc[0].bottom),
                target_work
            )

    def test_02_wm_nccalcsize_both_monitors_fail_gracefully(self):
        """When both MonitorFromRect and MonitorFromWindow fail, rgrc[0] remains untouched."""
        if self.filt is None or sys.platform != "win32":
            self.skipTest("Win32 required")

        from src.ui.native_window import user32

        params = NCCALCSIZE_PARAMS()
        params.rgrc[0].left = -1928
        params.rgrc[0].top = -8
        params.rgrc[0].right = 8
        params.rgrc[0].bottom = 1040

        msg = MSG()
        msg.hwnd = self.filt.hwnd
        msg.message = WM_NCCALCSIZE
        msg.wParam = 1
        msg.lParam = ctypes.addressof(params)

        with patch.object(user32, "IsZoomed", return_value=1), \
             patch.object(user32, "MonitorFromRect", return_value=0), \
             patch.object(user32, "MonitorFromWindow", return_value=0):

            handled, ret = self.filt.nativeEventFilter(
                b"windows_generic_MSG", ctypes.addressof(msg)
            )

            self.assertTrue(handled)
            self.assertEqual(ret, 0)
            self.assertEqual(
                (params.rgrc[0].left, params.rgrc[0].top, params.rgrc[0].right, params.rgrc[0].bottom),
                (-1928, -8, 8, 1040)
            )

    def test_03_invalid_message_addresses_safe(self):
        """Verify nativeEventFilter handles 0, null, or invalid message pointers without crashing."""
        if self.filt is None:
            self.skipTest("Native filter required")

        handled, ret = self.filt.nativeEventFilter(b"windows_generic_MSG", 0)
        self.assertFalse(handled)
        self.assertEqual(ret, 0)

        handled, ret = self.filt.nativeEventFilter(b"windows_generic_MSG", None)
        self.assertFalse(handled)
        self.assertEqual(ret, 0)

        handled, ret = self.filt.nativeEventFilter(b"invalid_event_type", 123456)
        self.assertFalse(handled)
        self.assertEqual(ret, 0)


class TestZeroEmojiCompliance(unittest.TestCase):
    """Exhaustive check that no emojis exist in modified or related codebase."""

    def test_zero_emojis(self):
        import unicodedata

        files_to_check = [
            REPO_ROOT / "src" / "ui" / "native_window.py",
            REPO_ROOT / "src" / "ui" / "window_effects.py",
            REPO_ROOT / "src" / "ui" / "main_window.py",
            REPO_ROOT / "tests" / "verify_onscreen_m4.py",
            REPO_ROOT / "tests" / "test_challenger_m4_adversarial.py",
        ]

        violations = []
        for f in files_to_check:
            if not f.exists():
                continue
            with open(f, "r", encoding="utf-8", errors="replace") as fp:
                for line_no, line in enumerate(fp, start=1):
                    for char in line:
                        if 0xE000 <= ord(char) <= 0xF8FF:
                            continue  # Private Use Area (Segoe icons)
                        char_name = unicodedata.name(char, "")
                        if "EMOJI" in char_name:
                            violations.append(f"{f.name}:{line_no} '{char}' ({char_name})")

        self.assertEqual(len(violations), 0, f"Found emojis: {violations}")


if __name__ == "__main__":
    unittest.main()
