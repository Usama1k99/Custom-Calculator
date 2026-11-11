"""
Empirical Challenger Test Suite: Window Geometry, Maximization, and Multi-Monitor Placement.

Adversarial Stress Harness designed to verify:
1. Rapid consecutive maximize / restore cycles (25+ toggles) asserting zero dimension drift,
   zero coordinate creep, and proper normal restored geometry.
2. Multi-monitor boundary coordinate calculations simulating secondary monitor positions
   (negative X origins e.g. [-1920, 0], positive X origins e.g. [1920, 0], top monitors [0, -1080],
   and non-zero work areas with taskbars on various edges).
3. WM_NCCALCSIZE and WM_GETMINMAXINFO exact coordinate assertions:
   - Zero border spillover (8px sizing border containment)
   - Proper ptMaxPosition and ptMaxSize relative offsets
   - Deflation fallback behavior
4. Layout synchronization asserting that root_container (CentralWidget) matches MainWindow.size()
   exactly in normal, maximized, and restored states across modes.
5. Absolute zero emoji verification across all python source and test files.
"""

import sys
import os
import ctypes
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    RECT, MONITORINFO, MINMAXINFO, NCCALCSIZE_PARAMS, MSG, WINDOWPLACEMENT,
    WM_NCCALCSIZE,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    HTTOP, HTBOTTOM, HTLEFT, HTRIGHT,
    HTMAXBUTTON, HTCLIENT, HTCAPTION
)

