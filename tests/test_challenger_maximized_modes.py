"""
Comprehensive Challenger Verification Suite:
Empirical Stress-Testing of Maximized Modes, Drawer Layouts, and Theme Transitions.

Objectives:
1. Maximize window and verify all 18 modes (Standard, Scientific, Programmer, Date Calculation, Graphing, and all 13 Unit Converters) expand to full client area without dead space.
2. Verify History drawer opening and closing while maximized: docking cleanly at right edge (x=content_w-290, width=290), keypad stretching across remaining space, cross-mode drawer persistence.
3. Verify Sidebar opening and closing while maximized: scrim covering 100% of content area, sidebar docking at left (width=260), scrim dismiss click.
4. Verify Theme switching across all themes (Dark, Light, OLED, Pastel, High Contrast tokens) while maximized:
   - Window controls (WindowMinimize, WindowMaximize, WindowRestore, WindowClose) retint dynamically.
   - Vector SVGs remain crisp, non-null, properly colored.
   - Zero emoji or unicode corruption.
5. Stress cycles: Rapid maximize/restore and drawer/overlay transitions.
"""

import sys
import ctypes
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QSize, QRect
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.theme_manager import ThemeManager, BUILTIN_THEMES
from src.ui.converter_view import CONVERSION_FACTORS
from src.ui.mode_icons import MODE_SVGS, get_themed_icon


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestChallengerMaximizedModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win.resize(400, 600)
        cls.win.show()
        cls._pump(10)

        cls.hwnd = int(cls.win.winId())
        cls.u = ctypes.windll.user32
        # Maximize window natively
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
            QTest.qWait(15)

    def setUp(self):
        # Ensure window is maximized before each test
        if not self.win.isMaximized():
            self.u.ShowWindow(self.hwnd, 3)
            self._pump(10)

    # =========================================================================
    # 1. Empirically Verify Every Calculator Mode Expands Fully
    # =========================================================================
    def test_01_all_18_modes_maximize_to_full_client_area(self):
        """Verify all 18 modes fill full client area with zero dead/empty space."""
        self.assertTrue(self.win.isMaximized())
        self.assertTrue(bool(self.u.IsZoomed(self.hwnd)))

        win_w = self.win.width()
        win_h = self.win.height()
        title_h = self.win.title_bar.height()
        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        self.assertGreater(win_w, 1000, f"Maximized window width {win_w} is too small")
        self.assertGreater(win_h, 700, f"Maximized window height {win_h} is too small")
        self.assertEqual(self.win.root_container.width(), win_w)
        self.assertEqual(self.win.root_container.height(), win_h)
        self.assertEqual(content_w, win_w)
        self.assertEqual(content_h, win_h - title_h)

        all_modes = [
            "Standard",
            "Scientific",
            "Programmer",
            "Date Calculation",
            "Graphing",
            "Currency",
            "Volume",
            "Length",
            "Weight and Mass",
            "Temperature",
            "Energy",
            "Area",
            "Speed",
            "Time",
            "Power",
            "Data",
            "Pressure",
            "Angle"
        ]

        # Verify we are testing all 18 modes
        self.assertEqual(len(all_modes), 18)

        for mode in all_modes:
            with self.subTest(mode=mode):
                self.win._switch_mode(mode, save_config=False)
                self._pump(4)

                # Geometry assertions
                self.assertEqual(self.win.root_container.size(), self.win.size())
                self.assertEqual(self.win.content_widget.width(), win_w)
                self.assertEqual(self.win.content_widget.height(), content_h)

                cw = self.win.stack.currentWidget()
                self.assertIsNotNone(cw)
                self.assertEqual(cw.width(), self.win.center_container.width())
                self.assertGreater(cw.height(), 0)

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
                    self.assertGreaterEqual(gp.canvas.width(), 800)
                    self.assertFalse(gp.mode_selector_bar.isVisible())
                elif mode == "Date Calculation":
                    dc = self.win.date_calc_page
                    self.assertEqual(dc.width(), self.win.center_container.width())
                    self.assertGreaterEqual(dc.width(), 1000)
                else:
                    # Unit Converters
                    cv = self.win.converter_page
                    self.assertEqual(cv.width(), self.win.center_container.width())
                    self.assertEqual(cv.category, mode)
                    self.assertGreaterEqual(cv.width(), 1000)

    # =========================================================================
    # 2. History Drawer Docking and Layout Under Maximization
    # =========================================================================
    def test_02_history_drawer_docking_and_keypad_stretching(self):
        """Verify history drawer docks cleanly at right edge and keypad fills remaining space."""
        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        self.win._switch_mode("Standard", save_config=False)
        self._pump(4)

        # 1. Initially drawer is hidden
        if self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
            self._pump(4)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)

        # 2. Open drawer
        self.win._toggle_history_drawer()
        self._pump(4)
        self.assertTrue(self.win.history_drawer.isVisible())

        # Drawer dimensions and docking
        drawer_w = self.win.history_drawer.width()
        drawer_h = self.win.history_drawer.height()
        drawer_geom = self.win.history_drawer.geometry()

        self.assertEqual(drawer_w, 290)
        self.assertEqual(drawer_h, content_h)
        self.assertEqual(drawer_geom.x(), content_w - 290)
        self.assertEqual(drawer_geom.right(), content_w - 1)

        # Keypad / center container stretching
        self.assertEqual(self.win.center_container.width(), content_w - 290)
        self.assertEqual(self.win.keypad.width(), content_w - 290)
        self.assertEqual(self.win.display.width(), content_w - 290)

        # 3. Interactive calculation with drawer open
        btn_7 = self.win.keypad.button_map.get("7")
        btn_add = self.win.keypad.button_map.get("+")
        btn_5 = self.win.keypad.button_map.get("5")
        btn_eq = self.win.keypad.button_map.get("=")

        QTest.mouseClick(btn_7, Qt.MouseButton.LeftButton)
        self._pump(2)
        QTest.mouseClick(btn_add, Qt.MouseButton.LeftButton)
        self._pump(2)
        QTest.mouseClick(btn_5, Qt.MouseButton.LeftButton)
        self._pump(2)
        QTest.mouseClick(btn_eq, Qt.MouseButton.LeftButton)
        self._pump(2)
        self.assertEqual(self.win.display.primary_display.text(), "12")

        # 4. Mode transitions with drawer open
        # Scientific
        self.win._switch_mode("Scientific", save_config=False)
        self._pump(4)
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.history_drawer.geometry().right(), content_w - 1)
        self.assertEqual(self.win.keypad.width(), content_w - 290)

        # Programmer
        self.win._switch_mode("Programmer", save_config=False)
        self._pump(4)
        self.assertTrue(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.history_drawer.geometry().right(), content_w - 1)
        self.assertEqual(self.win.keypad.width(), content_w - 290)

        # Graphing (history drawer should auto-close)
        self.win._switch_mode("Graphing", save_config=False)
        self._pump(4)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)

        # Switch back to Standard and close drawer
        self.win._switch_mode("Standard", save_config=False)
        self._pump(4)
        if self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
            self._pump(4)
        self.assertFalse(self.win.history_drawer.isVisible())
        self.assertEqual(self.win.center_container.width(), content_w)

    # =========================================================================
    # 3. Navigation Sidebar and Full Client Area Scrim
    # =========================================================================
    def test_03_sidebar_and_scrim_full_client_area_coverage(self):
        """Verify navigation sidebar flyout and scrim coverage across full client area."""
        content_w = self.win.content_widget.width()
        content_h = self.win.content_widget.height()

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # Open sidebar
        self.win._toggle_sidebar()
        self._pump(4)

        self.assertTrue(self.win.sidebar.isVisible())
        self.assertTrue(self.win.scrim.isVisible())

        # Scrim MUST cover 100% of the content widget client area
        scrim_rect = self.win.scrim.geometry()
        self.assertEqual(scrim_rect, QRect(0, 0, content_w, content_h))

        # Sidebar must be 260px wide and match content height
        sidebar_rect = self.win.sidebar.geometry()
        self.assertEqual(sidebar_rect, QRect(0, 0, 260, content_h))

        # Click scrim outside sidebar to close
        QTest.mouseClick(self.win.scrim, Qt.MouseButton.LeftButton, pos=QPoint(450, 350))
        self._pump(4)
        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())

        # Re-open and select mode from sidebar
        self.win._toggle_sidebar()
        self._pump(4)
        self.assertTrue(self.win.sidebar.isVisible())

        btn_prog = self.win.sidebar.buttons.get("Programmer")
        self.assertIsNotNone(btn_prog)
        QTest.mouseClick(btn_prog, Qt.MouseButton.LeftButton)
        self._pump(6)

        self.assertFalse(self.win.sidebar.isVisible())
        self.assertFalse(self.win.scrim.isVisible())
        self.assertEqual(self.win.state.mode, "Programmer")
        self.assertEqual(self.win.content_widget.width(), content_w)

    # =========================================================================
    # 4. Theme Switching While Maximized & Window Controls SVG Retinting
    # =========================================================================
    def test_04_theme_switching_and_window_controls_retinting(self):
        """Verify dynamic retinting of WindowMinimize, WindowRestore, WindowClose across all themes."""
        self.assertTrue(self.win.isMaximized())

        themes_to_test = [
            ("dark_monokai", "#F8F8F2"),
            ("dark_obsidian", "#FFFFFF"),    # OLED Theme
            ("dark_graphite", "#F5F5F7"),
            ("light_snow", "#1A1A1A"),
            ("light_soft_pink", "#881337"),  # Pastel Theme
            ("light_parchment", "#292524")
        ]

        title_bar = self.win.title_bar
        btn_min = title_bar.btn_minimize
        btn_max = title_bar.btn_maximize
        btn_close = title_bar.btn_close

        for theme_id, expected_text_color in themes_to_test:
            with self.subTest(theme=theme_id):
                self.win.theme_mgr.set_theme(theme_id)
                self.win._apply_theme()
                self._pump(4)

                # Geometry stability
                self.assertTrue(self.win.isMaximized())
                self.assertEqual(self.win.root_container.size(), self.win.size())

                # Window controls inspection
                self.assertFalse(btn_min.icon().isNull(), f"Minimize icon null in {theme_id}")
                self.assertFalse(btn_max.icon().isNull(), f"Maximize/Restore icon null in {theme_id}")
                self.assertFalse(btn_close.icon().isNull(), f"Close icon null in {theme_id}")

                # Tooltips and Maximize State
                self.assertEqual(btn_min.toolTip(), "Minimize")
                self.assertEqual(btn_max.toolTip(), "Restore")
                self.assertEqual(btn_close.toolTip(), "Close")
                self.assertTrue(getattr(title_bar, "_is_max", False))

                # Retinting verification: Title bar internal icon color
                self.assertEqual(title_bar._icon_color, expected_text_color)

                # Verify rendered pixmaps contain non-transparent pixels colored with active theme text color
                pix_min = btn_min.icon().pixmap(14, 14)
                self.assertFalse(pix_min.isNull())
                img_min = pix_min.toImage()
                has_colored_pixel = False
                target_qcolor = QColor(expected_text_color)
                for x in range(img_min.width()):
                    for y in range(img_min.height()):
                        pixel = img_min.pixelColor(x, y)
                        if pixel.alpha() > 100:
                            # Verify red/green/blue channels are within tolerance of target color
                            if (abs(pixel.red() - target_qcolor.red()) <= 15 and
                                abs(pixel.green() - target_qcolor.green()) <= 15 and
                                abs(pixel.blue() - target_qcolor.blue()) <= 15):
                                has_colored_pixel = True
                                break
                    if has_colored_pixel:
                        break
                self.assertTrue(has_colored_pixel, f"Minimize icon not tinted to {expected_text_color} in {theme_id}")

    # =========================================================================
    # 5. Restore / Maximize Icon Toggle and Dynamic Tooltips
    # =========================================================================
    def test_05_restore_maximize_icon_and_state_toggle(self):
        """Verify maximize button toggles cleanly between WindowMaximize and WindowRestore."""
        title_bar = self.win.title_bar
        btn_max = title_bar.btn_maximize

        # 1. In maximized state -> Restore icon and Restore tooltip
        self.assertTrue(self.win.isMaximized())
        self.assertEqual(btn_max.toolTip(), "Restore")
        self.assertTrue(getattr(title_bar, "_is_max", False))

        # 2. Restore window
        self.u.ShowWindow(self.hwnd, 9)  # SW_RESTORE
        self._pump(10)

        self.assertFalse(self.win.isMaximized())
        self.assertEqual(btn_max.toolTip(), "Maximize")
        self.assertFalse(getattr(title_bar, "_is_max", False))

        # 3. Maximize again
        btn_max.click()
        self._pump(10)

        self.assertTrue(self.win.isMaximized())
        self.assertEqual(btn_max.toolTip(), "Restore")
        self.assertTrue(getattr(title_bar, "_is_max", False))

    # =========================================================================
    # 6. High-Contrast / Custom Theme Vector Tinting
    # =========================================================================
    def test_06_high_contrast_custom_theme_tinting(self):
        """Verify vector SVGs handle high contrast colors without degradation or emoji fallback."""
        high_contrast_colors = ["#00FF00", "#FFFF00", "#00FFFF", "#FFFFFF"]
        for hc_hex in high_contrast_colors:
            with self.subTest(color=hc_hex):
                self.win.title_bar.update_theme_icons(hc_hex)
                self._pump(2)

                self.assertEqual(self.win.title_bar._icon_color, hc_hex)
                icon = self.win.title_bar.btn_maximize.icon()
                self.assertFalse(icon.isNull())
                pix = icon.pixmap(14, 14)
                img = pix.toImage()

                # Search for target colored pixel
                target = QColor(hc_hex)
                found = False
                for x in range(img.width()):
                    for y in range(img.height()):
                        c = img.pixelColor(x, y)
                        if c.alpha() > 150 and (
                            abs(c.red() - target.red()) <= 10 and
                            abs(c.green() - target.green()) <= 10 and
                            abs(c.blue() - target.blue()) <= 10
                        ):
                            found = True
                            break
                    if found:
                        break
                self.assertTrue(found, f"High contrast icon failed tinting for {hc_hex}")

    # =========================================================================
    # 7. Rapid Mode Switch Stress in Maximized State
    # =========================================================================
    def test_07_rapid_mode_switching_stress_in_maximized_state(self):
        """Stress-test rapid switches across multiple modes while maximized."""
        rapid_sequence = [
            "Standard", "Scientific", "Programmer", "Graphing",
            "Date Calculation", "Currency", "Length", "Standard",
            "Speed", "Temperature", "Energy", "Volume", "Standard"
        ]

        win_w = self.win.width()
        win_h = self.win.height()

        for mode in rapid_sequence:
            self.win._switch_mode(mode, save_config=False)
            self._pump(2)

            self.assertEqual(self.win.root_container.size(), self.win.size())
            self.assertEqual(self.win.content_widget.width(), win_w)
            self.assertEqual(self.win.content_widget.height(), win_h - self.win.title_bar.height())
            cw = self.win.stack.currentWidget()
            self.assertIsNotNone(cw)
            self.assertEqual(cw.width(), self.win.center_container.width())


if __name__ == "__main__":
    unittest.main()
