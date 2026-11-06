"""
Verification tests for:
- Settings ThemeDialog modal styling and custom title bar
- Window control buttons (translucent hover, intense click, green/yellow/red)
- Scientific mode Trigonometry and Function SVG compound dropdowns
- Native Win32 frameless hit-testing and edge/corner resizing
- Sidebar menu hover highlighting and scroll isolation
- Non-editable 'Invalid input' display presentation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QEnterEvent, QMouseEvent, QPixmap, QPainter
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.theme_dialog import ThemeDialog
from src.ui.theme_manager import ThemeManager
from src.ui.keypad_widget import KeypadWidget, SciDropdownButton
from src.ui.display_widget import DualTierDisplay
from src.ui.date_calc_view import DateCalcView
from src.ui.history_drawer import HistoryDrawer, HistoryConfirmDialog
from src.database.history_db import HistoryDB
import tempfile
import os
import json
from src.ui.title_bar import TITLE_BUTTON_STYLES, CustomTitleBar, DialogTitleBar
from src.ui.native_window import (
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT,
    HTTOP, HTBOTTOM, HTLEFT, HTRIGHT,
    HTMAXBUTTON, HTCLIENT, HTCAPTION
)

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestV2Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win._disable_win32_filter_for_testing = True
        cls.win.resize(360, 580)
        cls.win.show()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls.win, "_native_event_filter") and cls.win._native_event_filter:
            app_inst = QApplication.instance()
            if app_inst:
                app_inst.removeNativeEventFilter(cls.win._native_event_filter)
            cls.win._native_event_filter = None
        cls.win.close()

    # ─── 1. SETTINGS MODAL DIALOG ────────────────────────────────────
    def test_settings_modal_custom_titlebar_and_theme(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        dlg = ThemeDialog(theme_mgr, self.win)

        # Verify frameless flag
        self.assertTrue(bool(dlg.windowFlags() & Qt.WindowType.FramelessWindowHint))
        # Verify custom DialogTitleBar
        self.assertIsInstance(dlg.title_bar, DialogTitleBar)
        self.assertIsNotNone(dlg.title_bar.btn_close)
        self.assertEqual(dlg.title_bar.btn_close.objectName(), "winBtnClose")

        # Verify theme stylesheet applied
        qss = dlg.styleSheet()
        self.assertIn("QDialog#ThemeDialog", qss)
        self.assertIn("QWidget#dialogTitleBar", qss)
        self.assertIn(theme_mgr.current_tokens["bg_base"], qss)

    # ─── 2. WINDOW CONTROL BUTTONS STYLING ───────────────────────────
    def test_window_control_buttons_colors(self):
        tb = self.win.title_bar
        self.assertEqual(tb.btn_minimize.objectName(), "winBtnMinimize")
        self.assertEqual(tb.btn_maximize.objectName(), "winBtnMaximize")
        self.assertEqual(tb.btn_close.objectName(), "winBtnClose")

        # Minimize: Green
        self.assertIn("QPushButton#winBtnMinimize:hover", TITLE_BUTTON_STYLES)
        self.assertIn("rgba(34, 197, 94, 0.25)", TITLE_BUTTON_STYLES)
        self.assertIn("#22C55E", TITLE_BUTTON_STYLES)

        # Maximize: Yellow
        self.assertIn("QPushButton#winBtnMaximize:hover", TITLE_BUTTON_STYLES)
        self.assertIn("rgba(234, 179, 8, 0.28)", TITLE_BUTTON_STYLES)
        self.assertIn("#EAB308", TITLE_BUTTON_STYLES)

        # Close: Red
        self.assertIn("QPushButton#winBtnClose:hover", TITLE_BUTTON_STYLES)
        self.assertIn("rgba(239, 68, 68, 0.35)", TITLE_BUTTON_STYLES)
        self.assertIn("#EF4444", TITLE_BUTTON_STYLES)

    # ─── 3. SCIENTIFIC MODE DROPDOWN ICONS ───────────────────────────
    def test_scientific_dropdown_icons(self):
        keypad = KeypadWidget(mode="Scientific")
        self.assertIsInstance(keypad.btn_trig, SciDropdownButton)
        self.assertIsInstance(keypad.btn_func, SciDropdownButton)

        # Verify labels and icons exist
        self.assertEqual(keypad.btn_trig.lbl_text.text(), "Trigonometry")
        self.assertEqual(keypad.btn_func.lbl_text.text(), "Function")
        self.assertFalse(keypad.btn_trig.lbl_icon.pixmap().isNull())
        self.assertFalse(keypad.btn_trig.lbl_chevron.pixmap().isNull())
        self.assertFalse(keypad.btn_func.lbl_icon.pixmap().isNull())
        self.assertFalse(keypad.btn_func.lbl_chevron.pixmap().isNull())

    # ─── 4. WIN32 NATIVE RESIZING & HIT TESTING ─────────────────────
    def test_native_nchittest_edges_and_corners(self):
        w = self.win.width()
        h = self.win.height()
        top_left = self.win.mapToGlobal(QPoint(1, 1))
        top_right = self.win.mapToGlobal(QPoint(w - 2, 1))
        bottom_left = self.win.mapToGlobal(QPoint(1, h - 2))
        bottom_right = self.win.mapToGlobal(QPoint(w - 2, h - 2))

        # Corners
        self.assertEqual(self.win._handle_nchittest(top_left.x(), top_left.y()), HTTOPLEFT)
        self.assertEqual(self.win._handle_nchittest(top_right.x(), top_right.y()), HTTOPRIGHT)
        self.assertEqual(self.win._handle_nchittest(bottom_left.x(), bottom_left.y()), HTBOTTOMLEFT)
        self.assertEqual(self.win._handle_nchittest(bottom_right.x(), bottom_right.y()), HTBOTTOMRIGHT)

        # Edges
        left_edge = self.win.mapToGlobal(QPoint(1, h // 2))
        right_edge = self.win.mapToGlobal(QPoint(w - 2, h // 2))
        bottom_edge = self.win.mapToGlobal(QPoint(w // 2, h - 2))
        self.assertEqual(self.win._handle_nchittest(left_edge.x(), left_edge.y()), HTLEFT)
        self.assertEqual(self.win._handle_nchittest(right_edge.x(), right_edge.y()), HTRIGHT)
        self.assertEqual(self.win._handle_nchittest(bottom_edge.x(), bottom_edge.y()), HTBOTTOM)

        # Title bar controls
        p_max = self.win.btn_maximize.mapToGlobal(self.win.btn_maximize.rect().center())
        self.assertEqual(self.win._handle_nchittest(p_max.x(), p_max.y()), HTMAXBUTTON)

        p_close = self.win.btn_close.mapToGlobal(self.win.btn_close.rect().center())
        self.assertEqual(self.win._handle_nchittest(p_close.x(), p_close.y()), HTCLIENT)

        p_title = self.win.title_bar.mapToGlobal(QPoint(100, 15))
        self.assertEqual(self.win._handle_nchittest(p_title.x(), p_title.y()), HTCAPTION)

    # ─── 5. SIDEBAR MENU HOVER VISIBILITY ────────────────────────────
    def test_sidebar_hover_color_rendered(self):
        self.win._toggle_sidebar()
        self.assertTrue(self.win.sidebar.isVisible())

        btn = self.win.sidebar.buttons["Programmer"]
        self.assertTrue(btn.testAttribute(Qt.WidgetAttribute.WA_Hover))

        # Check render before hover
        btn_pos = btn.mapTo(self.win.sidebar, btn.rect().center())
        pix_before = QPixmap(self.win.sidebar.size())
        pix_before.fill(Qt.GlobalColor.black)
        p = QPainter(pix_before)
        self.win.sidebar.render(p)
        p.end()
        c_before = pix_before.toImage().pixel(btn_pos)

        # Simulate mouse hover
        btn.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
        app.sendEvent(btn, QEnterEvent(QPointF(20, 15), QPointF(20, 15), QPointF(20, 15)))
        app.sendEvent(btn, QMouseEvent(
            QMouseEvent.Type.MouseMove, QPointF(20, 15),
            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier
        ))
        app.processEvents()

        pix_after = QPixmap(self.win.sidebar.size())
        pix_after.fill(Qt.GlobalColor.black)
        p2 = QPainter(pix_after)
        self.win.sidebar.render(p2)
        p2.end()
        c_after = pix_after.toImage().pixel(btn_pos)

        # Color MUST transition to hover color
        self.assertNotEqual(c_before, c_after)
        self.win._toggle_sidebar()

    # ─── 6. NON-EDITABLE 'INVALID INPUT' DISPLAY ─────────────────────
    def test_invalid_input_non_editable_display(self):
        display = DualTierDisplay()

        # Normal value -> ArrowCursor (no blinking editing cursor, one-direction typing)
        display.set_drafting_state("", "12345")
        self.assertFalse(display.primary_display.isReadOnly())
        self.assertFalse(display.primary_display.property("is_error"))
        self.assertEqual(display.primary_display.cursor().shape(), Qt.CursorShape.ArrowCursor)

        # Invalid input -> read-only and error styled
        display.set_drafting_state("", "Invalid input")
        self.assertTrue(display.primary_display.isReadOnly())
        self.assertTrue(display.primary_display.property("is_error"))
        self.assertEqual(display.primary_display.cursor().shape(), Qt.CursorShape.ArrowCursor)

        # Cannot divide by zero -> read-only and error styled
        display.set_evaluated_state("1 / 0 =", "Cannot divide by zero")
        self.assertTrue(display.primary_display.isReadOnly())
        self.assertTrue(display.primary_display.property("is_error"))

        # Restoring normal number -> re-enables drafting
        display.set_drafting_state("", "99")
        self.assertFalse(display.primary_display.isReadOnly())
        self.assertFalse(display.primary_display.property("is_error"))
        self.assertEqual(display.primary_display.cursor().shape(), Qt.CursorShape.ArrowCursor)

    # ─── 7. SETTINGS UPDATES TAB & VERSION BROWSER ───────────────────
    def test_settings_updates_tab_and_version_info(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        dlg = ThemeDialog(theme_mgr, self.win)
        self.assertEqual(dlg.tabs.count(), 2)
        self.assertEqual(dlg.tabs.tabText(0), "Themes & Colors")
        self.assertEqual(dlg.tabs.tabText(1), "Updates & Versions")
        self.assertIsNotNone(dlg.btn_check_updates)
        self.assertIsNotNone(dlg.builds_combo)
        self.assertEqual(dlg.btn_check_updates.text(), "Check for Updates")
        from src.version import APP_VERSION
        self.assertIn(f"v{APP_VERSION}", dlg.version_footer_lbl.text())

    # ─── 8. DATE CALCULATION MODE INTEGRATION ────────────────────────
    def test_date_mode_switching_and_view(self):
        self.win._switch_mode("Date Calculation", save_config=False)
        self.assertEqual(self.win.stack.currentIndex(), 2)
        self.assertIsInstance(self.win.date_calc_page, DateCalcView)
        self.assertFalse(self.win.display.isVisible())
        self.assertFalse(self.win.mem_bar.isVisible())
        self.assertFalse(self.win.history_btn.isVisible())

        # Switch back to Standard
        self.win._switch_mode("Standard", save_config=False)
        self.assertEqual(self.win.stack.currentIndex(), 0)
        self.assertTrue(self.win.display.isVisible())
        self.assertTrue(self.win.mem_bar.isVisible())

    # ─── 9. SCIENTIFIC MODE FULL EXPRESSION TYPING & LIVE PREVIEW ────
    def test_scientific_full_expression_typing_and_live_preview(self):
        self.win._switch_mode("Scientific", save_config=False)
        self.win.state.clear_all()

        # Type full expression
        self.win.display.primary_display.setText("sin(30)")
        self.win.display.primary_display.textEdited.emit("sin(30)")
        app.processEvents()

        # Ghost preview should display "= 0.5"
        self.assertEqual(self.win.display.ghost_preview.text(), "= 0.5")

        # Press equals
        self.win.state.evaluate()
        app.processEvents()

        # Evaluated state pins the expression and sets primary result
        self.assertEqual(self.win.display.primary_display.text(), "0.5")
        self.assertIn("sin(30)", self.win.display.expression_label.text())

    # ─── 10. HISTORY DELETION CONFIRMATION ────────────────────────────
    def test_history_delete_confirmation_dialog(self):
        db = HistoryDB(db_path=":memory:")
        db.add_calculation("2 + 2", "4", "Standard")
        grouped = db.get_grouped_history()
        self.assertGreaterEqual(len(grouped[0]["calculations"]), 1)

        dlg = HistoryConfirmDialog()
        self.assertIsInstance(dlg.title_bar, DialogTitleBar)
        self.assertEqual(dlg.title_bar.lbl_title.text(), "Clear History")

        # Reject preserves history
        dlg.reject()
        grouped_after = db.get_grouped_history()
        self.assertGreaterEqual(len(grouped_after[0]["calculations"]), 1)
        db.close()

    # ─── 11. CUSTOM THEME NAMING AUTO-INCREMENT & STORAGE ────────────
    def test_custom_theme_naming_and_persistence(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_custom_file = Path(f.name)
        theme_mgr.custom_themes_file = temp_custom_file

        try:
            next_name = theme_mgr.get_next_custom_theme_name()
            self.assertTrue(next_name.startswith("CustomTheme"))

            # Save custom theme
            t_id = theme_mgr.save_new_custom_theme(next_name, theme_mgr.current_tokens)
            self.assertIn(t_id, theme_mgr.themes)
            self.assertEqual(theme_mgr.themes[t_id]["name"], next_name)

            # Next name should increment
            next_num_name = theme_mgr.get_next_custom_theme_name()
            self.assertNotEqual(next_name, next_num_name)
        finally:
            if temp_custom_file.exists():
                temp_custom_file.unlink()

    # ─── 12. THEME EXPORT AND IMPORT ─────────────────────────────────
    def test_theme_export_and_import(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2:
            temp_custom_file = Path(f2.name)
        theme_mgr.custom_themes_file = temp_custom_file

        try:
            # Export
            success = theme_mgr.export_theme("dark_monokai", temp_path)
            self.assertTrue(success)

            # Import
            imp_success, imp_id, msg = theme_mgr.import_theme(temp_path)
            self.assertTrue(imp_success)
            self.assertIn(imp_id, theme_mgr.themes)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if temp_custom_file.exists():
                temp_custom_file.unlink()

    # ─── 13. SYNCED HEX INPUT & COLOR BOX ────────────────────────────
    def test_synced_hex_input_and_swatch(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        dlg = ThemeDialog(theme_mgr, self.win)

        hex_input = dlg.hex_inputs["bg_base"]
        swatch = dlg.swatch_buttons["bg_base"]

        # User types hex without #
        hex_input.setText("ff0055")
        app.processEvents()
        self.assertEqual(dlg.temp_tokens["bg_base"], "#FF0055")
        self.assertIn("#FF0055", swatch.styleSheet())

        # User types with #
        hex_input.setText("#00AAFF")
        app.processEvents()
        self.assertEqual(dlg.temp_tokens["bg_base"], "#00AAFF")
        self.assertIn("#00AAFF", swatch.styleSheet())

    # ─── 14. SCIENTIFIC DROPDOWN MINIMUM WIDTH (IMAGE 1 FIX) ────────
    def test_scientific_dropdown_widths_no_clipping(self):
        keypad = KeypadWidget(mode="Scientific")
        self.assertGreaterEqual(keypad.btn_trig.minimumWidth(), 95)
        self.assertGreaterEqual(keypad.btn_func.minimumWidth(), 95)
        self.assertGreaterEqual(keypad.btn_trig.sizeHint().width(), 95)
        self.assertGreaterEqual(keypad.btn_func.sizeHint().width(), 95)

    # ─── 15. ACTIVE SIDEBAR ITEM STYLING (MIDDLE INDICATOR ONLY) ─────
    def test_sidebar_active_mode_styling_qss(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        qss = theme_mgr.generate_qss()
        # Verify active mode has transparent background (no full highlight)
        self.assertIn("background-color: transparent;", qss)
        self.assertIn("QFrame#SidebarSettingsDivider", qss)

    # ─── 16. FLOATING TRIGONOMETRY AND FUNCTION POPOVERS ─────────────
    def test_floating_popovers_trig_and_func(self):
        keypad = KeypadWidget(mode="Scientific")
        keypad.resize(450, 400)
        keypad.show()
        app.processEvents()

        # Initially invisible
        self.assertFalse(keypad.trig_popover.isVisible())
        self.assertFalse(keypad.func_popover.isVisible())

        # Click trig button
        keypad.btn_trig.click()
        app.processEvents()
        self.assertTrue(keypad.trig_popover.isVisible())
        self.assertFalse(keypad.func_popover.isVisible())

        # Click func button (closes trig, opens func)
        keypad.btn_func.click()
        app.processEvents()
        self.assertFalse(keypad.trig_popover.isVisible())
        self.assertTrue(keypad.func_popover.isVisible())

        # Click func button again (closes func)
        keypad.btn_func.click()
        app.processEvents()
        self.assertFalse(keypad.func_popover.isVisible())

    # ─── 17. DATE CALCULATION DISPLAY FORMAT DD-MM-YYYY ──────────────
    def test_date_calc_display_format_and_picker(self):
        view = DateCalcView()
        self.assertEqual(view.from_date_edit.displayFormat(), "dd-MM-yyyy")
        self.assertEqual(view.to_date_edit.displayFormat(), "dd-MM-yyyy")
        self.assertEqual(view.addsub_from_edit.displayFormat(), "dd-MM-yyyy")
        self.assertTrue(view.from_date_edit.calendarPopup())

    # ─── 18. THEME DIALOG SAVE CUSTOM PALETTE BUTTON VISIBILITY ───────
    def test_save_custom_palette_button_visibility(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        dlg = ThemeDialog(theme_mgr, self.win)
        dlg.show()
        app.processEvents()

        # On stock preset, Save Custom Palette is hidden
        self.assertTrue(dlg.save_btn.isHidden())

        # Modify a token so palette becomes custom
        dlg.hex_inputs["bg_base"].setText("#123456")
        app.processEvents()
        self.assertFalse(dlg.save_btn.isHidden())
        self.assertEqual(dlg.save_btn.text(), "Save Custom Palette")
        self.assertEqual(dlg.save_btn.width(), 200)
        dlg.close()

    # ─── 19. THEME IMPORT DATA AND RAW JSON VALIDATION ───────────────
    def test_theme_import_data_validation(self):
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_custom_file = Path(f.name)
        theme_mgr.custom_themes_file = temp_custom_file

        try:
            invalid_data = {"foo": "bar"}
            success, _, msg = theme_mgr.import_theme_data(invalid_data)
            self.assertFalse(success)
            self.assertIn("missing essential color tokens", msg)

            valid_data = {
                "name": "Emerald Test",
                "bg_base": "#052e16",
                "bg_card": "#14532d",
                "accent_primary": "#22c55e"
            }
            success, t_id, msg = theme_mgr.import_theme_data(valid_data)
            self.assertTrue(success)
            self.assertIn(t_id, theme_mgr.themes)
            self.assertEqual(theme_mgr.themes[t_id]["name"], "Emerald Test")
        finally:
            if temp_custom_file.exists():
                temp_custom_file.unlink()

    # ─── 20. HISTORY DRAWER DEACTIVATED ON EMPTY & NO NEW SESSION ────
    def test_history_drawer_empty_deactivation(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        temp_db = HistoryDB(temp_db_path)

        try:
            drawer = HistoryDrawer(temp_db)
            # Verify new session button does not exist
            self.assertFalse(hasattr(drawer, "new_sess_btn"))

            # When history is empty, action buttons are disabled
            self.assertFalse(drawer.export_btn.isEnabled())
            self.assertFalse(drawer.clear_btn.isEnabled())
            self.assertFalse(drawer.search_box.isEnabled())

            # Insert an item -> buttons become enabled
            temp_db.add_calculation("Standard", "2 + 2", "4")
            drawer.refresh_history()
            self.assertTrue(drawer.export_btn.isEnabled())
            self.assertTrue(drawer.clear_btn.isEnabled())
            self.assertTrue(drawer.search_box.isEnabled())
        finally:
            temp_db.close()
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

    # ─── 21. GRAPHING VIEW RESPONSIVE DUAL-PANE & KEYPAD INPUT ───────
    def test_graphing_view_responsive_layout_and_keypad(self):
        from src.ui.graphing_view import GraphingView
        view = GraphingView()
        view.show()

        # Wide layout (>= 500px)
        view.resize(720, 600)
        view._update_responsive_layout()
        app.processEvents()
        self.assertFalse(view.mode_selector_bar.isVisible())
        self.assertTrue(view.left_pane.isVisible())
        self.assertTrue(view.right_pane.isVisible())

        # Test keypad input into active row
        active_row = view._get_active_row()
        self.assertIsNotNone(active_row)
        active_row.expr_input.clear()

        # Type via keypad signals
        view.keypad.insertToken.emit("x")
        view.keypad.insertToken.emit("^")
        view.keypad.insertToken.emit("3")
        app.processEvents()
        self.assertEqual(active_row.expr_input.text(), "x^3")

        # Test Options popover toggle
        self.assertFalse(view.canvas.options_popover.isVisible())
        view.canvas.btn_options.click()
        app.processEvents()
        self.assertTrue(view.canvas.options_popover.isVisible())
        view.close()

    # ─── 22. ENERGY ICON FIRE FLAME SVG ──────────────────────────────
    def test_energy_icon_fire_svg(self):
        from src.ui.mode_icons import MODE_SVGS
        energy_svg = MODE_SVGS.get("Energy", "")
        self.assertIn("<svg", energy_svg)
        # Verify outer flame and inner flame curves
        self.assertIn("18.5", energy_svg)

    # ─── 23. THEME MODE TOGGLE & PRESETS FILTERING ────────────────────
    def test_theme_mode_toggle_and_presets_filtering(self):
        from src.ui.theme_dialog import ThemeDialog
        from src.ui.theme_manager import ThemeManager
        theme_mgr = ThemeManager(initial_theme_id="dark_monokai")
        dlg = ThemeDialog(theme_mgr, self.win)
        dlg.show()
        app.processEvents()

        # In dark mode, preset items should only contain dark presets
        for i in range(dlg.preset_combo.count()):
            t_id = dlg.preset_combo.itemData(i)
            from src.ui.theme_manager import BUILTIN_THEMES
            self.assertEqual(BUILTIN_THEMES[t_id]["category"], "dark")

        # Toggle to light mode
        dlg.mode_toggle.set_dark_mode(False, animate=False)
        app.processEvents()
        self.assertEqual(dlg.mode_desc_lbl.text(), "Light")

        # Preset items should now only contain light presets
        for i in range(dlg.preset_combo.count()):
            t_id = dlg.preset_combo.itemData(i)
            self.assertEqual(BUILTIN_THEMES[t_id]["category"], "light")

        dlg.close()

    # ─── 24. HISTORY DRAWER CLEAN VECTOR CLOSE ICON ───────────────────
    def test_history_drawer_vector_close_icon(self):
        self.win._toggle_history_drawer()
        app.processEvents()
        self.assertTrue(self.win.history_drawer.isVisible())
        # Verify close button does not use unicode "✕" text
        self.assertEqual(self.win.history_drawer.close_btn.text(), "")
        self.assertFalse(self.win.history_drawer.close_btn.icon().isNull())
        self.win._toggle_history_drawer()
        app.processEvents()

    # ─── 25. GRAPHING FUNCTION ROW EYE & CLOSE VECTOR ICONS ──────────
    def test_graphing_function_row_vector_icons(self):
        from src.ui.graphing_view import FunctionRowWidget
        row = FunctionRowWidget(index=0, initial_expr="x^2", color="#38BDF8")
        row.show()
        app.processEvents()
        # Ensure buttons use icons, not letter characters "V" or "X"
        self.assertEqual(row.btn_vis.text(), "")
        self.assertFalse(row.btn_vis.icon().isNull())
        self.assertEqual(row.btn_del.text(), "")
        self.assertFalse(row.btn_del.icon().isNull())
        # Toggle visibility
        row.btn_vis.click()
        app.processEvents()
        self.assertFalse(row.graph_fn.is_visible)
        self.assertFalse(row.btn_vis.icon().isNull())
        row.close()

    # ─── 26. DATE CALCULATION BOUNDARIES & ARITHMETIC CLAMPING ────────
    def test_date_calculation_limits_and_clamping(self):
        from datetime import date
        from src.core.date_engine import add_subtract_duration, MIN_DATE, MAX_DATE
        # Adding 10,000 years must safely clamp to MAX_DATE without raising ValueError
        d_add = add_subtract_duration(date(2026, 11, 6), years=10000, months=0, days=0, add=True)
        self.assertEqual(d_add, MAX_DATE)
        # Subtracting 3,000 years must safely clamp to MIN_DATE without raising ValueError
        d_sub = add_subtract_duration(date(2026, 11, 6), years=3000, months=0, days=0, add=False)
        self.assertEqual(d_sub, MIN_DATE)
        # Date view widgets have proper date ranges
        view = DateCalcView()
        self.assertEqual(view.from_date_edit.minimumDate().year(), 1900)
        self.assertEqual(view.from_date_edit.maximumDate().year(), 9999)

    # ─── 27. GRAPH OPTIONS POPOVER BOUNDS & CLOSE ICON ────────────────
    def test_graph_options_popover_bounds_and_theme(self):
        from src.ui.graph_canvas import GraphCanvas
        canvas = GraphCanvas()
        pop = canvas.options_popover
        pop.show()
        app.processEvents()
        self.assertEqual(pop.close_btn.text(), "")
        self.assertFalse(pop.close_btn.icon().isNull())
        self.assertEqual(pop.xmin_input.text(), "-10")
        self.assertEqual(pop.xmax_input.text(), "10")
        pop.close()

    # ─── 28. LICENSE COMMIT FILTERING IN VERSION PICKER ───────────────
    def test_license_commit_ignored_in_version_picker(self):
        from src.core.updater import is_license_entry
        self.assertTrue(is_license_entry({"tag_name": "license"}))
        self.assertTrue(is_license_entry({"name": "Initial license commit"}))
        self.assertTrue(is_license_entry({"commit": {"message": "Add LICENSE.md"}}))
        self.assertTrue(is_license_entry({"body": "Updated MIT license terms"}))
        self.assertFalse(is_license_entry({"tag_name": "v0.2.0", "name": "Release 0.2.0", "body": "Feature release"}))

    # ─── 29. HAMBURGER BUTTON SIZING AND ICON ─────────────────────────
    def test_hamburger_button_sizing_and_icon(self):
        self.assertEqual(self.win.hamburger_btn.width(), 36)
        self.assertEqual(self.win.hamburger_btn.height(), 32)
        self.assertEqual(self.win.hamburger_btn.iconSize().width(), 20)
        self.assertEqual(self.win.hamburger_btn.iconSize().height(), 20)

    # ─── 30. DROPDOWN FLYOUT GRIDS IN SCIENTIFIC & GRAPHING KEYPADS ───
    def test_dropdown_flyout_grids_and_theme_styling(self):
        # 1. Scientific mode dropdowns
        self.win._switch_mode("Scientific", save_config=False)
        kp = self.win.keypad
        kp.btn_trig.click()
        app.processEvents()
        self.assertTrue(kp.trig_popover.isVisible())
        self.assertEqual(kp.trig_popover.width(), 232)
        self.assertEqual(kp.trig_popover.height(), 66)
        kp.btn_trig.click()
        app.processEvents()
        self.assertFalse(kp.trig_popover.isVisible())

        kp.btn_func.click()
        app.processEvents()
        self.assertTrue(kp.func_popover.isVisible())
        self.assertEqual(kp.func_popover.width(), 176)
        self.assertEqual(kp.func_popover.height(), 66)
        kp.btn_func.click()
        app.processEvents()

        # 2. Graphing mode dropdowns
        self.win.resize(750, 600)
        self.win._switch_mode("Graphing", save_config=False)
        app.processEvents()
        g_kp = self.win.graphing_page.keypad
        g_kp.btn_trig.click()
        app.processEvents()
        self.assertTrue(g_kp.trig_popover.isVisible())
        self.assertEqual(g_kp.trig_popover.width(), 232)
        self.assertEqual(g_kp.trig_popover.height(), 66)
        g_kp.btn_trig.click()
        app.processEvents()

        g_kp.btn_ineq.click()
        app.processEvents()
        self.assertTrue(g_kp.ineq_popover.isVisible())
        self.assertEqual(g_kp.ineq_popover.width(), 112)
        self.assertEqual(g_kp.ineq_popover.height(), 66)
        g_kp.btn_ineq.click()
        app.processEvents()

        g_kp.btn_func.click()
        app.processEvents()
        self.assertTrue(g_kp.func_popover.isVisible())
        self.assertEqual(g_kp.func_popover.width(), 176)
        self.assertEqual(g_kp.func_popover.height(), 66)
        g_kp.btn_func.click()
        app.processEvents()

    # ─── 31. OPERATOR TRAILING PREVIEW SUPPRESSION ACROSS MODES ────────
    def test_operator_trailing_preview_suppression_all_modes(self):
        # Test Standard Mode: 60 + should NOT preview = 120 or ribbon 60 + 0
        self.win._switch_mode("Standard", save_config=False)
        self.win.state.clear_all()
        app.processEvents()

        self.win.state.input_digit("6")
        self.win.state.input_digit("0")
        app.processEvents()
        self.assertEqual(self.win.display.primary_display.text(), "60")

        # Press '+'
        self.win.state.input_operator("+")
        app.processEvents()

        # Ribbon must show '60 +' (never '60 + 0')
        self.assertEqual(self.win.display.expression_label.text(), "60 +")
        # Ghost preview must be empty (never '= 120')
        self.assertEqual(self.win.display.ghost_preview.text(), "")
        # Primary display retains 60 until next digit
        self.assertEqual(self.win.display.primary_display.text(), "60")

        # Type '5'
        self.win.state.input_digit("5")
        app.processEvents()
        self.assertEqual(self.win.display.expression_label.text(), "60 + 5")
        self.assertEqual(self.win.display.ghost_preview.text(), "= 65")
        self.assertEqual(self.win.display.primary_display.text(), "5")

        # Press '='
        self.win.state.evaluate()
        app.processEvents()
        self.assertEqual(self.win.display.primary_display.text(), "65")
        self.assertEqual(self.win.display.ghost_preview.text(), "")

        # Test other operators: -, ×, ÷, %
        for op in ("−", "×", "÷", "%"):
            self.win.state.clear_all()
            app.processEvents()
            self.win.state.input_digit("6")
            self.win.state.input_digit("0")
            self.win.state.input_operator(op)
            app.processEvents()
            self.assertEqual(self.win.display.ghost_preview.text(), "", f"Operator {op} should have empty preview")
            self.assertNotIn(" 0", self.win.display.expression_label.text())

        # Test Programmer Mode operators: AND, OR, XOR, mod, <<, >>
        self.win._switch_mode("Programmer", save_config=False)
        for prog_op in ("AND", "OR", "XOR", "mod", "<<", ">>"):
            self.win.state.clear_all()
            app.processEvents()
            self.win.state.input_digit("6")
            self.win.state.input_digit("0")
            self.win.state.input_operator(prog_op)
            app.processEvents()
            self.assertEqual(self.win.display.ghost_preview.text(), "", f"Prog op {prog_op} should have empty preview")
            self.assertNotIn(" 0", self.win.display.expression_label.text())

        # Test Scientific Mode typing directly in field: "60 +" -> empty, "60 + 5" -> = 65
        self.win._switch_mode("Scientific", save_config=False)
        self.win.state.clear_all()
        app.processEvents()
        self.win.display.primary_display.setText("60 +")
        self.win.display.primary_display.textEdited.emit("60 +")
        app.processEvents()
        self.assertEqual(self.win.display.ghost_preview.text(), "")

        self.win.display.primary_display.setText("60 + 5")
        self.win.display.primary_display.textEdited.emit("60 + 5")
        app.processEvents()
        self.assertEqual(self.win.display.ghost_preview.text(), "= 65")

        # Incomplete "60 + 5 *" -> empty
        self.win.display.primary_display.setText("60 + 5 *")
        self.win.display.primary_display.textEdited.emit("60 + 5 *")
        app.processEvents()
        self.assertEqual(self.win.display.ghost_preview.text(), "")

        # Complete "60 + 5 * 2" -> = 70
        self.win.display.primary_display.setText("60 + 5 * 2")
        self.win.display.primary_display.textEdited.emit("60 + 5 * 2")
        app.processEvents()
        self.assertEqual(self.win.display.ghost_preview.text(), "= 70")

    # ─── 32. TASKBAR APP USER MODEL ID & ICON RESOLUTION ───────────────
    def test_taskbar_app_user_model_id_and_icon(self):
        import sys
        if sys.platform == "win32":
            import ctypes
            res = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Usama1k99.CustomCalculator.App.0.2.0")
            self.assertEqual(res, 0)
        self.assertFalse(self.win.windowIcon().isNull())

    # ─── 33. THEMED SVG PATH ENGINE & FORWARD SLASH POSIX PATHS ────────
    def test_themed_svg_path_engine(self):
        from src.ui.mode_icons import get_themed_svg_path
        from pathlib import Path
        p1 = get_themed_svg_path("ChevronDown", "#FF0000")
        self.assertTrue(Path(p1).exists())
        self.assertIn("/", p1)
        self.assertNotIn("\\", p1)
        content = Path(p1).read_text(encoding="utf-8")
        self.assertIn("#FF0000", content)

        p2 = get_themed_svg_path("ChevronUp", "#00FF00")
        self.assertTrue(Path(p2).exists())
        self.assertIn("#00FF00", Path(p2).read_text(encoding="utf-8"))

    # ─── 34. SEMVER PARSING AND COMPARISON LOGIC ───────────────────────
    def test_semver_parsing_and_comparison(self):
        from src.core.updater import parse_semver
        self.assertEqual(parse_semver("v0.2.1"), (0, 2, 1))
        self.assertEqual(parse_semver("0.2.0"), (0, 2, 0))
        self.assertEqual(parse_semver("v1.0.0-alpha"), (1, 0, 0))
        self.assertTrue(parse_semver("v0.2.2") > parse_semver("v0.2.1"))
        self.assertTrue(parse_semver("0.2.1") > parse_semver("0.2.0"))
        self.assertFalse(parse_semver("0.2.0") > parse_semver("0.2.1"))

    # ─── 35. LIVE COMMITS FALLBACK AND UPDATER BEHAVIOR ────────────────
    def test_live_commits_fallback_and_updater(self):
        from unittest.mock import patch
        from src.version import APP_VERSION
        from src.core.updater import fetch_all_releases, VersionCheckWorker

        mock_commits = [
            {
                "sha": "abc1234567890",
                "commit": {
                    "message": f"v{APP_VERSION}: Major new feature release\n\nFull details",
                    "committer": {"date": "2026-11-07T00:00:00Z"}
                },
                "html_url": "https://github.com/Usama1k99/Custom-Calculator/commit/abc1234"
            },
            {
                "sha": "def5678901234",
                "commit": {
                    "message": "Update LICENSE\n\nLicense change",
                    "committer": {"date": "2026-11-06T00:00:00Z"}
                },
                "html_url": "https://github.com/Usama1k99/Custom-Calculator/commit/def5678"
            }
        ]

        # Test fetch_all_releases fallback when releases endpoint is empty
        def mock_urlopen(req, timeout=None):
            class MockResponse:
                def __init__(self, data):
                    self.data = data
                def read(self):
                    return json.dumps(self.data).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            if "releases" in req.full_url:
                return MockResponse([])
            elif "commits" in req.full_url:
                return MockResponse(mock_commits)
            return MockResponse([])

        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            releases = fetch_all_releases()
            self.assertEqual(len(releases), 1)
            self.assertEqual(releases[0]["tag_name"], f"v{APP_VERSION}")
            self.assertEqual(releases[0]["target_commitish"], "abc1234")
            self.assertTrue(releases[0]["is_commit_build"])

        # Test VersionCheckWorker: when remote version matches APP_VERSION, no spurious update!
        worker_same = VersionCheckWorker()
        results_same = []
        worker_same.checkCompleted.connect(lambda avail, info: results_same.append((avail, info)))
        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_urlopen):
            worker_same.run()

        self.assertEqual(len(results_same), 1)
        avail, _ = results_same[0]
        self.assertFalse(avail)  # Must be False when on latest release!

        # Test VersionCheckWorker: when remote version is newer (v99.0.0), update IS detected!
        mock_newer_commits = [
            {
                "sha": "9999999",
                "commit": {
                    "message": "v99.0.0: Future update\n\nNotes",
                    "committer": {"date": "2026-11-08T00:00:00Z"}
                },
                "html_url": "https://github.com/Usama1k99/Custom-Calculator/commit/9999999"
            }
        ]
        def mock_newer_urlopen(req, timeout=None):
            class MockResponse:
                def __init__(self, data):
                    self.data = data
                def read(self):
                    return json.dumps(self.data).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            if "releases" in req.full_url:
                return MockResponse([])
            return MockResponse(mock_newer_commits)

        worker_newer = VersionCheckWorker()
        results_newer = []
        worker_newer.checkCompleted.connect(lambda avail, info: results_newer.append((avail, info)))
        with patch("src.core.updater.urllib.request.urlopen", side_effect=mock_newer_urlopen):
            worker_newer.run()

        self.assertEqual(len(results_newer), 1)
        avail_newer, info_newer = results_newer[0]
        self.assertTrue(avail_newer)
        self.assertEqual(info_newer["tag_name"], "v99.0.0")

    # ─── 36. DIRECT EXECUTABLE AUTO-UPDATE RESOLUTION ──────────────────
    def test_get_release_download_url_and_fallbacks(self):
        from src.core.updater import get_release_download_url
        # 1. From release assets
        rel_with_asset = {
            "tag_name": "v0.3.0",
            "assets": [{"name": "CustomCalculator.exe", "browser_download_url": "https://example.com/CustomCalculator.exe"}]
        }
        self.assertEqual(get_release_download_url(rel_with_asset), "https://example.com/CustomCalculator.exe")

        # 2. From tag fallback
        rel_no_asset = {"tag_name": "v0.3.0"}
        self.assertEqual(
            get_release_download_url(rel_no_asset),
            "https://github.com/Usama1k99/Custom-Calculator/releases/download/v0.3.0/CustomCalculator.exe"
        )

        # 3. Canonical latest fallback
        self.assertEqual(
            get_release_download_url({}),
            "https://github.com/Usama1k99/Custom-Calculator/releases/latest/download/CustomCalculator.exe"
        )

    # ─── 37. MAJOR/MINOR RELEASES FILTER ONLY (EXCLUDING PATCHES) ──────
    def test_major_minor_release_filtering(self):
        from scripts.publish_release import is_major_minor_release
        self.assertTrue(is_major_minor_release("0.3.0"))
        self.assertTrue(is_major_minor_release("v0.3.0"))
        self.assertTrue(is_major_minor_release("v1.0.0"))
        self.assertTrue(is_major_minor_release("2.5.0"))
        self.assertFalse(is_major_minor_release("0.2.1"))
        self.assertFalse(is_major_minor_release("v0.3.4"))
        self.assertFalse(is_major_minor_release("1.0.1"))

    # ─── 38. TITLE BAR ICON & SIDEBAR VERSION LABEL ───────────────────
    def test_titlebar_icon_and_sidebar_version_label(self):
        from src.version import APP_VERSION
        # Check title bar icon widget exists and has a non-null pixmap
        self.assertTrue(hasattr(self.win.title_bar, "icon_lbl"))
        self.assertIsNotNone(self.win.title_bar.icon_lbl.pixmap())
        self.assertFalse(self.win.title_bar.icon_lbl.pixmap().isNull())

        # Check sidebar version label exists and matches current APP_VERSION
        self.assertTrue(hasattr(self.win.sidebar, "version_lbl"))
        self.assertEqual(self.win.sidebar.version_lbl.text(), f"v{APP_VERSION}")

    # ─── 39. SWITCH VERSION & INSTALL BUILD WORKER TEST ───────────────
    def test_switch_version_installs_build_without_name_error(self):
        from unittest.mock import patch, MagicMock
        from src.ui.theme_dialog import ThemeDialog
        from src.ui.theme_manager import ThemeManager

        tm = ThemeManager()
        dlg = ThemeDialog(tm, initial_tab=1)
        # Simulate an older build entry like v0.2.2
        older_data = {"tag_name": "v0.2.2", "body": "Release 0.2.2 notes", "assets": []}
        dlg.builds_combo.addItem("v0.2.2", older_data)
        dlg.builds_combo.setCurrentIndex(dlg.builds_combo.count() - 1)

        self.assertFalse(dlg.btn_install_selected.isHidden())
        self.assertEqual(dlg.btn_install_selected.text(), "Switch to v0.2.2")

        with patch("src.ui.theme_dialog.BinaryDownloadWorker") as MockWorker:
            mock_inst = MagicMock()
            MockWorker.return_value = mock_inst
            # Invoking _install_selected_build must not crash with NameError (e.g. tempfile)
            dlg._install_selected_build()
            self.assertTrue(MockWorker.called)
            # Verify out_path was formatted into temp dir
            download_url, out_path = MockWorker.call_args[0]
            self.assertIn("Calculator_v0.2.2.exe", out_path)
            self.assertTrue(mock_inst.start.called)


if __name__ == "__main__":
    unittest.main()
