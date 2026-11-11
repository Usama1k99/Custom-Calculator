"""
Independent Empirical Challenger Test Suite for Milestone 4.
Validates:
1. 25+ rapid consecutive maximize and restore cycles ensuring zero geometry drift or creep.
2. Opening and closing history drawer while maximized (window must remain maximized, no un-maximize).
3. Opening history drawer in normal mode, maximizing, closing history drawer while maximized,
   then restoring to normal (must cleanly return to 380px compact width).
4. Toggling always-on-top while maximized (must remain maximized, zero flicker).
5. Switching calculator modes while maximized across all modes (must remain maximized).
6. Verifying data/config.json never persists maximized dimensions (width/height > 1000).
7. Interactive calculation consistency across rapid geometry transitions.
Zero emojis used anywhere.
"""

import sys
import os
import json
import time
import ctypes
from ctypes import wintypes
import unittest
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QSize, QRect
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.core.config import ConfigManager
from src.ui.converter_view import CONVERSION_FACTORS

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMilestone4EmpiricalStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = REPO_ROOT / "data" / "config.json"
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(380, 560)
        cls.win.show()
        cls._pump_events(10)

        cls.hwnd = int(cls.win.winId()) if sys.platform == "win32" else 0
        cls.u = ctypes.windll.user32 if sys.platform == "win32" else None

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls.win, "_native_event_filter") and cls.win._native_event_filter:
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeNativeEventFilter(cls.win._native_event_filter)
            cls.win._native_event_filter = None
        cls.win.close()
        cls._pump_events(5)

    @classmethod
    def _pump_events(cls, count: int = 5):
        for _ in range(count):
            app.processEvents()
            QTest.qWait(12)

    def setUp(self):
        # Reset window to Standard mode and restored 380x560 geometry
        self.win._switch_mode("Standard", save_config=False)
        if sys.platform == "win32":
            if self.u.IsZoomed(wintypes.HWND(self.hwnd)) or self.win.isMaximized():
                self.u.ShowWindow(self.hwnd, 9)  # SW_RESTORE
                self.win.showNormal()
        elif self.win.isMaximized():
            self.win.showNormal()

        if hasattr(self.win, "history_drawer") and self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
        if hasattr(self.win, "sidebar") and self.win.sidebar.isVisible():
            self.win._toggle_sidebar()

        self.win.resize(380, 560)
        self.win.config.set("window_width", 380, auto_save=True)
        self.win.config.set("window_height", 560, auto_save=True)
        self._pump_events(5)

    def _is_zoomed(self) -> bool:
        if sys.platform == "win32" and self.u:
            return bool(self.u.IsZoomed(wintypes.HWND(self.hwnd)))
        return self.win.isMaximized()

    # =========================================================================
    # TEST 1: 25+ RAPID CONSECUTIVE MAXIMIZE / RESTORE CYCLES — ZERO DRIFT
    # =========================================================================
    def test_01_rapid_consecutive_maximize_restore_cycles(self):
        """Stress-test 30 consecutive maximize/restore cycles: assert zero geometry drift or creep."""
        initial_w = self.win.width()
        initial_h = self.win.height()
        self.assertEqual(initial_w, 380)
        self.assertEqual(initial_h, 560)

        for cycle in range(30):
            # 1. Maximize
            self.win.title_bar.btn_maximize.click()
            self._pump_events(3)

            self.assertTrue(self.win.isMaximized() or self._is_zoomed(), f"Failed to maximize on cycle {cycle}")
            self.assertEqual(self.win.root_container.size(), self.win.size())
            self.assertEqual(self.win.title_bar.btn_maximize.toolTip(), "Restore")
            self.assertGreater(self.win.width(), 1000)

            # 2. Restore
            self.win.title_bar.btn_maximize.click()
            self._pump_events(3)

            self.assertFalse(self.win.isMaximized(), f"Failed to restore on cycle {cycle}")
            self.assertFalse(self._is_zoomed(), f"IsZoomed still True after restore on cycle {cycle}")
            self.assertEqual(self.win.root_container.size(), self.win.size())
            self.assertEqual(self.win.title_bar.btn_maximize.toolTip(), "Maximize")

        # Verify zero geometry drift or creep after 30 cycles
        final_w = self.win.width()
        final_h = self.win.height()
        self.assertAlmostEqual(final_w, initial_w, delta=1,
                               msg=f"Width drifted from {initial_w} to {final_w} after 30 cycles")
        self.assertAlmostEqual(final_h, initial_h, delta=1,
                               msg=f"Height drifted from {initial_h} to {final_h} after 30 cycles")

        # Config dimensions must remain intact at normal dimensions
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 560)

    # =========================================================================
    # TEST 2: HISTORY DRAWER TOGGLE WHILE MAXIMIZED
    # =========================================================================
    def test_02_history_drawer_toggle_while_maximized(self):
        """Verify opening and closing history drawer while maximized never un-maximizes the window."""
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertTrue(self._is_zoomed())
        max_w = self.win.width()
        max_h = self.win.height()

        for cycle in range(10):
            # Open history drawer while maximized
            self.win._toggle_history_drawer()
            self._pump_events(3)

            self.assertTrue(self.win.history_drawer.isVisible(), f"History drawer should be visible (cycle {cycle})")
            self.assertTrue(self._is_zoomed(), f"Window un-maximized upon opening history drawer (cycle {cycle})")
            self.assertEqual(self.win.size(), QSize(max_w, max_h))
            self.assertEqual(self.win.history_drawer.width(), 290)
            self.assertEqual(
                self.win.center_container.width(),
                self.win.content_widget.width() - 290,
                "Center container should adapt to remaining width alongside history drawer"
            )

            # Close history drawer while maximized
            self.win._toggle_history_drawer()
            self._pump_events(3)

            self.assertFalse(self.win.history_drawer.isVisible(), f"History drawer should be hidden (cycle {cycle})")
            self.assertTrue(self._is_zoomed(), f"Window un-maximized upon closing history drawer (cycle {cycle})")
            self.assertEqual(self.win.size(), QSize(max_w, max_h))
            self.assertEqual(
                self.win.center_container.width(),
                self.win.content_widget.width(),
                "Center container should expand to full content width when history drawer closes"
            )

    # =========================================================================
    # TEST 3: OPEN DRAWER IN NORMAL -> MAXIMIZE -> CLOSE DRAWER -> RESTORE CLEAN
    # =========================================================================
    def test_03_drawer_normal_to_maximized_to_closed_to_clean_restore(self):
        """
        Critical test:
        1. Open history drawer in normal mode (window auto-expands from 380 to 630).
        2. Maximize window.
        3. Close history drawer while maximized.
        4. Restore to normal -> window MUST cleanly return to 380px compact width.
        """
        for repetition in range(5):
            # 1. Start in compact normal mode
            self.assertEqual(self.win.width(), 380)
            self.assertFalse(self._is_zoomed())

            # 2. Open drawer in normal mode
            self.win._toggle_history_drawer()
            self._pump_events(3)
            self.assertTrue(self.win.history_drawer.isVisible())
            expanded_normal_w = self.win.width()
            self.assertGreaterEqual(expanded_normal_w, 630, "Window should auto-expand when drawer opens in normal mode")

            # 3. Maximize
            self.win.title_bar.btn_maximize.click()
            self._pump_events(5)
            self.assertTrue(self._is_zoomed())
            self.assertTrue(self.win.history_drawer.isVisible())

            # 4. Close history drawer WHILE MAXIMIZED
            self.win._toggle_history_drawer()
            self._pump_events(3)
            self.assertFalse(self.win.history_drawer.isVisible())
            self.assertTrue(self._is_zoomed(), "Window must stay maximized when drawer is closed")

            # 5. Restore to normal
            self.win.title_bar.btn_maximize.click()
            self._pump_events(5)
            self.assertFalse(self._is_zoomed(), "Window must be restored")
            self.assertFalse(self.win.isMaximized())

            # Check clean restoration back to 380px compact width
            restored_w = self.win.width()
            restored_h = self.win.height()
            self.assertEqual(
                restored_w, 380,
                f"Repetition {repetition}: Window failed to return to 380px compact width, got {restored_w}"
            )
            self.assertEqual(
                restored_h, 560,
                f"Repetition {repetition}: Window height corrupted, got {restored_h}"
            )

    # =========================================================================
    # TEST 4: ALWAYS-ON-TOP TOGGLE WHILE MAXIMIZED (ZERO FLICKER / NO UN-MAXIMIZE)
    # =========================================================================
    def test_04_always_on_top_toggle_while_maximized(self):
        """Verify toggling always-on-top while maximized maintains maximize state seamlessly."""
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertTrue(self._is_zoomed())
        max_w = self.win.width()
        max_h = self.win.height()

        for cycle in range(20):
            # Toggle Pin On
            self.win.pin_btn.setChecked(True)
            self.win._toggle_always_on_top()
            self._pump_events(2)

            self.assertTrue(self._is_zoomed(), f"Cycle {cycle}: Window lost maximize state when pin enabled")
            self.assertEqual(self.win.size(), QSize(max_w, max_h))
            self.assertTrue(self.win.config.get("always_on_top"))

            # Win32 style check
            if sys.platform == "win32":
                WS_EX_TOPMOST = 0x00000008
                GWL_EXSTYLE = -20
                ex_style = self.u.GetWindowLongW(wintypes.HWND(self.hwnd), GWL_EXSTYLE)
                self.assertTrue(bool(ex_style & WS_EX_TOPMOST), f"Cycle {cycle}: WS_EX_TOPMOST not set in Win32")

            # Toggle Pin Off
            self.win.pin_btn.setChecked(False)
            self.win._toggle_always_on_top()
            self._pump_events(2)

            self.assertTrue(self._is_zoomed(), f"Cycle {cycle}: Window lost maximize state when pin disabled")
            self.assertEqual(self.win.size(), QSize(max_w, max_h))
            self.assertFalse(self.win.config.get("always_on_top"))

            if sys.platform == "win32":
                ex_style = self.u.GetWindowLongW(wintypes.HWND(self.hwnd), GWL_EXSTYLE)
                self.assertFalse(bool(ex_style & WS_EX_TOPMOST), f"Cycle {cycle}: WS_EX_TOPMOST still set in Win32")

    # =========================================================================
    # TEST 5: MODE SWITCHING WHILE MAXIMIZED
    # =========================================================================
    def test_05_mode_switching_while_maximized(self):
        """Verify switching modes while maximized preserves maximize state across all 18 modes."""
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertTrue(self._is_zoomed())
        max_w = self.win.width()
        max_h = self.win.height()

        all_modes = [
            "Standard",
            "Scientific",
            "Programmer",
            "Date Calculation",
            "Graphing",
        ] + list(CONVERSION_FACTORS.keys())

        for mode in all_modes:
            with self.subTest(mode=mode):
                self.win._switch_mode(mode, save_config=False)
                self._pump_events(3)

                self.assertTrue(self._is_zoomed(), f"Mode switch to '{mode}' broke maximize state")
                self.assertEqual(self.win.size(), QSize(max_w, max_h))
                self.assertEqual(self.win.root_container.size(), QSize(max_w, max_h))
                self.assertEqual(self.win.content_widget.size(), QSize(max_w, max_h - self.win.title_bar.height()))

                # Ensure active stack page is fully expanded
                cw = self.win.stack.currentWidget()
                self.assertIsNotNone(cw)
                self.assertEqual(cw.width(), self.win.center_container.width())

        # Rapid cycling back and forth between core modes
        core_modes = ["Standard", "Scientific", "Programmer", "Graphing", "Date Calculation"]
        for _ in range(3):
            for mode in core_modes:
                self.win._switch_mode(mode, save_config=False)
                self._pump_events(2)
                self.assertTrue(self._is_zoomed(), f"Rapid cycling mode '{mode}' broke maximize state")
                self.assertEqual(self.win.size(), QSize(max_w, max_h))

    # =========================================================================
    # TEST 6: CONFIG PERSISTENCE NEVER OVERWRITTEN WITH MAXIMIZED GEOMETRY
    # =========================================================================
    def test_06_config_persistence_never_saves_maximized_dimensions(self):
        """Directly verify config.json on disk NEVER contains maximized window dimensions."""
        # Ensure base size is 380x560
        self.win.resize(380, 560)
        self.win.config.set("window_width", 380, auto_save=True)
        self.win.config.set("window_height", 560, auto_save=True)
        self._pump_events(3)

        # Maximize window
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertTrue(self._is_zoomed())
        self.assertGreater(self.win.width(), 1000)

        # Simulate resize events and explicit config save while maximized
        self.win.config.save()

        # Read config.json directly from disk
        self.assertTrue(self.config_path.exists())
        with open(self.config_path, "r", encoding="utf-8") as f:
            disk_config = json.load(f)

        saved_w = disk_config.get("window_width")
        saved_h = disk_config.get("window_height")

        self.assertIsNotNone(saved_w)
        self.assertIsNotNone(saved_h)
        self.assertLess(saved_w, 1000, f"Config disk width was poisoned with maximized size: {saved_w}")
        self.assertLess(saved_h, 800, f"Config disk height was poisoned with maximized size: {saved_h}")
        self.assertEqual(saved_w, 380)
        self.assertEqual(saved_h, 560)

        # In-memory config object check
        self.assertEqual(self.win.config.get("window_width"), 380)
        self.assertEqual(self.win.config.get("window_height"), 560)

    # =========================================================================
    # TEST 7: INTERACTIVE CALCULATION INTEGRITY ACROSS RAPID GEOMETRY CHANGES
    # =========================================================================
    def test_07_interactive_calculation_across_rapid_geometry_changes(self):
        """Verify calculations, display tokens, and history persist accurately across rapid cycles."""
        self.win.state.clear_all()

        # 1. Normal: Calculate 15 * 4
        self.win.state.input_digit("1")
        self.win.state.input_digit("5")
        self.win.state.input_operator("×")
        self.win.state.input_digit("4")
        self.win.state.evaluate()
        self._pump_events(3)
        self.assertEqual(self.win.display.primary_display.text(), "60")

        # 2. Maximize while displaying result
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertTrue(self._is_zoomed())
        self.assertEqual(self.win.display.primary_display.text(), "60")

        # 3. Calculate while maximized: 60 + 40 = 100
        self.win.state.input_operator("+")
        self.win.state.input_digit("4")
        self.win.state.input_digit("0")
        self.win.state.evaluate()
        self._pump_events(3)
        self.assertEqual(self.win.display.primary_display.text(), "100")

        # 4. Open history drawer while maximized
        self.win._toggle_history_drawer()
        self._pump_events(3)
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertTrue(self._is_zoomed())

        # 5. Restore to normal with drawer open
        self.win.title_bar.btn_maximize.click()
        self._pump_events(5)
        self.assertFalse(self._is_zoomed())
        self.assertEqual(self.win.display.primary_display.text(), "100")

        # 6. Close drawer in normal
        self.win._toggle_history_drawer()
        self._pump_events(3)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.display.primary_display.text(), "100")


if __name__ == "__main__":
    unittest.main()
