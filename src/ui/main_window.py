"""
Main Application Window for Custom-Calculator.
Replicates Windows Calculator UI/UX:
- Seamless acrylic glass blur effect via Windows DWM
- Custom title bar with amber/green/red hover highlights (Min/Max/Close)
- Flyout sidebar overlay (slides OVER calculator without squishing buttons)
- Single hamburger menu button
- Blinking clickable writing cursor in primary display
- Complete settings persistence (theme, mode, window size, always-on-top)
- Robust hardware Numpad event handling
"""

from pathlib import Path
import sys
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import QIcon, QKeyEvent, QMouseEvent, QCursor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QStackedWidget, QApplication
)
from src.core.config import ConfigManager
from src.core.engine import MathEngine, AngleMode
from src.core.state import CalculatorState
from src.core.updater import VersionCheckWorker, is_connected_to_internet
from src.database.history_db import HistoryDB
from src.ui.theme_manager import ThemeManager
from src.ui.title_bar import CustomTitleBar
from src.ui.window_effects import apply_window_blur, remove_window_blur
from src.ui.native_window import (
    apply_native_window_frame,
    HTMAXBUTTON, HTCLIENT, HTCAPTION,
    HTLEFT, HTRIGHT, HTTOP, HTBOTTOM,
    HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT
)
from src.ui.display_widget import DualTierDisplay
from src.ui.keypad_widget import KeypadWidget
from src.ui.sidebar_drawer import NavigationSidebar
from src.ui.converter_view import ConverterView
from src.ui.date_calc_view import DateCalcView
from src.ui.graphing_view import GraphingView
from src.ui.history_drawer import HistoryDrawer
from src.ui.theme_dialog import ThemeDialog
from src.ui.update_dialog import UpdatePromptDialog
from src.ui.mode_icons import get_themed_icon
from src.core.crash_reporter import (
    register_context_provider, unregister_context_provider, record_breadcrumb
)
from src.core.input_validator import is_char_allowed, sanitize_leading_zeros


