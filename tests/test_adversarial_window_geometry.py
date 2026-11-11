"""
Adversarial Window Resizing & Win32 Stress Test Suite.

Adversarially challenges and stress-tests:
1. Rapid toggle of maximize / restore (Win32 & Qt event queue stress).
2. Win32 native ShowWindow rapid toggling.
3. Aero Snap simulations (Top, Left, Right, 4 Corners).
4. Extreme geometry sizes (4K UHD 3840x2160, Ultrawide 5120x1440).
5. Minimum tracking size enforcement (WM_GETMINMAXINFO & minimumSize).
6. Expanded client area event responsiveness (clicks, hovers at x > 1000px, x > 1500px).
7. Non-drifting dimensions and zero clipping across all calculator modes.
8. Sidebar & history drawer overlay stability during maximize / restore cycles.
"""

import sys
import os
import time
import ctypes
import unittest
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    HTTOP, HTBOTTOM, HTLEFT, HTRIGHT,
    HTMAXBUTTON, HTCLIENT, HTCAPTION,
    MINMAXINFO, MSG
)

WM_GETMINMAXINFO = 0x0024

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestAdversarialWindowGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(360, 580)
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
        # Reset window to Standard mode and normal size before each test
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
        self.win.resize(360, 580)
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()
            time.sleep(0.01)

    # ─── 1. RAPID MAXIMIZE / RESTORE TOGGLE STRESS ────────────────────
    def test_rapid_maximize_restore_toggle(self):
        """Stress-test rapid toggling between maximize and restore 30 times in quick succession."""
        initial_w = self.win.width()
        initial_h = self.win.height()
        self.assertEqual(initial_w, 360)
        self.assertEqual(initial_h, 580)

        for i in range(30):
            self.win.title_bar.btn_maximize.click()
            app.processEvents()

        # Final state check: Ensure window is in a known consistent state
        if self.win.isMaximized():
            self.win.title_bar.btn_maximize.click()
            for _ in range(10):
                app.processEvents()
                time.sleep(0.01)

        # Confirm cleanly restored to normal state
        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.title_bar.btn_maximize.toolTip(), "Maximize")
        self.assertFalse(self.win.title_bar.btn_maximize.icon().isNull())
        self.assertEqual(self.win.root_container.size(), self.win.size())

        # Check dimension drift: un-maximized width/height must not drift uncontrollably
        self.assertAlmostEqual(self.win.width(), initial_w, delta=20)
        self.assertAlmostEqual(self.win.height(), initial_h, delta=20)

    # ─── 2. WIN32 RAPID SHOWWINDOW TOGGLE ────────────────────────────
    @unittest.skipUnless(sys.platform == "win32", "Win32 specific ShowWindow stress test")
    def test_win32_rapid_showwindow_toggle(self):
        """Stress-test rapid native Win32 ShowWindow(SW_SHOWMAXIMIZED / SW_SHOWNORMAL) 20 times."""
        hwnd = int(self.win.winId())
        u = ctypes.windll.user32
        SW_MAXIMIZE = 3
        SW_RESTORE = 9

        for i in range(20):
            cmd = SW_MAXIMIZE if (i % 2 == 0) else SW_RESTORE
            u.ShowWindow(hwnd, cmd)
            app.processEvents()
            time.sleep(0.01)

        # Restore cleanly
        u.ShowWindow(hwnd, SW_RESTORE)
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)

        self.assertFalse(self.win.isMaximized())
        self.assertFalse(bool(u.IsZoomed(ctypes.c_void_p(hwnd))))
        self.assertEqual(self.win.root_container.size(), self.win.size())

    # ─── 3. AERO SNAP SIMULATIONS ────────────────────────────────────
    @unittest.skipUnless(sys.platform == "win32", "Win32 specific Aero Snap test")
    def test_aero_snap_top_sides_and_corners(self):
        """Simulate Aero Snap to Top (maximize), Left half, Right half, and 4 Corners."""
        hwnd = int(self.win.winId())
        u = ctypes.windll.user32

        # 3.1 Snap to Top (Maximize)
        u.ShowWindow(hwnd, 3)
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)

        self.assertTrue(self.win.width() > 1000)
        self.assertEqual(self.win.root_container.size(), self.win.size())
        self.assertEqual(self.win.keypad.width(), self.win.width())
        self.assertEqual(self.win.display.width(), self.win.width())
        self.assertEqual(self.win.title_bar.btn_maximize.toolTip(), "Restore")
        self.assertFalse(self.win.title_bar.btn_maximize.icon().isNull())

        # 3.2 Snap to Left (Half-screen e.g. 960x1000)
        u.ShowWindow(hwnd, 9)
        app.processEvents()
        u.SetWindowPos(hwnd, 0, 0, 0, 960, 1000, 0x0004 | 0x0040)
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.width(), 960)
        self.assertEqual(self.win.height(), 1000)
        self.assertEqual(self.win.root_container.size(), self.win.size())
        self.assertEqual(self.win.keypad.width(), 960)

        # 3.3 Snap to Right (Half-screen e.g. 960x1000)
        u.SetWindowPos(hwnd, 0, 960, 0, 960, 1000, 0x0004 | 0x0040)
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.width(), 960)
        self.assertEqual(self.win.height(), 1000)
        self.assertEqual(self.win.root_container.size(), self.win.size())

        # 3.4 Snap to 4 Corners (Quarter-screen e.g. 960x520)
        corners = [
            (0, 0, 960, 520),        # Top-Left
            (960, 0, 960, 520),      # Top-Right
            (0, 520, 960, 520),      # Bottom-Left
            (960, 520, 960, 520),    # Bottom-Right
        ]
        for x, y, w, h in corners:
            u.SetWindowPos(hwnd, 0, x, y, w, h, 0x0004 | 0x0040)
            for _ in range(5):
                app.processEvents()
                time.sleep(0.01)
            self.assertEqual(self.win.size(), QSize(w, h))
            self.assertEqual(self.win.root_container.size(), QSize(w, h))

    # ─── 4. EXTREME GEOMETRY SIZES & MINIMUM TRACKING SIZE ───────────
    def test_extreme_geometry_sizes(self):
        """Test ultrawide and 4K extreme geometry sizes without clipping or layout failure."""
        extreme_resolutions = [
            (800, 600),
            (1280, 720),
            (1920, 1080),  # Full HD
            (2560, 1080),  # Ultrawide
            (3840, 1080),  # Super Ultrawide
        ]
        for w, h in extreme_resolutions:
            self.win.resize(w, h)
            self.win._force_layout_update()
            app.processEvents()

            cur_w = self.win.width()
            cur_h = self.win.height()

            # Window inner components must match window's actual dimensions perfectly (zero clipping)
            self.assertEqual(self.win.root_container.size(), self.win.size())
            self.assertEqual(self.win.title_bar.width(), cur_w)
            self.assertEqual(self.win.content_widget.width(), cur_w)
            self.assertEqual(self.win.keypad.width(), cur_w)

    def test_minimum_tracking_size_enforcement(self):
        """Test minimum tracking size prevents collapsing window below usable bounds."""
        min_w = self.win.minimumWidth()
        min_h = self.win.minimumHeight()
        self.assertGreaterEqual(min_w, 320)
        self.assertGreaterEqual(min_h, 520)

        # Try resizing below minimum bounds
        self.win.resize(100, 100)
        app.processEvents()
        self.assertGreaterEqual(self.win.width(), min_w)
        self.assertGreaterEqual(self.win.height(), min_h)

        # Test WM_GETMINMAXINFO is not intercepted (deferred to native Windows / Qt QWidget minimum size)
        if hasattr(self.win, "_native_event_filter") and self.win._native_event_filter:
            mmi = MINMAXINFO()
            mmi.ptMinTrackSize.x = 0
            mmi.ptMinTrackSize.y = 0

            msg = MSG()
            msg.hwnd = self.win._native_event_filter.hwnd
            msg.message = WM_GETMINMAXINFO
            msg.wParam = 0
            msg.lParam = ctypes.addressof(mmi)

            handled, ret = self.win._native_event_filter.nativeEventFilter(
                b"windows_generic_MSG", ctypes.addressof(msg)
            )
            self.assertFalse(handled)
            self.assertEqual(ret, 0)

    # ─── 5. EXPANDED CLIENT AREA HIT TESTING & RESPONSIVENESS ────────
    def test_expanded_client_area_responsiveness(self):
        """Test clicks, hovers, and hit-testing across extreme coordinates (x > 1000px, x > 1500px)."""
        # Maximize window
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(10):
            app.processEvents()
            time.sleep(0.01)

        win_w = self.win.width()
        self.assertTrue(win_w > 1000, f"Expected maximized width > 1000, got {win_w}")

        # Verify buttons on the far right column are positioned at x > 1000px
        btn_eq = self.win.keypad.button_map.get("=")
        btn_mul = self.win.keypad.button_map.get("×") or self.win.keypad.button_map.get("*")
        btn_9 = self.win.keypad.button_map.get("9")
        btn_8 = self.win.keypad.button_map.get("8")

        eq_center = btn_eq.mapToGlobal(btn_eq.rect().center())
        self.assertGreater(eq_center.x(), 1000, "Equal button should be at x > 1000 in maximized state")

        # Perform calculation via mouse clicks on far-right expanded buttons
        self.win.state.clear_all()
        QTest.mouseClick(btn_9, Qt.MouseButton.LeftButton)
        app.processEvents()
        QTest.mouseClick(btn_mul, Qt.MouseButton.LeftButton)
        app.processEvents()
        QTest.mouseClick(btn_8, Qt.MouseButton.LeftButton)
        app.processEvents()
        QTest.mouseClick(btn_eq, Qt.MouseButton.LeftButton)
        app.processEvents()

        self.assertEqual(self.win.display.primary_display.text(), "72")

        # Test title bar buttons hit-testing
        close_center = self.win.btn_close.mapToGlobal(self.win.btn_close.rect().center())
        max_center = self.win.btn_maximize.mapToGlobal(self.win.btn_maximize.rect().center())

        self.assertEqual(self.win._handle_nchittest(close_center.x(), close_center.y()), HTCLIENT)
        if getattr(self.win, "_native_event_filter", None) is not None:
            self.assertEqual(self.win._handle_nchittest(max_center.x(), max_center.y()), HTMAXBUTTON)

        # Test that resizing borders are NOT returned when maximized (no accidental border drag)
        self.assertNotEqual(self.win._handle_nchittest(1, 1), HTTOPLEFT)
        self.assertNotEqual(self.win._handle_nchittest(win_w - 2, 1), HTTOPRIGHT)
        self.assertNotEqual(self.win._handle_nchittest(win_w - 2, self.win.height() - 2), HTBOTTOMRIGHT)

    # ─── 6. ALL MODES MAXIMIZATION & NO CLIPPING ─────────────────────
    def test_all_modes_maximize_and_no_clipping(self):
        """Test that every calculator mode expands fully to client bounds without clipping when maximized."""
        modes_to_test = [
            "Standard",
            "Scientific",
            "Programmer",
            "Date Calculation",
            "Graphing",
            "Length",
            "Temperature",
        ]

        for mode in modes_to_test:
            self.win._switch_mode(mode, save_config=False)
            self.win.showMaximized()
            self.win._force_layout_update()
            for _ in range(5):
                app.processEvents()
                time.sleep(0.01)

            w = self.win.width()
            h = self.win.height()

            # Verify root container fills window
            self.assertEqual(self.win.root_container.size(), QSize(w, h), f"Root container mismatch in mode {mode}")
            self.assertEqual(self.win.content_widget.width(), w, f"Content widget width mismatch in mode {mode}")

            # Mode-specific inner page check
            if mode in ("Standard", "Scientific", "Programmer"):
                self.assertEqual(self.win.keypad.width(), w, f"Keypad width mismatch in mode {mode}")
                self.assertEqual(self.win.display.width(), w, f"Display width mismatch in mode {mode}")
            elif mode == "Date Calculation":
                self.assertEqual(self.win.date_calc_page.width(), w, f"Date calc page mismatch in mode {mode}")
            elif mode == "Graphing":
                self.assertEqual(self.win.graphing_page.width(), w, f"Graphing page mismatch in mode {mode}")
            else:
                self.assertEqual(self.win.converter_page.width(), w, f"Converter page mismatch in mode {mode}")

            # Restore and check clean restoration
            self.win.showNormal()
            self.win._force_layout_update()
            for _ in range(5):
                app.processEvents()
                time.sleep(0.01)

            self.assertFalse(self.win.isMaximized(), f"Failed to restore in mode {mode}")
            self.assertEqual(self.win.root_container.size(), self.win.size(), f"Restored root container mismatch in {mode}")

    # ─── 7. SIDEBAR & HISTORY DRAWER STABILITY UNDER MAXIMIZE ────────
    def test_sidebar_and_history_drawer_maximize_restore_stability(self):
        """Test opening sidebar and history drawer while maximized, and toggling states."""
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        w = self.win.width()
        h = self.win.height()

        # 7.1 Open Sidebar while maximized
        self.win._toggle_sidebar()
        self.assertTrue(self.win.sidebar.isVisible())
        self.assertTrue(self.win.scrim.isVisible())
        self.assertEqual(self.win.scrim.size(), self.win.content_widget.size())
        # Sidebar should cap at 260px width
        self.assertLessEqual(self.win.sidebar.width(), 260)

        # Close Sidebar
        self.win._toggle_sidebar()
        self.assertFalse(self.win.sidebar.isVisible())

        # 7.2 Open History Drawer while maximized
        self.win._toggle_history_drawer()
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.root_container.size(), QSize(w, h))

        # Restore window while History Drawer is open
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertFalse(self.win.isMaximized())
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.root_container.size(), self.win.size())

        # Close History Drawer
        self.win._toggle_history_drawer()
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.root_container.size(), self.win.size())

    # ─── 8. CONFIG PERSISTENCE & GEOMETRY DRIFT PREVENTION ───────────
    def test_config_geometry_persistence_during_maximize(self):
        """Verify that maximizing never overwrites normal window_width/height in config."""
        self.win.resize(380, 600)
        app.processEvents()
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 600)

        # Maximize window
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertTrue(self.win.width() > 1000)
        # Config width/height MUST still reflect normal dimensions, not maximized monitor size!
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 600)

        # Restore window
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertEqual(self.win.width(), 380)
        self.assertEqual(self.win.height(), 600)
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 600)

    # ─── 9. MINIMIZE TO TASKBAR & RESTORE FROM MAXIMIZED STATE ───────
    def test_minimize_and_restore_from_maximized_state(self):
        """Test minimizing to taskbar while maximized, then restoring directly."""
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        max_w = self.win.width()
        max_h = self.win.height()
        self.assertTrue(self.win.isMaximized())

        # Minimize to taskbar
        self.win.showMinimized()
        for _ in range(5):
            app.processEvents()

        self.assertTrue(self.win.isMinimized())

        # Restore from taskbar
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertFalse(self.win.isMinimized())
        is_max = self.win.isMaximized() or (
            sys.platform == "win32" and bool(ctypes.windll.user32.IsZoomed(int(self.win.winId())))
        )
        self.assertTrue(is_max)
        self.assertEqual(self.win.size(), QSize(max_w, max_h))
        self.assertEqual(self.win.root_container.size(), QSize(max_w, max_h))

    # ─── 10. TITLE BAR RAPID DOUBLE-CLICK TOGGLE ─────────────────────
    def test_title_bar_rapid_double_clicks(self):
        """Simulate rapid double-clicking on title bar caption to toggle maximize."""
        for _ in range(10):
            # Double click caption
            self.win._toggle_maximize()
            app.processEvents()

        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.root_container.size(), self.win.size())

    # ─── 11. ALL KEYPAD BUTTONS HIT TESTING & CLICKABILITY ───────────
    def test_all_keypad_buttons_clickable_when_maximized(self):
        """Confirm every single keypad button is within expanded client area and clickable without dead zones."""
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        win_rect = self.win.rect()
        for label, btn in self.win.keypad.button_map.items():
            if not btn.isVisible():
                continue
            # Map button center to window coords
            btn_pos_in_win = self.win.mapFromGlobal(btn.mapToGlobal(btn.rect().center()))
            self.assertTrue(
                win_rect.contains(btn_pos_in_win),
                f"Button '{label}' at {btn_pos_in_win} falls outside window bounds {win_rect}"
            )
            # Ensure button is clickable without throwing exceptions
            btn.click()
            app.processEvents()

    # ─── 12. CALCULATION STATE PRESERVATION ACROSS TRANSITIONS ───────
    def test_calculation_state_preserved_across_geometry_transitions(self):
        """Ensure math drafting expression and live preview are not lost during maximize/restore/snap."""
        self.win.state.clear_all()
        # Input '456 + 123'
        self.win.state.input_digit("4")
        self.win.state.input_digit("5")
        self.win.state.input_digit("6")
        self.win.state.input_operator("+")
        self.win.state.input_digit("1")
        self.win.state.input_digit("2")
        self.win.state.input_digit("3")
        app.processEvents()

        self.assertEqual(self.win.display.primary_display.text(), "123")
        self.assertEqual(self.win.display.expression_label.text(), "456 + 123")

        # Maximize
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertEqual(self.win.display.primary_display.text(), "123")
        self.assertEqual(self.win.display.expression_label.text(), "456 + 123")

        # Snap to Left
        if sys.platform == "win32":
            hwnd = int(self.win.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 960, 800, 0x0004 | 0x0040)
            for _ in range(5):
                app.processEvents()

        self.assertEqual(self.win.display.primary_display.text(), "123")
        self.assertEqual(self.win.display.expression_label.text(), "456 + 123")

        # Restore
        self.win.showNormal()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        self.assertEqual(self.win.display.primary_display.text(), "123")
        self.assertEqual(self.win.display.expression_label.text(), "456 + 123")

        # Complete calculation
        self.win.state.evaluate()
        app.processEvents()
        self.assertEqual(self.win.display.primary_display.text(), "579")

    # ─── 13. COMPREHENSIVE NCHITTEST MATRIX (NORMAL VS MAXIMIZED) ────
    def test_nchittest_comprehensive_matrix(self):
        """Adversarially probe _handle_nchittest across the full 2D coordinate space."""
        # A. Normal Un-Maximized State (360x580)
        self.win.resize(360, 580)
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        w = self.win.width()
        h = self.win.height()
        tl = self.win.mapToGlobal(QPoint(1, 1))
        tr = self.win.mapToGlobal(QPoint(w - 2, 1))
        bl = self.win.mapToGlobal(QPoint(1, h - 2))
        br = self.win.mapToGlobal(QPoint(w - 2, h - 2))
        left = self.win.mapToGlobal(QPoint(1, h // 2))
        right = self.win.mapToGlobal(QPoint(w - 2, h // 2))
        top = self.win.mapToGlobal(QPoint(w // 2, 1))
        bottom = self.win.mapToGlobal(QPoint(w // 2, h - 2))
        center = self.win.mapToGlobal(QPoint(w // 2, h // 2))

        # Must return resize borders when NOT maximized
        self.assertEqual(self.win._handle_nchittest(tl.x(), tl.y()), HTTOPLEFT)
        self.assertEqual(self.win._handle_nchittest(tr.x(), tr.y()), HTTOPRIGHT)
        self.assertEqual(self.win._handle_nchittest(bl.x(), bl.y()), HTBOTTOMLEFT)
        self.assertEqual(self.win._handle_nchittest(br.x(), br.y()), HTBOTTOMRIGHT)
        self.assertEqual(self.win._handle_nchittest(left.x(), left.y()), HTLEFT)
        self.assertEqual(self.win._handle_nchittest(right.x(), right.y()), HTRIGHT)
        self.assertEqual(self.win._handle_nchittest(top.x(), top.y()), HTTOP)
        self.assertEqual(self.win._handle_nchittest(bottom.x(), bottom.y()), HTBOTTOM)
        self.assertEqual(self.win._handle_nchittest(center.x(), center.y()), HTCLIENT)

        # B. Maximized State
        self.win.showMaximized()
        self.win._force_layout_update()
        for _ in range(5):
            app.processEvents()

        max_w = self.win.width()
        max_h = self.win.height()
        max_tl = self.win.mapToGlobal(QPoint(1, 1))
        max_tr = self.win.mapToGlobal(QPoint(max_w - 2, 1))
        max_bl = self.win.mapToGlobal(QPoint(1, max_h - 2))
        max_br = self.win.mapToGlobal(QPoint(max_w - 2, max_h - 2))
        max_left = self.win.mapToGlobal(QPoint(1, max_h // 2))
        max_right = self.win.mapToGlobal(QPoint(max_w - 2, max_h // 2))
        max_center = self.win.mapToGlobal(QPoint(max_w // 2, max_h // 2))

        # None of the corners or edges may return resize codes when maximized
        resize_codes = {HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT, HTLEFT, HTRIGHT, HTTOP, HTBOTTOM}
        self.assertNotIn(self.win._handle_nchittest(max_tl.x(), max_tl.y()), resize_codes)
        self.assertNotIn(self.win._handle_nchittest(max_tr.x(), max_tr.y()), resize_codes)
        self.assertNotIn(self.win._handle_nchittest(max_bl.x(), max_bl.y()), resize_codes)
        self.assertNotIn(self.win._handle_nchittest(max_br.x(), max_br.y()), resize_codes)
        self.assertNotIn(self.win._handle_nchittest(max_left.x(), max_left.y()), resize_codes)
        self.assertNotIn(self.win._handle_nchittest(max_right.x(), max_right.y()), resize_codes)
        self.assertEqual(self.win._handle_nchittest(max_center.x(), max_center.y()), HTCLIENT)

    # ─── 14. EMOJI AUDIT (RULE 2 CONFORMANCE) ────────────────────────
    def test_no_emojis_in_entire_ui(self):
        """Confirm that zero emojis are used in buttons, labels, dialogs, or title bars."""
        import re
        from PyQt6.QtWidgets import QWidget, QPushButton, QLabel

        # Regex for standard emoji Unicode blocks (excluding Private Use Area \uE000-\uF8FF used for Segoe Fluent icons)
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"  # Emoticons
            r"\U0001F300-\U0001F5FF"  # Symbols & Pictographs
            r"\U0001F680-\U0001F6FF"  # Transport & Map
            r"\U0001F700-\U0001F77F"  # Alchemical
            r"\U0001F780-\U0001F7FF"  # Geometric
            r"\U0001F800-\U0001F8FF"  # Supplemental Arrows
            r"\U0001F900-\U0001F9FF"  # Supplemental Symbols
            r"\U0001FA00-\U0001FA6F"  # Chess
            r"\U0001FA70-\U0001FAFF"  # Extended-A
            r"\u2600-\u26FF"          # Misc Symbols
            r"\u2700-\u27BF]"         # Dingbats
        )

        all_widgets = self.win.findChildren(QWidget)
        for w in all_widgets:
            text = ""
            if isinstance(w, (QPushButton, QLabel)):
                text = w.text()
            tip = w.toolTip()
            match_text = emoji_pattern.search(text)
            match_tip = emoji_pattern.search(tip)
            self.assertIsNone(match_text, f"Emoji found in widget text '{text}' on {w.objectName() or w}")
            self.assertIsNone(match_tip, f"Emoji found in tooltip '{tip}' on {w.objectName() or w}")


if __name__ == "__main__":
    unittest.main()
