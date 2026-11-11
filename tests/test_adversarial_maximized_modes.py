"""
Adversarial Stress Test Suite for Maximized Window Multi-Mode UI Layout & Geometry.
Validates:
1. Multi-mode geometry expansion (Standard, Scientific, Programmer, Graphing, Converters, Date Calc)
2. Overlay geometry and scrims (Navigation Sidebar, History Drawer, Memory Bar)
3. Zero dead click zones on all edges and corners
4. Dynamic theme switching across light and dark themes in maximized state
5. Restore / Re-maximize cycles
"""

import sys
import ctypes
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.native_window import (
    HTMAXBUTTON, HTCLIENT, HTCAPTION,
    HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT
)
from src.ui.converter_view import CONVERSION_FACTORS


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMaximizedMultiModeAdversarial(unittest.TestCase):
    def setUp(self):
        self.win = MainWindow(check_updates=False)
        self.win._switch_mode("Standard", save_config=False)
        self.win.resize(360, 580)
        self.win.show()
        app.processEvents()

        # Maximize natively
        self.hwnd = int(self.win.winId())
        self.u = ctypes.windll.user32
        self.u.ShowWindow(self.hwnd, 3)  # SW_SHOWMAXIMIZED
        self._pump_events(10)

    def tearDown(self):
        self.win.close()
        self._pump_events(5)

    def _pump_events(self, iterations: int = 5):
        for _ in range(iterations):
            app.processEvents()
            QTest.qWait(15)

    def test_01_maximized_geometry_across_all_modes(self):
        """Verify that every single mode expands to full client area without clipping."""
        self.assertTrue(self.win.isMaximized())
        self.assertTrue(bool(self.u.IsZoomed(self.hwnd)))

        win_w = self.win.width()
        win_h = self.win.height()
        self.assertGreater(win_w, 1000, f"Window width not expanded: {win_w}")
        self.assertGreater(win_h, 700, f"Window height not expanded: {win_h}")

        modes_to_test = [
            "Standard",
            "Scientific",
            "Programmer",
            "Graphing",
            "Date Calculation",
        ] + list(CONVERSION_FACTORS.keys())

        for mode in modes_to_test:
            with self.subTest(mode=mode):
                self.win._switch_mode(mode, save_config=False)
                self._pump_events(5)

                # 1. Root container and content widget fill window
                self.assertEqual(self.win.root_container.size(), self.win.size())
                self.assertEqual(self.win.content_widget.width(), win_w)
                self.assertEqual(self.win.content_widget.height(), win_h - self.win.title_bar.height())

                # 2. Current stack widget fills available area
                cw = self.win.stack.currentWidget()
                self.assertIsNotNone(cw)
                self.assertEqual(cw.width(), self.win.center_container.width())
                self.assertGreater(cw.height(), 0)

                # 3. Check mode-specific component expansion
                if mode in ("Standard", "Scientific", "Programmer"):
                    self.assertEqual(self.win.display.width(), self.win.center_container.width())
                    self.assertEqual(self.win.keypad.width(), self.win.center_container.width())
                    self.assertGreater(self.win.keypad.height(), 400)
                    self.assertEqual(self.win.keypad.geometry().right(), self.win.center_container.width() - 1)
                elif mode == "Graphing":
                    gp = self.win.graphing_page
                    self.assertEqual(gp.width(), self.win.center_container.width())
                    self.assertTrue(gp.left_pane.isVisible())
                    self.assertTrue(gp.right_pane.isVisible())
                    self.assertGreaterEqual(gp.canvas.width(), 800, "Graph canvas should expand in wide view")
                    self.assertFalse(gp.mode_selector_bar.isVisible(), "Mobile bar should be hidden in maximized view")
                elif mode == "Date Calculation":
                    dc = self.win.date_calc_page
                    self.assertEqual(dc.width(), self.win.center_container.width())
                else:
                    # Converter modes
                    cv = self.win.converter_page
                    self.assertEqual(cv.width(), self.win.center_container.width())
                    self.assertEqual(cv.category, mode)

    def test_02_maximized_overlays_and_scrim_geometry(self):
        """Verify navigation sidebar scrim, sidebar flyout, and history drawer geometries when maximized."""
        win_w = self.win.width()
        win_h = self.win.height()
        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        # ─── Navigation Sidebar Overlay ───
        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # Open sidebar
        self.win._toggle_sidebar()
        self._pump_events(5)

        self.assertTrue(self.win.sidebar.isVisible())
        self.assertTrue(self.win.scrim.isVisible())

        # Scrim MUST cover the entire content area
        scrim_geom = self.win.scrim.geometry()
        self.assertEqual(scrim_geom.x(), 0)
        self.assertEqual(scrim_geom.y(), 0)
        self.assertEqual(scrim_geom.width(), content_w)
        self.assertEqual(scrim_geom.height(), content_h)

        # Sidebar must be 260px wide and match content height
        sidebar_geom = self.win.sidebar.geometry()
        self.assertEqual(sidebar_geom.x(), 0)
        self.assertEqual(sidebar_geom.y(), 0)
        self.assertEqual(sidebar_geom.width(), 260)
        self.assertEqual(sidebar_geom.height(), content_h)

        # Clicking scrim outside sidebar closes sidebar
        QTest.mouseClick(self.win.scrim, Qt.MouseButton.LeftButton, pos=QPoint(400, 300))
        self._pump_events(5)
        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # ─── History Drawer Panel ───
        self.win._switch_mode("Standard", save_config=False)
        self._pump_events(5)

        # Open history drawer
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
            self._pump_events(5)

        self.assertTrue(self.win.history_drawer.isVisible())
        hw = self.win.history_drawer.width()
        self.assertEqual(hw, 290)

        # History drawer should dock cleanly to the right edge
        self.assertEqual(
            self.win.center_container.width() + self.win.history_drawer.width(),
            content_w
        )
        self.assertEqual(
            self.win.history_drawer.geometry().right(),
            content_w - 1
        )

        # Close history drawer
        self.win._toggle_history_drawer()
        self._pump_events(5)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)

    def test_03_zero_dead_click_zones_on_edges_and_corners(self):
        """Verify no dead click zones, correct NCHITTEST codes, and edge hit-testing in maximized state."""
        w = self.win.width()
        h = self.win.height()

        # Critical test: In maximized state, resize border codes must NEVER be returned
        forbidden_resize_codes = {
            HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
            HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT
        }

        # Test corners
        corner_points = [
            ("top-left", 0, 0),
            ("top-right", w - 1, 0),
            ("bottom-left", 0, h - 1),
            ("bottom-right", w - 1, h - 1),
        ]
        for name, lx, ly in corner_points:
            gp = self.win.mapToGlobal(QPoint(lx, ly))
            hit = self.win._handle_nchittest(gp.x(), gp.y())
            self.assertNotIn(hit, forbidden_resize_codes, f"Corner {name} returned resize hit code {hit} while maximized")

        # Test edges
        edge_points = [
            ("top-edge", w // 2, 0),
            ("bottom-edge", w // 2, h - 1),
            ("left-edge", 0, h // 2),
            ("right-edge", w - 1, h // 2),
        ]
        for name, lx, ly in edge_points:
            gp = self.win.mapToGlobal(QPoint(lx, ly))
            hit = self.win._handle_nchittest(gp.x(), gp.y())
            self.assertNotIn(hit, forbidden_resize_codes, f"Edge {name} returned resize hit code {hit} while maximized")

        # Fitts's law: Top-right corner (w-1, 0) must target the close button
        gp_close = self.win.mapToGlobal(QPoint(w - 1, 0))
        btn_close_pt = self.win.btn_close.mapFromGlobal(gp_close)
        self.assertTrue(
            self.win.btn_close.rect().contains(btn_close_pt),
            "Top-right pixel (w-1, 0) failed to hit the close button!"
        )

        # Maximize button returns HTMAXBUTTON for native Win11 Snap Layouts flyout
        gp_max = self.win.btn_maximize.mapToGlobal(self.win.btn_maximize.rect().center())
        hit_max = self.win._handle_nchittest(gp_max.x(), gp_max.y())
        self.assertEqual(hit_max, HTMAXBUTTON)

        # Bottom-right corner hits child widget inside client area with no dead zone
        child_br = self.win.childAt(w - 1, h - 1)
        self.assertIsNotNone(child_br, "Bottom-right corner returned None (dead click zone)!")

        # Bottom-left corner hits child widget inside client area with no dead zone
        child_bl = self.win.childAt(0, h - 1)
        self.assertIsNotNone(child_bl, "Bottom-left corner returned None (dead click zone)!")

    def test_04_interactive_clicks_in_all_modes_when_maximized(self):
        """Verify calculations and button clicks register properly in every mode while maximized."""
        # 1. Standard mode
        self.win._switch_mode("Standard", save_config=False)
        self._pump_events(5)

        btn_8 = self.win.keypad.button_map.get("8")
        btn_mul = self.win.keypad.button_map.get("×") or self.win.keypad.button_map.get("*")
        btn_9 = self.win.keypad.button_map.get("9")
        btn_eq = self.win.keypad.button_map.get("=")

        # Far-right equals button is positioned at the far right of the monitor
        self.assertGreater(btn_eq.mapToGlobal(QPoint(0, 0)).x(), 1200)

        QTest.mouseClick(btn_8, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        QTest.mouseClick(btn_mul, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        QTest.mouseClick(btn_9, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        QTest.mouseClick(btn_eq, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        self.assertEqual(self.win.display.primary_display.text(), "72")

        # 2. Scientific mode
        self.win._switch_mode("Scientific", save_config=False)
        self._pump_events(5)

        btn_pi = self.win.keypad.button_map.get("π")
        btn_sci_eq = self.win.keypad.button_map.get("=")
        QTest.mouseClick(btn_pi, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        QTest.mouseClick(btn_sci_eq, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        self.assertIn("3.14159", self.win.display.primary_display.text())

        # 3. Programmer mode
        self.win._switch_mode("Programmer", save_config=False)
        self._pump_events(5)

        btn_a = self.win.keypad.button_map.get("A")
        btn_prog_eq = self.win.keypad.button_map.get("=")
        QTest.mouseClick(btn_a, Qt.MouseButton.LeftButton)
        self._pump_events(2)
        self.assertIn("A", self.win.display.primary_display.text())

        # 4. Graphing mode
        self.win._switch_mode("Graphing", save_config=False)
        self._pump_events(5)

        gp = self.win.graphing_page
        self.assertGreater(len(gp.function_rows), 0)
        # Click add function
        initial_count = len(gp.function_rows)
        QTest.mouseClick(gp.btn_add_fn, Qt.MouseButton.LeftButton)
        self._pump_events(5)
        self.assertEqual(len(gp.function_rows), initial_count + 1)

        # 5. Converter mode
        self.win._switch_mode("Length", save_config=False)
        self._pump_events(5)
        cv = self.win.converter_page
        cv.input1.setText("100")
        cv._on_input1_changed("100")
        self._pump_events(2)
        self.assertTrue(len(cv.input2.text()) > 0)
        self.assertNotEqual(cv.input2.text(), "0")

    def test_05_theme_switching_while_maximized(self):
        """Verify seamless theme transitions without geometry clipping or icon distortion."""
        themes = [
            "dark_monokai",
            "light_snow",
            "dark_obsidian",
            "light_soft_pink",
            "dark_graphite",
            "light_parchment"
        ]

        orig_w = self.win.width()
        orig_h = self.win.height()

        for theme_id in themes:
            with self.subTest(theme=theme_id):
                self.win.theme_mgr.set_theme(theme_id)
                self.win._apply_theme()
                self._pump_events(5)

                # Geometry must remain fully maximized
                self.assertTrue(self.win.isMaximized())
                self.assertEqual(self.win.width(), orig_w)
                self.assertEqual(self.win.height(), orig_h)
                self.assertEqual(self.win.root_container.size(), self.win.size())

                # Icons must be non-null and valid
                self.assertFalse(self.win.hamburger_btn.icon().isNull())
                backspace_btn = self.win.keypad.button_map.get("⌫")
                if backspace_btn:
                    self.assertFalse(backspace_btn.icon().isNull())

    def test_06_restore_and_remaximize_cycles(self):
        """Verify cycling between maximized and restored states preserves geometry and layouts."""
        orig_max_w = self.win.width()
        orig_max_h = self.win.height()

        # 1. Restore window
        self.u.ShowWindow(self.hwnd, 9)  # SW_RESTORE
        self._pump_events(10)
        self.assertFalse(self.win.isMaximized())
        self.assertLess(self.win.width(), 800)
        self.assertEqual(self.win.root_container.size(), self.win.size())

        # 2. Re-maximize via title bar maximize button
        self.win.title_bar.btn_maximize.click()
        self._pump_events(10)
        self.assertTrue(self.win.isMaximized())
        self.assertEqual(self.win.width(), orig_max_w)
        self.assertEqual(self.win.height(), orig_max_h)
        self.assertEqual(self.win.root_container.size(), self.win.size())
        self.assertEqual(self.win.content_widget.width(), orig_max_w)

    def test_07_mode_switching_with_history_drawer_open(self):
        """Verify mode switching while history panel is open maintains correct split geometry."""
        content_w = self.win.content_widget.width()

        # Open history drawer
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
            self._pump_events(5)

        self.assertTrue(self.win.history_drawer.isVisible())
        hw = self.win.history_drawer.width()
        self.assertEqual(self.win.center_container.width(), content_w - hw)

        # Switch to Scientific
        self.win._switch_mode("Scientific", save_config=False)
        self._pump_events(5)
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w - hw)
        self.assertEqual(self.win.keypad.width(), content_w - hw)

        # Switch to Programmer
        self.win._switch_mode("Programmer", save_config=False)
        self._pump_events(5)
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w - hw)
        self.assertEqual(self.win.keypad.width(), content_w - hw)

        # Switch to Graphing (should auto-close history drawer)
        self.win._switch_mode("Graphing", save_config=False)
        self._pump_events(5)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)

    def test_08_sidebar_selection_and_closing_while_maximized(self):
        """Verify navigation sidebar mode selection updates mode and hides overlays."""
        self.win._switch_mode("Standard", save_config=False)
        self._pump_events(5)

        self.win._toggle_sidebar()
        self._pump_events(5)
        self.assertTrue(self.win.sidebar.isVisible())
        self.assertTrue(self.win.scrim.isVisible())

        btn_sci = self.win.sidebar.buttons.get("Scientific")
        self.assertIsNotNone(btn_sci)
        QTest.mouseClick(btn_sci, Qt.MouseButton.LeftButton)
        self._pump_events(10)

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())
        self.assertEqual(self.win.state.mode, "Scientific")
        self.assertTrue(self.win.hamburger_btn.isVisible())
        self.assertEqual(self.win.width(), self.win.root_container.width())

    def test_09_side_and_corner_snap_layouts(self):
        """Verify window behavior when snapped to screen sides and corners (Aero Snap)."""
        # Un-maximize / restore first as Windows does before snapping to sides/corners
        self.u.ShowWindow(self.hwnd, 9)  # SW_RESTORE
        self._pump_events(10)
        self.assertFalse(self.win.isMaximized())

        # Side Snap: 960 x 1032
        self.u.SetWindowPos(self.hwnd, 0, 0, 0, 960, 1032, 0x0004 | 0x0040)
        self._pump_events(10)
        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.width(), 960)
        self.assertEqual(self.win.root_container.width(), 960)
        self.assertEqual(self.win.content_widget.width(), 960)

        # Corner Snap: 960 x 540
        self.u.SetWindowPos(self.hwnd, 0, 0, 0, 960, 540, 0x0004 | 0x0040)
        self._pump_events(10)
        self.assertFalse(self.win.isMaximized())
        self.assertEqual(self.win.width(), 960)
        self.assertEqual(self.win.height(), 540)
        self.assertEqual(self.win.root_container.size(), self.win.size())




if __name__ == "__main__":
    unittest.main()