class MainWindow(QMainWindow):
    def __init__(self, check_updates: bool = True):
        super().__init__()

        # ─── 1. FRAMELESS WINDOW & BLUR GLASS SETUP ──────────────────
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._history_auto_expanded_delta = 0

        # Load Configuration
        self.config = ConfigManager()
        saved_theme = self.config.get("theme_id", "dark_monokai")
        saved_mode = self.config.get("mode", "Standard")
        w = self.config.get("window_width", 360)
        h = self.config.get("window_height", 580)
        always_on_top = self.config.get("always_on_top", False)

        self.resize(w, h)
        self.setMinimumSize(320, 520)

        if always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # Set Window Icon (Prefer multi-resolution ICO for native Windows taskbar & alt-tab; fallback to SVG)
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
        icon_ico = base_dir / "assets" / "icons" / "app_icon.ico"
        if not icon_ico.exists():
            icon_ico = Path("assets") / "icons" / "app_icon.ico"
        icon_svg = base_dir / "assets" / "icons" / "app_icon.svg"
        if not icon_svg.exists():
            icon_svg = Path("assets") / "icons" / "app_icon.svg"

        if icon_ico.exists():
            self.setWindowIcon(QIcon(str(icon_ico)))
        elif icon_svg.exists():
            self.setWindowIcon(QIcon(str(icon_svg)))

        # ─── 2. LOGIC INITIALIZATION ─────────────────────────────────
        self.engine = MathEngine()
        self.db = HistoryDB()
        self.theme_mgr = ThemeManager(initial_theme_id=saved_theme)
        self.state = CalculatorState(self.engine, self.db, self._on_calculator_state_changed)

        self._init_ui()
        self._apply_theme()
        self._switch_mode(saved_mode, save_config=False)
        register_context_provider(self._get_crash_context)
        record_breadcrumb("Lifecycle", f"MainWindow initialized with theme '{saved_theme}', mode '{saved_mode}'")
        if check_updates:
            self._start_version_check()

    def _init_ui(self):
        # Master root container holding TitleBar + Central Body
        self.root_container = QWidget(self)
        self.root_container.setObjectName("CentralWidget")
        self.setCentralWidget(self.root_container)

        self.master_layout = QVBoxLayout(self.root_container)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.setSpacing(0)

        # 1. Custom Title Bar with Yellow/Green/Red Window Controls
        self.title_bar = CustomTitleBar(self, title="Calculator")
        self.master_layout.addWidget(self.title_bar)
        self.btn_minimize = self.title_bar.btn_minimize
        self.btn_maximize = self.title_bar.btn_maximize
        self.btn_close = self.title_bar.btn_close

        # 2. Main Content Widget (Calculator + Overlays)
        self.content_widget = QWidget()
        self.master_layout.addWidget(self.content_widget, stretch=1)

        # Content Horizontal Layout: Main Area (left) + History Drawer (right)
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Center Calculator Container
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # ─── WINDOWS CALC HEADER BAR ─────────────────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(2)

        self.hamburger_btn = QPushButton()
        self.hamburger_btn.setObjectName("HamburgerBtn")
        self.hamburger_btn.setFixedSize(36, 32)
        self.hamburger_btn.setToolTip("Open Navigation Menu")
        self.hamburger_btn.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.hamburger_btn)

        self.mode_title = QLabel("Standard")
        self.mode_title.setObjectName("ModeTitle")
        header_layout.addWidget(self.mode_title)

        header_layout.addStretch()

        # Always-on-top button
        self.pin_btn = QPushButton("◳")
        self.pin_btn.setProperty("class", "iconHeaderBtn")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(self.config.get("always_on_top", False))
        self.pin_btn.setToolTip("Keep on top")
        self.pin_btn.clicked.connect(self._toggle_always_on_top)
        header_layout.addWidget(self.pin_btn)

        # History button
        self.history_btn = QPushButton("◷")
        self.history_btn.setProperty("class", "iconHeaderBtn")
        self.history_btn.setToolTip("History (Ctrl+H)")
        self.history_btn.clicked.connect(self._toggle_history_drawer)
        header_layout.addWidget(self.history_btn)

        center_layout.addWidget(header_frame)

        # ─── STACKED VIEWS (CALCULATOR, CONVERTER, PLACEHOLDERS) ────
        self.stack = QStackedWidget()

        # Page 0: Calculator Keypad & Display
        self.calc_page = QWidget()
        calc_page_layout = QVBoxLayout(self.calc_page)
        calc_page_layout.setContentsMargins(0, 0, 0, 0)
        calc_page_layout.setSpacing(0)

        # 3-Tier Display with Blinking Writing Cursor
        self.display = DualTierDisplay(self)
        self.display.expressionClicked.connect(self.state.restore_expression)
        self.display.userTyped.connect(self._on_user_typed_in_display)
        self.display.operatorClicked.connect(self.state.input_operator)
        self.display.equalsClicked.connect(self.state.evaluate)
        self.display.clearClicked.connect(self.state.clear_all)
        self.display.clearEntryClicked.connect(self.state.clear_entry)
        calc_page_layout.addWidget(self.display)

        # Memory Bar (MC, MR, M+, M-, MS)
        self.mem_bar = QFrame()
        self.mem_bar.setObjectName("MemoryBar")
        mem_layout = QHBoxLayout(self.mem_bar)
        mem_layout.setContentsMargins(8, 0, 8, 4)
        mem_layout.setSpacing(2)

        mem_buttons = [
            ("MC", self._memory_clear),
            ("MR", self._memory_recall),
            ("M+", self._memory_add),
            ("M-", self._memory_sub),
            ("MS", self._memory_store)
        ]
        self.mem_widgets = {}
        for label, handler in mem_buttons:
            btn = QPushButton(label)
            btn.setProperty("class", "memBtn")
            btn.clicked.connect(handler)
            mem_layout.addWidget(btn)
            self.mem_widgets[label] = btn

        self._update_memory_buttons()
        calc_page_layout.addWidget(self.mem_bar)

        # Keypad (Windows 4x6 Layout with 2px tight spacing)
        self.keypad = KeypadWidget(mode="Standard", parent=self)
        self.keypad.digitClicked.connect(self.state.input_digit)
        self.keypad.operatorClicked.connect(self.state.input_operator)
        self.keypad.unaryFunctionClicked.connect(self.state.input_unary_operation)
        self.keypad.equalsClicked.connect(self.state.evaluate)
        self.keypad.clearClicked.connect(self.state.clear_all)
        self.keypad.clearEntryClicked.connect(self.state.clear_entry)
        self.keypad.backspaceClicked.connect(self.state.backspace)
        self.keypad.negateClicked.connect(self.state.negate)
        self.keypad.percentageClicked.connect(self.state.input_percentage)
        self.keypad.parenthesisClicked.connect(self.state.input_digit)
        self.keypad.angleModeToggled.connect(self._on_angle_mode_toggled)
        self.keypad.feToggled.connect(self._on_fe_toggled)

        calc_page_layout.addWidget(self.keypad, stretch=1)
        self.stack.addWidget(self.calc_page)

        # Page 1: Unit & Currency Converter View
        self.converter_page = ConverterView(category=self.config.get("converter_category", "Length"), parent=self)
        self.stack.addWidget(self.converter_page)

        # Page 2: Date Calculation View
        self.date_calc_page = DateCalcView(parent=self)
        self.stack.addWidget(self.date_calc_page)

        # Page 3: Graphing Mode View
        self.graphing_page = GraphingView(parent=self)
        self.stack.addWidget(self.graphing_page)

        center_layout.addWidget(self.stack, stretch=1)
        self.content_layout.addWidget(self.center_container, stretch=1)

        # ─── RIGHT: HISTORY DRAWER (COLLAPSIBLE SIDE PANEL) ──────────
        self.history_drawer = HistoryDrawer(self.db, self)
        self.history_drawer.expressionSelected.connect(self._on_history_expression_selected)
        self.history_drawer.closeRequested.connect(self._toggle_history_drawer)
        self.history_drawer.setVisible(self.config.get("history_open", False))
        self.content_layout.addWidget(self.history_drawer)

        # ─── FLYOUT OVERLAY: NAVIGATION SIDEBAR & SCRIM ──────────────
        # Scrim / Backdrop covers the calculator when sidebar opens; clicking it closes the sidebar
        self.scrim = QWidget(self.content_widget)
        self.scrim.setStyleSheet("background-color: rgba(0, 0, 0, 0.45);")
        self.scrim.setVisible(False)
        self.scrim.mousePressEvent = lambda e: self._toggle_sidebar()

        # Sidebar Drawer overlays on top of the UI without pushing or resizing buttons!
        self.sidebar = NavigationSidebar(current_mode=self.config.get("mode", "Standard"), parent=self.content_widget)
        self.sidebar.modeSelected.connect(self._on_sidebar_mode_selected)
        self.sidebar.themeSettingsRequested.connect(self._open_theme_dialog)
        self.sidebar.closeRequested.connect(self._toggle_sidebar)
        self.sidebar.setVisible(False)

    def _on_user_typed_in_display(self, text: str):
        sanitized = sanitize_leading_zeros(text, self.state.mode)
        self.state.active_token = sanitized
        self.state.is_evaluated = False
        self.state._notify()

    def _on_calculator_state_changed(self, is_evaluated: bool, expression_trail: str, active_token: str, live_preview: str):
        if is_evaluated:
            self.display.set_evaluated_state(expression_trail, active_token)
            if self.history_drawer.isVisible():
                self.history_drawer.refresh_history()
        else:
            self.display.set_drafting_state(expression_trail, active_token, live_preview)

    def _toggle_sidebar(self):
        is_visible = not self.sidebar.isVisible()
        if is_visible:
            # Position flyout overlay over content without pushing layout
            cw = self.content_widget.width()
            ch = self.content_widget.height()
            self.scrim.setGeometry(0, 0, cw, ch)
            self.scrim.setVisible(True)
            self.scrim.raise_()

            self.sidebar.setGeometry(0, 0, min(260, int(cw * 0.85)), ch)
            self.sidebar.setVisible(True)
            self.sidebar.raise_()

            # Hide main header hamburger so only ONE hamburger button exists
            self.hamburger_btn.setVisible(False)
        else:
            self.sidebar.setVisible(False)
            self.scrim.setVisible(False)
            self.hamburger_btn.setVisible(True)

    def _on_sidebar_mode_selected(self, mode: str):
        self._toggle_sidebar()
        self._switch_mode(mode)

    def _switch_mode(self, mode: str, save_config: bool = True):
        record_breadcrumb("Navigation", f"Switched mode to '{mode}'")
        self.mode_title.setText(mode)
        self.state.mode = mode
        self.sidebar.set_current_mode(mode)

        if mode in ("Standard", "Scientific", "Programmer"):
            radix = getattr(self.keypad, "current_radix", "HEX" if mode == "Programmer" else "DEC")
            self.display.set_mode(mode, radix)
            self.state.radix = radix
            self.stack.setCurrentIndex(0)
            self.keypad.set_mode(mode)
            if mode == "Scientific":
                self.keypad.set_angle_mode_text(self.engine.angle_mode)
            self.keypad.update_theme_icons(self.theme_mgr.current_tokens.get("text_primary", "#FFFFFF"))
            self.display.setVisible(True)
            self.mem_bar.setVisible(mode != "Programmer")
            self.history_btn.setVisible(True)
        elif mode == "Date Calculation":
            self.stack.setCurrentIndex(2)
            self.display.setVisible(False)
            self.mem_bar.setVisible(False)
            self.history_btn.setVisible(False)
            if self.history_drawer.isVisible():
                self.history_drawer.setVisible(False)
        elif mode == "Graphing":
            self.stack.setCurrentIndex(3)
            self.display.setVisible(False)
            self.mem_bar.setVisible(False)
            self.history_btn.setVisible(False)
            if self.history_drawer.isVisible():
                self.history_drawer.setVisible(False)
        else:
            # 12 Unit Converters
            self.stack.setCurrentIndex(1)
            self.display.setVisible(False)
            self.mem_bar.setVisible(False)
            self.converter_page.set_category(mode)
            self.history_btn.setVisible(False)
            if self.history_drawer.isVisible():
                self.history_drawer.setVisible(False)

        if save_config:
            self.config.set("mode", mode)

        # Set minimum width per mode (for calculation modes, enforce ergonomic min width)
        calc_min_widths = {
            "Standard": 340,
            "Scientific": 430,
            "Programmer": 380,
            "Date Calculation": 360,
            "Graphing": 460,
        }
        base_min_w = calc_min_widths.get(mode, 320)
        h_open = hasattr(self, "history_drawer") and self.history_drawer.isVisible()
        h_w = self.history_drawer.width() if h_open else 0
        total_min_w = base_min_w + h_w
        self.setMinimumWidth(total_min_w)
        if self.width() < total_min_w:
            self.resize(total_min_w, self.height())

    def set_radix(self, radix: str):
        if hasattr(self, "keypad"):
            self.keypad.set_radix(radix)
        if hasattr(self, "display"):
            self.display.set_mode(self.state.mode, radix)
        self.state.radix = radix

    def _toggle_history_drawer(self):
        is_visible = not self.history_drawer.isVisible()
        calc_min_widths = {
            "Standard": 340,
            "Scientific": 430,
            "Programmer": 380,
            "Date Calculation": 360,
            "Graphing": 460,
        }
        mode_min_w = calc_min_widths.get(self.state.mode, 340)
        h_w = self.history_drawer.width()

        if is_visible:
            # Check if there is already more than enough width
            if self.width() < mode_min_w + h_w:
                delta = (mode_min_w + h_w) - self.width()
                new_x = max(0, self.x() - delta)
                new_w = self.width() + delta
                self.setGeometry(new_x, self.y(), new_w, self.height())
                self._history_auto_expanded_delta = delta
            else:
                self._history_auto_expanded_delta = 0

            self.setMinimumWidth(mode_min_w + h_w)
            self.history_drawer.setVisible(True)
            self.history_drawer.refresh_history()
        else:
            self.history_drawer.setVisible(False)
            if getattr(self, "_history_auto_expanded_delta", 0) > 0:
                delta = self._history_auto_expanded_delta
                new_x = self.x() + delta
                new_w = max(mode_min_w, self.width() - delta)
                self.setGeometry(new_x, self.y(), new_w, self.height())
                self._history_auto_expanded_delta = 0
            self.setMinimumWidth(mode_min_w)

        self.config.set("history_open", is_visible)

    def _toggle_always_on_top(self):
        is_pinned = self.pin_btn.isChecked()
        self.config.set("always_on_top", is_pinned)
        pos = self.pos()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, is_pinned)
        self.show()
        self.move(pos)

    def _on_history_expression_selected(self, expr: str):
        self.state.restore_expression(expr)

    def _open_theme_dialog(self, initial_tab: int = 0):
        if self.sidebar.isVisible():
            self._toggle_sidebar()
        dlg = ThemeDialog(self.theme_mgr, self, initial_tab=initial_tab)
        dlg.themeApplied.connect(self._on_theme_updated)
        dlg.exec()

    def _on_theme_updated(self):
        self._apply_theme()
        self.config.set("theme_id", self.theme_mgr.current_theme_id)

    def _apply_theme(self):
        blur_enabled = self.config.get("blur_enabled", True)
        qss = self.theme_mgr.generate_qss(blur_enabled=blur_enabled)
        self.setStyleSheet(qss)
        tokens = self.theme_mgr.current_tokens
        # Dynamically recolor vector icons (Backspace, Navigation modes & converters)
        text_color = tokens.get("text_primary", "#FFFFFF")
        accent_color = tokens.get("accent_primary", "#F92672")
        if hasattr(self, "hamburger_btn"):
            self.hamburger_btn.setIcon(get_themed_icon("Hamburger", text_color, size=20))
            self.hamburger_btn.setIconSize(QSize(20, 20))
        if hasattr(self, "keypad"):
            self.keypad.update_theme_icons(text_color)
        if hasattr(self, "sidebar"):
            self.sidebar.update_theme_icons(text_color, accent_color)
        if hasattr(self, "history_drawer"):
            self.history_drawer.update_theme_icons(text_color)
        if hasattr(self, "graphing_page"):
            self.graphing_page.set_theme_tokens(tokens)

        # Apply Windows 11 Mica / Acrylic blur effect
        is_dark = tokens.get("category", "dark") == "dark"
        if blur_enabled:
            apply_window_blur(int(self.winId()), dark_mode=is_dark, acrylic=False)
        else:
            remove_window_blur(int(self.winId()))

    def _on_angle_mode_toggled(self, new_mode: str):
        self.engine.set_angle_mode(new_mode)
        self.config.set("angle_mode", new_mode)

    def _on_fe_toggled(self, fe_active: bool):
        self.engine.scientific_notation = fe_active
        self.state._notify()

    # ─── MEMORY OPERATIONS ───────────────────────────────────────────
    def _memory_clear(self):
        self.state.memory_value = 0
        self._update_memory_buttons()

    def _memory_recall(self):
        if self.state.memory_value:
            val_str = self.engine.format_number(self.state.memory_value)
            self.state.input_digit(val_str)

    def _memory_add(self):
        if self.state.last_result:
            self.state.memory_value += self.state.last_result
        self._update_memory_buttons()

    def _memory_sub(self):
        if self.state.last_result:
            self.state.memory_value -= self.state.last_result
        self._update_memory_buttons()

    def _memory_store(self):
        if self.state.last_result:
            self.state.memory_value = self.state.last_result
        self._update_memory_buttons()

    def _update_memory_buttons(self):
        has_mem = bool(self.state.memory_value)
        self.mem_widgets["MC"].setEnabled(has_mem)
        self.mem_widgets["MR"].setEnabled(has_mem)

    # ─── HARDWARE NUMPAD & KEYBOARD INTERCEPTION ─────────────────────
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        # Keyboard shortcuts
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_H:
                self._toggle_history_drawer()
                return
            elif key == Qt.Key.Key_M:
                self._toggle_sidebar()
                return
            elif key == Qt.Key.Key_T:
                self._open_theme_dialog()
                return
            elif key == Qt.Key.Key_C:
                self.display.copy_to_clipboard()
                return

        # Numpad & Standard Digits
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            digit = chr(ord('0') + (key - Qt.Key.Key_0))
            self.state.input_digit(digit)
            self.keypad.flash_button(digit)
            return

        # Hex digits in Programmer Mode
        if Qt.Key.Key_A <= key <= Qt.Key.Key_F:
            if self.state.mode == "Programmer":
                char = chr(ord('A') + (key - Qt.Key.Key_A))
                self.state.input_digit(char)
                self.keypad.flash_button(char)
                return
            elif self.state.mode == "Scientific":
                char = chr(ord('a') + (key - Qt.Key.Key_A))
                if is_char_allowed(char, "Scientific"):
                    self.display.primary_display.setFocus()
                    QApplication.sendEvent(self.display.primary_display, event)
                    return
            return

        # Parentheses (Scientific and Programmer modes)
        if key == Qt.Key.Key_ParenLeft:
            if self.state.mode in ("Scientific", "Programmer"):
                self.state.input_digit("(")
                self.keypad.flash_button("(")
            return
        elif key == Qt.Key.Key_ParenRight:
            if self.state.mode in ("Scientific", "Programmer"):
                self.state.input_digit(")")
                self.keypad.flash_button(")")
            return

        # Exponentiation / XOR
        if key == Qt.Key.Key_AsciiCircum:
            if self.state.mode == "Scientific":
                self.state.input_operator("^")
            elif self.state.mode == "Programmer":
                self.state.input_operator("XOR")
            return

        # Bitwise operations in Programmer mode
        if self.state.mode == "Programmer":
            if key == Qt.Key.Key_Ampersand:
                self.state.input_operator("AND")
                return
            elif key == Qt.Key.Key_Bar:
                self.state.input_operator("OR")
                return
            elif key == Qt.Key.Key_AsciiTilde:
                self.state.input_unary_operation("NOT")
                return

        # Operators & Controls
        if key in (Qt.Key.Key_Period, Qt.Key.Key_Comma):
            if self.state.mode == "Programmer":
                return  # Decimal point is strictly forbidden in Programmer mode
            self.state.input_digit(".")
            self.keypad.flash_button(".")
        elif key == Qt.Key.Key_Plus:
            self.state.input_operator("+")
            self.keypad.flash_button("+")
        elif key == Qt.Key.Key_Minus:
            self.state.input_operator("−")
            self.keypad.flash_button("−")
        elif key == Qt.Key.Key_Asterisk:
            self.state.input_operator("×")
            self.keypad.flash_button("×")
        elif key == Qt.Key.Key_Slash:
            self.state.input_operator("÷")
            self.keypad.flash_button("÷")
        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.state.evaluate()
            self.keypad.flash_button("=")
        elif key == Qt.Key.Key_Backspace:
            self.state.backspace()
            self.keypad.flash_button("⌫")
        elif key == Qt.Key.Key_Escape:
            self.state.clear_all()
            self.keypad.flash_button("C")
        elif key == Qt.Key.Key_Delete:
            self.state.clear_entry()
            self.keypad.flash_button("CE")
        elif key == Qt.Key.Key_Percent:
            self.state.input_percentage()
        elif self.state.mode == "Scientific" and event.text():
            char = event.text()
            if is_char_allowed(char, "Scientific"):
                self.display.primary_display.setFocus()
                QApplication.sendEvent(self.display.primary_display, event)
                return
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.config.set("window_width", self.width(), auto_save=False)
        self.config.set("window_height", self.height(), auto_save=False)
        # Update flyout overlay geometry if visible
        if hasattr(self, "sidebar") and self.sidebar.isVisible():
            cw = self.content_widget.width()
            ch = self.content_widget.height()
            self.scrim.setGeometry(0, 0, cw, ch)
            self.sidebar.setGeometry(0, 0, min(260, int(cw * 0.85)), ch)

    def closeEvent(self, event):
        record_breadcrumb("Lifecycle", "MainWindow closeEvent triggered")
        unregister_context_provider(self._get_crash_context)
        self.config.set("window_width", self.width(), auto_save=False)
        self.config.set("window_height", self.height(), auto_save=True)
        if hasattr(self, "version_worker") and self.version_worker.isRunning():
            self.version_worker.terminate()
            self.version_worker.wait()
        if hasattr(self, "_native_event_filter") and self._native_event_filter:
            app = QApplication.instance()
            if app:
                app.removeNativeEventFilter(self._native_event_filter)
            self._native_event_filter = None
        super().closeEvent(event)

    def _get_crash_context(self) -> dict:
        """Captures real-time calculator context and inputs for crash reports."""
        ctx = {
            "mode": getattr(self.state, "mode", "Unknown"),
            "active_token": getattr(self.state, "active_token", "N/A"),
            "expression_trail": getattr(self.state, "expression_trail", "N/A"),
            "live_preview": getattr(self.state, "pinned_expression", "N/A"),
            "is_evaluated": getattr(self.state, "is_evaluated", False),
            "has_error": getattr(self.state, "has_error", False),
            "memory": str(getattr(self.state, "memory_value", "0")),
            "angle_mode": getattr(self.engine, "angle_mode", "DEG"),
            "theme": getattr(self.theme_mgr, "current_theme_id", "default"),
            "window_size": f"{self.width()}x{self.height()}",
            "is_maximized": self.isMaximized(),
            "history_open": self.history_drawer.isVisible() if hasattr(self, "history_drawer") else False,
            "sidebar_open": self.sidebar.isVisible() if hasattr(self, "sidebar") else False,
        }

        # Rich Mode-Specific Details
        mode = ctx["mode"]
        if mode == "Programmer" and hasattr(self, "keypad"):
            ctx["programmer_radix"] = getattr(self.keypad, "current_radix", "DEC")
            ctx["programmer_word_size"] = getattr(self.keypad, "current_word_size", "QWORD")
        elif mode == "Graphing" and hasattr(self, "graphing_page"):
            gp = self.graphing_page
            if hasattr(gp, "canvas"):
                ctx["graph_bounds"] = f"X[{gp.canvas.x_min:.4g}, {gp.canvas.x_max:.4g}], Y[{gp.canvas.y_min:.4g}, {gp.canvas.y_max:.4g}]"
                ctx["graph_functions"] = [f.raw_expression for f in gp.canvas.functions if f.raw_expression]
        elif mode == "Date Calculation" and hasattr(self, "date_calc_page"):
            dp = self.date_calc_page
            ctx["date_submode"] = dp.mode_combo.currentText() if hasattr(dp, "mode_combo") else "Unknown"
            if hasattr(dp, "from_date_edit"):
                ctx["date_from"] = dp.from_date_edit.date().toString("dd-MM-yyyy")
            if hasattr(dp, "to_date_edit"):
                ctx["date_to"] = dp.to_date_edit.date().toString("dd-MM-yyyy")
        elif hasattr(self, "converter_page"):
            cp = self.converter_page
            ctx["converter_category"] = cp.category
            if hasattr(cp, "combo_from") and hasattr(cp, "combo_to"):
                ctx["converter_from_unit"] = cp.combo_from.currentText()
                ctx["converter_to_unit"] = cp.combo_to.currentText()
            if hasattr(cp, "input_from") and hasattr(cp, "input_to"):
                ctx["converter_input"] = cp.input_from.text()
                ctx["converter_output"] = cp.input_to.text()

        return ctx

    def _start_version_check(self):
        if not is_connected_to_internet(timeout=1.5):
            return
        self.version_worker = VersionCheckWorker(self)
        self.version_worker.checkCompleted.connect(self._on_version_check_result)
        self.version_worker.start()

    def _on_version_check_result(self, update_available: bool, release_info: dict):
        if update_available and not release_info.get("is_offline"):
            dlg = UpdatePromptDialog(release_info, self)
            dlg.exec()

    # ─── WIN32 NATIVE FRAMELESS & AERO SNAP INTEGRATION ─────────────
    _RESIZE_MARGIN = 4
    _CORNER_MARGIN = 8

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "_win32_setup_done"):
            self._win32_setup_done = True
            apply_native_window_frame(self)
            self._apply_theme()

    def _toggle_maximize(self):
        self.title_bar._toggle_maximize()

    def _set_btn_maximize_hover(self, hover: bool):
        self.title_bar.set_btn_maximize_hover(hover)
        if hover:
            QTimer.singleShot(50, self._check_maximize_hover_liveness)

    def _set_btn_maximize_pressed(self, pressed: bool):
        self.title_bar.set_btn_maximize_pressed(pressed)

    def _check_maximize_hover_liveness(self):
        if not getattr(self, "_btn_maximize_hovered", False):
            return
        p_max = self.btn_maximize.mapFromGlobal(QCursor.pos())
        if not self.btn_maximize.rect().contains(p_max):
            self._btn_maximize_hovered = False
            self._set_btn_maximize_hover(False)
            self._set_btn_maximize_pressed(False)
        else:
            QTimer.singleShot(50, self._check_maximize_hover_liveness)

    def _handle_nchittest(self, global_x: int, global_y: int):
        pt = self.mapFromGlobal(QPoint(global_x, global_y))
        lx = pt.x()
        ly = pt.y()
        w = self.width()
        h = self.height()
        B = self._RESIZE_MARGIN
        C = self._CORNER_MARGIN

        # 1. Edge & Corner resizing (only when not maximized)
        if not self.isMaximized():
            if (ly < C) and (lx < C):
                return HTTOPLEFT
            if (ly < C) and (lx >= w - C):
                return HTTOPRIGHT
            if (ly >= h - C) and (lx < C):
                return HTBOTTOMLEFT
            if (ly >= h - C) and (lx >= w - C):
                return HTBOTTOMRIGHT

            if ly < B:
                if hasattr(self, "btn_maximize") and self.btn_maximize.isVisible():
                    p_max = self.btn_maximize.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_maximize.rect().contains(p_max):
                        return HTMAXBUTTON
                if hasattr(self, "btn_close") and self.btn_close.isVisible():
                    p_close = self.btn_close.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_close.rect().contains(p_close):
                        return HTCLIENT
                if hasattr(self, "btn_minimize") and self.btn_minimize.isVisible():
                    p_min = self.btn_minimize.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_minimize.rect().contains(p_min):
                        return HTCLIENT
                return HTTOP
            if ly >= h - B:
                return HTBOTTOM
            if lx < B:
                return HTLEFT
            if lx >= w - B:
                return HTRIGHT

        # 2. Title bar hit-testing (for Aero Snap, Snap Layouts flyout, and controls)
        if hasattr(self, "title_bar") and self.title_bar.isVisible():
            tb_rect = self.title_bar.rect()
            tb_pt = self.title_bar.mapFromGlobal(QPoint(global_x, global_y))
            if tb_rect.contains(tb_pt):
                # Maximize button -> HTMAXBUTTON enables Windows 11 Snap Layouts flyout on hover
                if hasattr(self, "btn_maximize") and self.btn_maximize.isVisible():
                    p_max = self.btn_maximize.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_maximize.rect().contains(p_max):
                        return HTMAXBUTTON

                # Minimize and Close buttons -> HTCLIENT so Qt processes hover highlights & clicks
                if hasattr(self, "btn_minimize") and self.btn_minimize.isVisible():
                    p_min = self.btn_minimize.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_minimize.rect().contains(p_min):
                        return HTCLIENT

                if hasattr(self, "btn_close") and self.btn_close.isVisible():
                    p_close = self.btn_close.mapFromGlobal(QPoint(global_x, global_y))
                    if self.btn_close.rect().contains(p_close):
                        return HTCLIENT

                # Other title bar areas -> HTCAPTION for native Aero Snap & double click maximize
                return HTCAPTION

        return HTCLIENT