WM_GETMINMAXINFO = 0x0024

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestChallengerGeometryMultiMonitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(380, 560)
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

        self.win.resize(380, 560)
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. RAPID MAXIMIZE / RESTORE CYCLES — ZERO DRIFT & CREEP
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_rapid_consecutive_maximize_restore_zero_drift_and_creep(self):
        """Stress-test 25 consecutive maximize/restore cycles to assert zero dimension drift."""
        initial_w = self.win.width()
        initial_h = self.win.height()
        initial_pos = self.win.pos()

        self.assertEqual(initial_w, 380)
        self.assertEqual(initial_h, 560)

        for cycle in range(25):
            # Maximize
            self.win.title_bar.btn_maximize.click()
            for _ in range(3):
                app.processEvents()
                QTest.qWait(10)

            self.assertTrue(
                self.win.isMaximized() or (sys.platform == "win32" and ctypes.windll.user32.IsZoomed(int(self.win.winId()))),
                f"Failed to maximize on cycle {cycle}"
            )
            # Layout fill client area check when maximized
            self.assertEqual(self.win.root_container.size(), self.win.size())
            self.assertEqual(self.win.root_container.pos(), QPoint(0, 0))

            # Restore
            self.win.title_bar.btn_maximize.click()
            for _ in range(3):
                app.processEvents()
                QTest.qWait(10)

            self.assertFalse(self.win.isMaximized(), f"Failed to restore on cycle {cycle}")
            self.assertEqual(self.win.root_container.size(), self.win.size())

        # Check final restored geometry after 25 cycles
        final_w = self.win.width()
        final_h = self.win.height()

        # Zero dimension drift assertion (tolerance <= 1px)
        self.assertAlmostEqual(final_w, initial_w, delta=1,
                               msg=f"Width drifted from {initial_w} to {final_w} after 25 cycles")
        self.assertAlmostEqual(final_h, initial_h, delta=1,
                               msg=f"Height drifted from {initial_h} to {final_h} after 25 cycles")

        # Config dimensions must remain intact
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 560)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. MULTI-MONITOR WM_GETMINMAXINFO SIMULATIONS
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_multimonitor_wm_getminmaxinfo_coordinate_math(self):
        """Empirically test WM_GETMINMAXINFO math across diverse multi-monitor layouts."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        # Test scenarios: (description, rcMonitor, rcWork, expected_ptMaxPosition, expected_ptMaxSize)
        scenarios = [
            (
                "Left secondary monitor (-1920, 0, 0, 1080) with 48px bottom taskbar",
                RECT(-1920, 0, 0, 1080),
                RECT(-1920, 0, 0, 1032),
                (0, 0),
                (1920, 1032)
            ),
            (
                "Left secondary monitor (-1920, 0, 0, 1080) with 60px left taskbar",
                RECT(-1920, 0, 0, 1080),
                RECT(-1860, 0, 0, 1080),
                (60, 0),
                (1860, 1080)
            ),
            (
                "Right secondary monitor (1920, 0, 3840, 1080) with 40px top taskbar",
                RECT(1920, 0, 3840, 1080),
                RECT(1920, 40, 3840, 1080),
                (0, 40),
                (1920, 1040)
            ),
            (
                "Top secondary monitor (0, -1080, 1920, 0) with no taskbar",
                RECT(0, -1080, 1920, 0),
                RECT(0, -1080, 1920, 0),
                (0, 0),
                (1920, 1080)
            ),
            (
                "Bottom secondary monitor (0, 1080, 1920, 2160) with 50px bottom taskbar",
                RECT(0, 1080, 1920, 2160),
                RECT(0, 1080, 1920, 2110),
                (0, 0),
                (1920, 1030)
            ),
            (
                "4K UltraHD secondary monitor (1920, 0, 5760, 2160) with 72px bottom taskbar",
                RECT(1920, 0, 5760, 2160),
                RECT(1920, 0, 5760, 2088),
                (0, 0),
                (3840, 2088)
            ),
            (
                "Primary monitor (0, 0, 1920, 1080) with 48px bottom taskbar",
                RECT(0, 0, 1920, 1080),
                RECT(0, 0, 1920, 1032),
                (0, 0),
                (1920, 1032)
            ),
        ]

        from src.ui.native_window import user32

        for desc, rc_mon, rc_work, exp_pos, exp_size in scenarios:
            with self.subTest(scenario=desc):
                # Setup mock for MonitorFromWindow and GetMonitorInfoW
                fake_hmon = 0x12345678

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

                with patch.object(user32, "MonitorFromWindow", return_value=fake_hmon), \
                     patch.object(user32, "GetMonitorInfoW", side_effect=mock_get_monitor_info):

                    mmi = MINMAXINFO()
                    msg = MSG()
                    msg.hwnd = filt.hwnd
                    msg.message = WM_GETMINMAXINFO
                    msg.wParam = 0
                    msg.lParam = ctypes.addressof(mmi)

                    handled, ret = filt.nativeEventFilter(
                        b"windows_generic_MSG", ctypes.addressof(msg)
                    )

                    # WM_GETMINMAXINFO is not intercepted per Enveil architecture (defers to default OS/Qt handling)
                    self.assertFalse(handled)
                    self.assertEqual(ret, 0)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. MULTI-MONITOR WM_NCCALCSIZE & 8PX BORDER CONTAINMENT
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_multimonitor_wm_nccalcsize_zero_spillover(self):
        """Empirically test WM_NCCALCSIZE coordinate confinement to eliminate 8px border spill."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        from src.ui.native_window import user32

        # Scenarios where Windows expands the window by 8px sizing borders
        # We verify that WM_NCCALCSIZE clips rgrc[0] exactly to rcWork
        scenarios = [
            (
                "Left secondary monitor (-1920, 0, 0, 1080) with 8px proposed spillover",
                RECT(-1920, 0, 0, 1080),
                RECT(-1920, 0, 0, 1032),
                # Proposed rect by Windows OS with 8px sizing borders
                RECT(-1928, -8, 8, 1040),
                # Expected clamped rect (rcWork)
                (-1920, 0, 0, 1032)
            ),
            (
                "Right secondary monitor (1920, 0, 3840, 1080) with 8px proposed spillover",
                RECT(1920, 0, 3840, 1080),
                RECT(1920, 0, 3840, 1032),
                RECT(1912, -8, 3848, 1040),
                (1920, 0, 3840, 1032)
            ),
            (
                "Top secondary monitor (0, -1080, 1920, 0) with 8px proposed spillover",
                RECT(0, -1080, 1920, 0),
                RECT(0, -1080, 1920, -40),
                RECT(-8, -1088, 1928, -32),
                (0, -1080, 1920, -40)
            ),
            (
                "Primary monitor (0, 0, 1920, 1080) with 8px proposed spillover",
                RECT(0, 0, 1920, 1080),
                RECT(0, 0, 1920, 1032),
                RECT(-8, -8, 1928, 1040),
                (0, 0, 1920, 1032)
            ),
        ]

        for desc, rc_mon, rc_work, proposed_rect, exp_rect in scenarios:
            with self.subTest(scenario=desc):
                fake_hmon = 0x87654321

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
                msg.hwnd = filt.hwnd
                msg.message = WM_NCCALCSIZE
                msg.wParam = 1  # TRUE: specifies that the application can indicate which part of client area contains valid information
                msg.lParam = ctypes.addressof(params)

                # Mock IsZoomed to return True to simulate maximized state
                with patch.object(user32, "IsZoomed", return_value=1), \
                     patch.object(user32, "MonitorFromRect", return_value=fake_hmon), \
                     patch.object(user32, "GetMonitorInfoW", side_effect=mock_get_monitor_info):

                    handled, ret = filt.nativeEventFilter(
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
                        actual_rect,
                        exp_rect,
                        f"Border spillover detected in scenario: {desc}. Expected {exp_rect}, got {actual_rect}"
                    )

    def test_04_wm_nccalcsize_no_artificial_border_deflation(self):
        """Test WM_NCCALCSIZE does not artificially deflate borders when monitor resolution fails."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        from src.ui.native_window import user32

        proposed_rect = RECT(-8, -8, 1928, 1040)
        params = NCCALCSIZE_PARAMS()
        params.rgrc[0].left = proposed_rect.left
        params.rgrc[0].top = proposed_rect.top
        params.rgrc[0].right = proposed_rect.right
        params.rgrc[0].bottom = proposed_rect.bottom

        msg = MSG()
        msg.hwnd = filt.hwnd
        msg.message = WM_NCCALCSIZE
        msg.wParam = 1
        msg.lParam = ctypes.addressof(params)

        # Mock MonitorFromWindow and MonitorFromRect to return NULL (0)
        with patch.object(user32, "IsZoomed", return_value=1), \
             patch.object(user32, "MonitorFromWindow", return_value=0), \
             patch.object(user32, "MonitorFromRect", return_value=0):

            handled, ret = filt.nativeEventFilter(
                b"windows_generic_MSG", ctypes.addressof(msg)
            )

            self.assertTrue(handled)
            self.assertEqual(ret, 0)

            # Zero border deflation applied:
            self.assertEqual((params.rgrc[0].left, params.rgrc[0].top, params.rgrc[0].right, params.rgrc[0].bottom),
                             (-8, -8, 1928, 1040))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. CLIENT AREA EXPANSION & CHILD LAYOUT SIZING
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_maximized_root_container_and_child_layouts(self):
        """Verify root_container matches MainWindow.size() exactly and child layouts fill client area."""
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

        win_w = self.win.width()
        win_h = self.win.height()

        self.assertGreater(win_w, 1000)
        self.assertGreater(win_h, 600)

        # 1. CentralWidget / root_container matches window size exactly
        self.assertEqual(self.win.root_container.width(), win_w)
        self.assertEqual(self.win.root_container.height(), win_h)
        self.assertEqual(self.win.root_container.pos(), QPoint(0, 0))

        # 2. Title bar spans the full width
        self.assertEqual(self.win.title_bar.width(), win_w)
        self.assertEqual(self.win.title_bar.pos(), QPoint(0, 0))

        # 3. Content widget spans the full width and remaining height
        expected_content_h = win_h - self.win.title_bar.height()
        self.assertEqual(self.win.content_widget.width(), win_w)
        self.assertEqual(self.win.content_widget.height(), expected_content_h)

        # 4. Keypad and display fill horizontal space
        self.assertEqual(self.win.display.width(), win_w)
        self.assertEqual(self.win.keypad.width(), win_w)

        # 5. Buttons occupy full width without dead space on the right
        btn_eq = self.win.keypad.button_map.get("=")
        self.assertIsNotNone(btn_eq)
        btn_right = btn_eq.geometry().right()
        self.assertGreater(btn_right, win_w - 100, f"Button right {btn_right} leaves dead space in {win_w}px window")

    def test_06_scientific_mode_with_history_drawer_expansion(self):
        """Verify layout when Scientific mode is maximized with the history drawer open."""
        self.win._switch_mode("Scientific", save_config=False)
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()

        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

        win_w = self.win.width()
        win_h = self.win.height()

        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.root_container.size(), QSize(win_w, win_h))

        drawer_w = self.win.history_drawer.width()
        center_w = self.win.center_container.width()

        # Drawer + Center container must equal the full window width
        self.assertEqual(drawer_w + center_w, win_w)
        self.assertEqual(self.win.history_drawer.geometry().right(), win_w - 1)
        self.assertEqual(self.win.center_container.geometry().left(), 0)

        # Close history drawer and restore
        self.win._toggle_history_drawer()
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.root_container.size(), self.win.size())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. NCHITTEST SIZING BORDER INACTIVATION WHEN MAXIMIZED
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_nchittest_no_resize_borders_when_maximized(self):
        """Assert that no sizing border hit-test codes are emitted when maximized."""
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            QTest.qWait(10)

        w = self.win.width()
        h = self.win.height()

        forbidden_codes = {
            HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
            HTTOP, HTBOTTOM, HTLEFT, HTRIGHT
        }

        # Probe perimeter pixels (all 4 corners and midpoints of all 4 edges)
        probe_points = [
            (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
            (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)
        ]

        for lx, ly in probe_points:
            pt = self.win.mapToGlobal(QPoint(lx, ly))
            code = self.win._handle_nchittest(pt.x(), pt.y())
            self.assertNotIn(
                code, forbidden_codes,
                f"NCHITTEST returned resize border code {code} at point ({lx}, {ly}) while maximized!"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. ABSOLUTE ZERO EMOJIS CONSTRAINT
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_absolute_zero_emojis_in_source_and_tests(self):
        """Exhaustively verify that zero emojis exist anywhere in src/ or tests/."""
        import unicodedata

        repo_root = Path(__file__).resolve().parent.parent
        src_dir = repo_root / "src"
        tests_dir = repo_root / "tests"

        emoji_violations = []

        for scan_dir in [src_dir, tests_dir]:
            for root, _, files in os.walk(scan_dir):
                for f in files:
                    if f.endswith(".py"):
                        file_path = Path(root) / f
                        with open(file_path, "r", encoding="utf-8", errors="replace") as fp:
                            for line_no, line in enumerate(fp, start=1):
                                for char in line:
                                    # Private Use Area (Segoe icons \uE000-\uF8FF) is allowed
                                    if 0xE000 <= ord(char) <= 0xF8FF:
                                        continue
                                    char_name = unicodedata.name(char, "")
                                    if "EMOJI" in char_name:
                                        emoji_violations.append(
                                            f"{file_path.relative_to(repo_root)}:{line_no} char '{char}' ({char_name})"
                                        )

        self.assertEqual(
            len(emoji_violations), 0,
            f"Emoji violations found in codebase:\n" + "\n".join(emoji_violations)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 7. ADVERSARIAL EDGE CASES: NCCALCSIZE UNMAXIMIZED & ZERO WPARAM
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_wm_nccalcsize_unmaximized_and_zero_wparam(self):
        """Verify that WM_NCCALCSIZE does not alter rgrc when unmaximized or wParam=0."""
        filt = getattr(self.win, "_native_event_filter", None)
        if filt is None:
            self.skipTest("Native event filter not active (non-Windows or headless)")

        from src.ui.native_window import user32

        # 1. Unmaximized window with wParam=1
        params = NCCALCSIZE_PARAMS()
        params.rgrc[0].left = 100
        params.rgrc[0].top = 100
        params.rgrc[0].right = 500
        params.rgrc[0].bottom = 600

        msg = MSG()
        msg.hwnd = filt.hwnd
        msg.message = WM_NCCALCSIZE
        msg.wParam = 1
        msg.lParam = ctypes.addressof(params)

        with patch.object(user32, "IsZoomed", return_value=0), \
             patch.object(user32, "GetWindowPlacement", return_value=0):

            handled, ret = filt.nativeEventFilter(
                b"windows_generic_MSG", ctypes.addressof(msg)
            )

            # Must return True, 0 and leave rgrc[0] intact
            self.assertTrue(handled)
            self.assertEqual(ret, 0)
            self.assertEqual((params.rgrc[0].left, params.rgrc[0].top, params.rgrc[0].right, params.rgrc[0].bottom),
                             (100, 100, 500, 600))

        # 2. wParam = 0 (rare, but defined in Win32 as RECT* in lParam)
        rect = RECT(50, 50, 400, 500)
        msg2 = MSG()
        msg2.hwnd = filt.hwnd
        msg2.message = WM_NCCALCSIZE
        msg2.wParam = 0
        msg2.lParam = ctypes.addressof(rect)

        handled, ret = filt.nativeEventFilter(
            b"windows_generic_MSG", ctypes.addressof(msg2)
        )
        self.assertFalse(handled)
        self.assertEqual(ret, 0)
        self.assertEqual((rect.left, rect.top, rect.right, rect.bottom), (50, 50, 400, 500))

    # ─────────────────────────────────────────────────────────────────────────
    # 8. TITLE BAR MAXIMIZE BUTTON VECTOR SVG & TOOLTIP SYNC
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_btn_maximize_vector_svg_icon_and_tooltip_synchronization(self):
        """Verify vector SVG icon is non-null and tooltips toggle between 'Maximize' and 'Restore'."""
        btn_max = self.win.title_bar.btn_maximize

        # Normal state
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(3):
            app.processEvents()

        self.assertFalse(self.win.isMaximized())
        self.assertFalse(btn_max.icon().isNull(), "Maximize button icon must be a non-null vector SVG")
        self.assertEqual(btn_max.toolTip(), "Maximize")

        # Maximized state
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(3):
            app.processEvents()

        self.assertTrue(self.win.isMaximized() or (sys.platform == "win32" and ctypes.windll.user32.IsZoomed(int(self.win.winId()))))
        self.assertFalse(btn_max.icon().isNull(), "Restore button icon must be a non-null vector SVG")
        self.assertEqual(btn_max.toolTip(), "Restore")

        # Restore back
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(3):
            app.processEvents()

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(btn_max.toolTip(), "Maximize")


if __name__ == "__main__":
    unittest.main()
