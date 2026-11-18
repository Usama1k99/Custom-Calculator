"""
Unit Tests for Converter Enhancements, Currency Engine, and Blur/Transparency Controls.
Zero emojis.
"""

import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.core.config import ConfigManager
from src.core.currency_engine import CurrencyEngine, format_currency_label, code_from_label
from src.ui.converter_view import ConverterView, CONVERSION_FACTORS
from src.ui.theme_manager import ThemeManager
from src.ui.theme_dialog import ThemeDialog

app = QApplication.instance() or QApplication([])


class TestConverterAndEffects(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()
        self.config.set("history_open", False)

    def test_volume_converter_cubic_units(self):
        self.assertIn("Volume", CONVERSION_FACTORS)
        vol_factors = CONVERSION_FACTORS["Volume"]
        
        # Must explicitly mention cubic units
        cubic_units = [u for u in vol_factors.keys() if "Cubic" in u]
        self.assertGreaterEqual(len(cubic_units), 6)
        self.assertIn("Cubic Meters (m³)", vol_factors)
        self.assertIn("Cubic Centimeters (cm³)", vol_factors)
        self.assertIn("Cubic Millimeters (mm³)", vol_factors)
        self.assertIn("Cubic Inches (in³)", vol_factors)
        self.assertIn("Cubic Feet (ft³)", vol_factors)
        self.assertIn("Cubic Yards (yd³)", vol_factors)

        # 1 Cubic Meter = 1,000 Liters
        self.assertEqual(vol_factors["Cubic Meters (m³)"], 1000.0)
        self.assertEqual(vol_factors["Liters (L)"], 1.0)
        # 1,000,000 cm³ = 1 m³
        self.assertAlmostEqual(vol_factors["Cubic Centimeters (cm³)"] * 1000000, vol_factors["Cubic Meters (m³)"])

    def test_data_converter_above_tb(self):
        self.assertIn("Data", CONVERSION_FACTORS)
        data_factors = CONVERSION_FACTORS["Data"]

        # Must go well above TB
        self.assertIn("Petabytes (PB)", data_factors)
        self.assertIn("Exabytes (EB)", data_factors)
        self.assertIn("Zettabytes (ZB)", data_factors)
        self.assertIn("Yottabytes (YB)", data_factors)

        # Verify power-of-2 scaling
        tb = data_factors["Terabytes (TB)"]
        pb = data_factors["Petabytes (PB)"]
        eb = data_factors["Exabytes (EB)"]
        zb = data_factors["Zettabytes (ZB)"]
        yb = data_factors["Yottabytes (YB)"]

        self.assertEqual(pb, tb * 1024)
        self.assertEqual(eb, pb * 1024)
        self.assertEqual(zb, eb * 1024)
        self.assertEqual(yb, zb * 1024)

    def test_currency_engine_conversion_and_labels(self):
        ce = CurrencyEngine()
        currencies = ce.get_currency_list()
        self.assertGreaterEqual(len(currencies), 30)

        # Label formatting
        usd_label = format_currency_label("USD")
        self.assertIn("USD", usd_label)
        self.assertIn("US Dollar", usd_label)
        self.assertEqual(code_from_label(usd_label), "USD")

        # Conversions
        res_usd_to_usd = ce.convert(100.0, "USD", "USD")
        self.assertEqual(res_usd_to_usd, 100.0)

        eur_rate = ce.get_rate("EUR")
        res_usd_to_eur = ce.convert(100.0, "USD", "EUR")
        self.assertAlmostEqual(res_usd_to_eur, 100.0 * eur_rate, places=2)

    def test_converter_view_currency_mode_and_vertical_spacing(self):
        view = ConverterView("Length")
        # Check tightened margins and spacing
        layout = view.layout()
        m = layout.contentsMargins()
        self.assertLessEqual(m.top(), 8)
        self.assertLessEqual(m.bottom(), 8)
        self.assertLessEqual(layout.spacing(), 8)

        # Switch to Currency
        view.set_category("Currency")
        self.assertFalse(view.currency_status_row.isHidden())
        self.assertGreaterEqual(view.combo1.count(), 30)
        self.assertIn("USD", view.combo1.currentText())

        # Test calculation
        view.input1.setText("50")
        view._calculate()
        self.assertNotEqual(view.input2.text(), "0")
        self.assertNotEqual(view.input2.text(), "Invalid input")

        # Switch to Volume
        view.set_category("Volume")
        self.assertTrue(view.currency_status_row.isHidden())
        self.assertIn("Cubic", view.combo1.itemText(0))

    def test_theme_dialog_blur_and_transparency_controls(self):
        tm = ThemeManager()
        dlg = ThemeDialog(tm, initial_tab=0)

        # Verify transparency toggle and two-pane layout exist
        self.assertTrue(hasattr(dlg, "trans_toggle") or hasattr(dlg, "blur_toggle"))
        self.assertTrue(hasattr(dlg, "slider_trans"))
        self.assertTrue(hasattr(dlg, "left_scroll"))
        self.assertTrue(hasattr(dlg, "right_scroll"))
        self.assertTrue(hasattr(dlg, "pane_divider"))

        # Verify 0 to 25 capped slider range
        self.assertEqual(dlg.slider_trans.minimum(), 0)
        self.assertEqual(dlg.slider_trans.maximum(), 25)

        # Test toggling transparency OFF
        toggle = getattr(dlg, "trans_toggle", getattr(dlg, "blur_toggle", None))
        if hasattr(toggle, "set_transparency"):
            toggle.set_transparency(False, animate=False)
        else:
            toggle.set_blur(False, animate=False)
        self.assertFalse(dlg.slider_trans.isEnabled())
        self.assertFalse(dlg.lbl_trans_title.isEnabled())
        self.assertFalse(ConfigManager().get("transparency_enabled"))
        desc_lbl = getattr(dlg, "trans_desc_lbl", getattr(dlg, "blur_desc_lbl", None))
        self.assertEqual(desc_lbl.text(), "Off")

        # Test toggling transparency ON
        if hasattr(toggle, "set_transparency"):
            toggle.set_transparency(True, animate=False)
        else:
            toggle.set_blur(True, animate=False)
        self.assertTrue(dlg.slider_trans.isEnabled())
        self.assertTrue(dlg.lbl_trans_title.isEnabled())
        self.assertTrue(ConfigManager().get("transparency_enabled"))
        self.assertEqual(desc_lbl.text(), "On")

        # Test changing transparency within 0-25%
        dlg.slider_trans.setValue(20)
        self.assertEqual(ConfigManager().get("window_transparency"), 20)
        self.assertIn("20%", dlg.lbl_trans_title.text())

        # Test capping at 25%
        dlg.slider_trans.setValue(45)
        self.assertEqual(dlg.slider_trans.value(), 25)
        self.assertEqual(ConfigManager().get("window_transparency"), 25)
        self.assertIn("25%", dlg.lbl_trans_title.text())

        # Test animated toggling does not raise NameError or unhandled exception
        toggle.set_transparency(False, animate=True)
        QApplication.instance().processEvents()
        toggle.set_transparency(True, animate=True)
        QApplication.instance().processEvents()
        if hasattr(dlg, "mode_toggle"):
            dlg.mode_toggle.set_dark_mode(False, animate=True)
            QApplication.instance().processEvents()
            dlg.mode_toggle.set_dark_mode(True, animate=True)
            QApplication.instance().processEvents()

        # Test Done button commits
        dlg._on_done_clicked()
        self.assertEqual(ConfigManager().get("window_transparency"), 25)
        self.assertTrue(ConfigManager().get("transparency_enabled"))

        # Reset to default 15%
        dlg.slider_trans.setValue(15)
        dlg._on_done_clicked()

    def test_titlebar_icon_size_22x22(self):
        from src.ui.main_window import MainWindow
        win = MainWindow(check_updates=False)
        self.assertEqual(win.title_bar.icon_lbl.width(), 22)
        self.assertEqual(win.title_bar.icon_lbl.height(), 22)
        win.close()

    def test_sidebar_menu_solid_opaque_styling(self):
        tm = ThemeManager()
        qss = tm.generate_qss(blur_enabled=True, window_transparency=70)
        tokens = tm.current_tokens
        # NavSidebar must use opaque bg_surface, never rgba with transparency
        self.assertIn(f"QFrame#NavSidebar {{\n            background-color: {tokens['bg_surface']};", qss)
        self.assertIn(f"QScrollArea#NavScrollArea,\n        QWidget#NavScrollContainer", qss)

    def test_maximize_expands_layout_and_toggles_icon(self):
        from src.ui.main_window import MainWindow
        win = MainWindow(check_updates=False)
        win.show()
        QApplication.instance().processEvents()

        # Normal size
        self.assertEqual(win.title_bar.btn_maximize.toolTip(), "Maximize")
        self.assertFalse(win.title_bar.btn_maximize.icon().isNull())

        # Maximize
        win._toggle_maximize()
        QApplication.instance().processEvents()
        self.assertTrue(win.isMaximized())
        self.assertEqual(win.title_bar.btn_maximize.toolTip(), "Restore")
        self.assertFalse(win.title_bar.btn_maximize.icon().isNull())
        self.assertEqual(win.root_container.width(), win.width())
        self.assertEqual(win.root_container.height(), win.height())

        # Restore
        win._toggle_maximize()
        QApplication.instance().processEvents()
        self.assertFalse(win.isMaximized())
        self.assertEqual(win.title_bar.btn_maximize.toolTip(), "Maximize")
        self.assertFalse(win.title_bar.btn_maximize.icon().isNull())
        self.assertEqual(win.root_container.width(), win.width())
        win.close()

    def test_history_drawer_toggle_keeps_x_position_static(self):
        from src.ui.main_window import MainWindow
        win = MainWindow(check_updates=False)
        if win.history_drawer.isVisible():
            win._toggle_history_drawer()
        win.show()
        # Set a narrow initial width below threshold
        initial_x = 200
        initial_y = 150
        win.move(initial_x, initial_y)
        win.resize(340, 560)
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().processEvents()

        # Open history drawer
        win._toggle_history_drawer()
        QApplication.instance().processEvents()

        # Window position x must NOT shift to the left
        self.assertEqual(win.x(), initial_x, "Window x-coordinate shifted when opening history drawer")
        self.assertTrue(win.history_drawer.isVisible())
        self.assertGreater(win.width(), 340, "Window width should have extended to the right")

        # Close history drawer
        win._toggle_history_drawer()
        QApplication.instance().processEvents()

        # Window position x must still remain at the exact same position
        self.assertEqual(win.x(), initial_x, "Window x-coordinate shifted when closing history drawer")
        self.assertFalse(win.history_drawer.isVisible())
        win.close()

    def test_history_drawer_blur_and_transparency_styling(self):
        tm = ThemeManager()
        # When blur is enabled
        qss_blur = tm.generate_qss(blur_enabled=True, window_transparency=65)
        self.assertIn("QFrame#HistoryDrawer {", qss_blur)
        self.assertIn("rgba(", qss_blur)
        self.assertIn("QLineEdit#HistorySearch {", qss_blur)
        self.assertIn("QFrame.historyCard", qss_blur)

        # When blur is disabled
        qss_solid = tm.generate_qss(blur_enabled=False)
        tokens = tm.current_tokens
        self.assertIn(f"QFrame#HistoryDrawer {{\n            background-color: {tokens['bg_surface']};", qss_solid)
        self.assertIn(f"QFrame.historyCard, QFrame[class=\"historyCard\"] {{\n            background-color: {tokens['bg_card']};", qss_solid)

    def test_window_transparency_scaling(self):
        # Validates that theme manager scales transparency smoothly across 0-25 range
        tm = ThemeManager()
        qss_0 = tm.generate_qss(transparency_enabled=True, window_transparency=0)
        qss_25 = tm.generate_qss(transparency_enabled=True, window_transparency=25)
        qss_solid = tm.generate_qss(transparency_enabled=False)
        self.assertIn("rgba", qss_25)
        self.assertIn("background-color:", qss_solid)
        # Verify sidebar is always solid hex, never rgba
        self.assertIn(f"background-color: {tm.current_tokens['bg_surface']};", qss_25)

    def test_hit_testing_empty_space_and_titlebar(self):
        from src.ui.main_window import MainWindow
        from PyQt6.QtCore import QPoint
        win = MainWindow(check_updates=False)
        win.resize(360, 580)
        win.show()
        QApplication.instance().processEvents()

        # Title bar empty space should return HTCAPTION (2) so window can be dragged
        pos_tb = win.mapToGlobal(QPoint(150, 15))
        res_tb = win._handle_nchittest(pos_tb.x(), pos_tb.y())
        self.assertEqual(res_tb, 2)  # HTCAPTION

        # Display area empty space should return HTCLIENT (1) so mouse focuses on app
        pos_disp = win.mapToGlobal(QPoint(150, 80))
        res_disp = win._handle_nchittest(pos_disp.x(), pos_disp.y())
        self.assertEqual(res_disp, 1)  # HTCLIENT

        # Keypad button area should return HTCLIENT (1)
        pos_btn = win.mapToGlobal(QPoint(100, 300))
        res_btn = win._handle_nchittest(pos_btn.x(), pos_btn.y())
        self.assertEqual(res_btn, 1)  # HTCLIENT
        win.close()

    def test_maximize_aero_snap_and_restore(self):
        from src.ui.main_window import MainWindow
        win = MainWindow(check_updates=False)
        win._switch_mode("Standard", save_config=False)
        win.config.set("window_width", 360, auto_save=False)
        win.config.set("window_height", 580, auto_save=False)
        win.show()
        win.resize(360, 580)
        QApplication.instance().processEvents()
        initial_w = win.width()

        # Simulate maximize
        win.showMaximized()
        QApplication.instance().processEvents()
        self.assertTrue(win.isMaximized())
        self.assertEqual(win.root_container.width(), win.width())
        self.assertEqual(win.keypad.width(), win.width())

        # Simulate restore
        win.showNormal()
        QApplication.instance().processEvents()
        self.assertFalse(win.isMaximized())
        self.assertEqual(win.width(), initial_w)
        self.assertEqual(win.root_container.width(), initial_w)
        win.close()

    def test_config_schema_migration_backward_compatibility(self):
        """Validates that ConfigManager automatically migrates legacy schema v1 to v2 safely."""
        from src.core.config import ConfigManager, CURRENT_SCHEMA_VERSION
        import tempfile
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_cfg = Path(tmp_dir) / "config.json"
            # Write legacy schema v1 configuration
            legacy_data = {
                "theme_id": "dark_cyberpunk",
                "mode": "Scientific",
                "blur_enabled": False,
                "blur_intensity": "strong",
                "window_transparency": 60,
                "always_on_top": True
            }
            with open(tmp_cfg, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            cm = ConfigManager()
            cm.config_path = tmp_cfg
            cm.load()

            # Verify migration occurred
            self.assertEqual(cm.get("schema_version"), CURRENT_SCHEMA_VERSION)
            self.assertFalse(cm.get("transparency_enabled"))
            # Legacy blur_enabled should fallback cleanly to transparency_enabled
            self.assertFalse(cm.get("blur_enabled"))
            # Obsolete blur_intensity fallback to 'none'
            self.assertEqual(cm.get("blur_intensity"), "none")
            # window_transparency scaled down from 60 (out of 100) to 0-25 range: round((60/100)*25) = 15
            self.assertLessEqual(cm.get("window_transparency"), 25)
            self.assertEqual(cm.get("window_transparency"), 15)
            # Preserved custom user values
            self.assertEqual(cm.get("theme_id"), "dark_cyberpunk")
            self.assertEqual(cm.get("mode"), "Scientific")
            self.assertTrue(cm.get("always_on_top"))

            # Check that file on disk was cleanly rewritten without obsolete keys
            with open(tmp_cfg, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertNotIn("blur_enabled", saved)
            self.assertNotIn("blur_intensity", saved)
            self.assertIn("transparency_enabled", saved)
            self.assertEqual(saved["schema_version"], 2)


if __name__ == "__main__":
    unittest.main()
