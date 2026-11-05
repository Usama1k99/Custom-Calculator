"""
Windows Calculator-Style Keypad Grid.
Replicates Windows Calculator's exact Standard (4x6), Scientific (5x7),
and Programmer layouts with 2px tight spacing.
Includes Trigonometry and Function popovers, 2nd key toggles, and themed SVG icons.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QFrame, QLabel, QSizePolicy, QGraphicsDropShadowEffect, QLayout
)
from src.ui.mode_icons import get_themed_icon


class SciDropdownButton(QPushButton):
    """Compound dropdown button with vector mode icon, clean typography, and chevron."""

    def __init__(self, mode_icon_name: str, label_text: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "sciDropdownBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_icon_name = mode_icon_name
        self.label_text = label_text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedSize(18, 18)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(label_text, self)
        self.lbl_text.setStyleSheet("font-size: 13px; font-weight: 500; background: transparent;")
        self.lbl_text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_text)

        self.lbl_chevron = QLabel(self)
        self.lbl_chevron.setFixedSize(12, 12)
        self.lbl_chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_chevron)

        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(32)

        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        self.setMinimumWidth(text_w + 18 + 12 + 28)

    def sizeHint(self) -> QSize:
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        return QSize(text_w + 18 + 12 + 28, 32)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def update_icons(self, text_color: str):
        self.lbl_icon.setPixmap(get_themed_icon(self.mode_icon_name, text_color, size=18).pixmap(18, 18))
        self.lbl_chevron.setPixmap(get_themed_icon("ChevronDown", text_color, size=12).pixmap(12, 12))
        self.lbl_text.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {text_color}; background: transparent;")
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        self.setMinimumWidth(text_w + 18 + 12 + 28)



class KeypadWidget(QWidget):
    # Signals
    digitClicked = pyqtSignal(str)
    operatorClicked = pyqtSignal(str)
    unaryFunctionClicked = pyqtSignal(str)
    equalsClicked = pyqtSignal()
    clearClicked = pyqtSignal()
    clearEntryClicked = pyqtSignal()
    backspaceClicked = pyqtSignal()
    negateClicked = pyqtSignal()
    percentageClicked = pyqtSignal()
    parenthesisClicked = pyqtSignal(str)
    angleModeToggled = pyqtSignal(str)
    feToggled = pyqtSignal(bool)

    def __init__(self, mode: str = "Standard", parent=None):
        super().__init__(parent)
        self.setObjectName("KeypadFrame")
        self.mode = mode
        self.current_radix = "HEX"
        self.button_map = {}
        self._current_text_color = "#FFFFFF"
        self._is_2nd_active = False
        self._is_trig_2nd = False
        self._is_trig_hyp = False
        self._angle_mode = "DEG"
        self._fe_active = False
        self._init_ui()

    def set_mode(self, mode: str):
        if self.mode != mode:
            self.mode = mode
            self._is_2nd_active = False
            self._init_ui()

    def set_angle_mode_text(self, mode_str: str):
        self._angle_mode = mode_str
        if hasattr(self, "btn_angle_mode") and self.btn_angle_mode:
            self.btn_angle_mode.setText(mode_str)

    def update_theme_icons(self, text_color: str):
        self._current_text_color = text_color
        btn = self.button_map.get("⌫")
        if btn:
            try:
                btn.setText("")
                btn.setIcon(get_themed_icon("Backspace", text_color, size=20))
            except RuntimeError:
                pass
        if self.mode == "Scientific":
            if hasattr(self, "btn_trig") and isinstance(self.btn_trig, SciDropdownButton):
                try:
                    self.btn_trig.update_icons(text_color)
                except RuntimeError:
                    pass
            if hasattr(self, "btn_func") and isinstance(self.btn_func, SciDropdownButton):
                try:
                    self.btn_func.update_icons(text_color)
                except RuntimeError:
                    pass

    def _init_ui(self):
        if self.layout() is not None:
            QWidget().setLayout(self.layout())

        self.button_map.clear()
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(4, 2, 4, 4)
        master_layout.setSpacing(2)

        if self.mode == "Standard":
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(2)
            self._build_windows_standard_grid(grid)
            master_layout.addLayout(grid, stretch=1)

        elif self.mode == "Scientific":
            self._build_windows_scientific_layout(master_layout)

        elif self.mode == "Programmer":
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(2)
            self._build_programmer_grid(grid)
            master_layout.addLayout(grid, stretch=1)

    # ─────────────────────────────────────────────────────────────────────────
    # STANDARD MODE (4x6)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_windows_standard_grid(self, grid: QGridLayout):
        layout_map = [
            [("%", "fnKey", self.percentageClicked),
             ("CE", "fnKey", self.clearEntryClicked),
             ("C", "fnKey", self.clearClicked),
             ("⌫", "fnKey", self.backspaceClicked)],
            [("1/x", "fnKey", lambda: self.unaryFunctionClicked.emit("recip")),
             ("x²", "fnKey", lambda: self.unaryFunctionClicked.emit("sqr")),
             ("²√x", "fnKey", lambda: self.unaryFunctionClicked.emit("sqrt")),
             ("÷", "opKey", lambda: self.operatorClicked.emit("÷"))],
            [("7", "numKey", lambda: self.digitClicked.emit("7")),
             ("8", "numKey", lambda: self.digitClicked.emit("8")),
             ("9", "numKey", lambda: self.digitClicked.emit("9")),
             ("×", "opKey", lambda: self.operatorClicked.emit("×"))],
            [("4", "numKey", lambda: self.digitClicked.emit("4")),
             ("5", "numKey", lambda: self.digitClicked.emit("5")),
             ("6", "numKey", lambda: self.digitClicked.emit("6")),
             ("−", "opKey", lambda: self.operatorClicked.emit("−"))],
            [("1", "numKey", lambda: self.digitClicked.emit("1")),
             ("2", "numKey", lambda: self.digitClicked.emit("2")),
             ("3", "numKey", lambda: self.digitClicked.emit("3")),
             ("+", "opKey", lambda: self.operatorClicked.emit("+"))],
            [("+/-", "numKey", self.negateClicked),
             ("0", "numKey", lambda: self.digitClicked.emit("0")),
             (".", "numKey", lambda: self.digitClicked.emit(".")),
             ("=", "equalsKey", self.equalsClicked)]
        ]
        self._populate_grid(grid, layout_map)
    # ─────────────────────────────────────────────────────────────────────────
    # SCIENTIFIC MODE (Ribbon + Flyouts + 5x7 Grid)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_windows_scientific_layout(self, parent_layout: QVBoxLayout):
        # 1. Top Ribbon: DEG and F-E
        ribbon_frame = QFrame()
        ribbon_frame.setObjectName("ScientificHeaderBar")
        ribbon_layout = QHBoxLayout(ribbon_frame)
        ribbon_layout.setContentsMargins(0, 0, 0, 2)
        ribbon_layout.setSpacing(6)

        self.btn_angle_mode = QPushButton(self._angle_mode)
        self.btn_angle_mode.setProperty("class", "sciRibbonBtn")
        self.btn_angle_mode.setToolTip("Angle mode: DEG / RAD / GRAD")
        self.btn_angle_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_angle_mode.clicked.connect(self._on_angle_mode_clicked)
        ribbon_layout.addWidget(self.btn_angle_mode)

        self.btn_fe = QPushButton("F-E")
        self.btn_fe.setProperty("class", "sciRibbonBtn")
        self.btn_fe.setCheckable(True)
        self.btn_fe.setChecked(self._fe_active)
        self.btn_fe.setToolTip("Toggle scientific exponential notation")
        self.btn_fe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fe.clicked.connect(self._on_fe_clicked)
        ribbon_layout.addWidget(self.btn_fe)

        ribbon_layout.addStretch()
        parent_layout.addWidget(ribbon_frame)

        # 2. Function Dropdowns Row: Trigonometry and Function
        func_row = QHBoxLayout()
        func_row.setContentsMargins(0, 0, 0, 2)
        func_row.setSpacing(6)

        self.btn_trig = SciDropdownButton("Trigonometry", "Trigonometry", self)
        self.btn_trig.clicked.connect(self._toggle_trig_flyout)
        self.btn_trig.update_icons(self._current_text_color)
        func_row.addWidget(self.btn_trig)

        self.btn_func = SciDropdownButton("Function", "Function", self)
        self.btn_func.clicked.connect(self._toggle_func_flyout)
        self.btn_func.update_icons(self._current_text_color)
        func_row.addWidget(self.btn_func)

        func_row.addStretch()
        parent_layout.addLayout(func_row)

        # 3. Trigonometry Popover Drawer (4x2 grid) - Floating overlay over keypad grid
        self.trig_popover = QFrame(self)
        self.trig_popover.setObjectName("SciFlyoutPanel")
        self.trig_popover.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.trig_popover.setAutoFillBackground(True)
        self.trig_popover.setVisible(False)

        trig_shadow = QGraphicsDropShadowEffect(self.trig_popover)
        trig_shadow.setBlurRadius(20)
        trig_shadow.setOffset(0, 6)
        trig_shadow.setColor(QColor(0, 0, 0, 160))
        self.trig_popover.setGraphicsEffect(trig_shadow)

        trig_grid = QGridLayout(self.trig_popover)
        trig_grid.setContentsMargins(4, 4, 4, 4)
        trig_grid.setSpacing(3)
        for col in range(4):
            trig_grid.setColumnStretch(col, 1)
        for row in range(2):
            trig_grid.setRowStretch(row, 1)

        self.trig_2nd_btn = QPushButton("2ⁿᵈ")
        self.trig_2nd_btn.setProperty("class", "sciFlyoutKey")
        self.trig_2nd_btn.setCheckable(True)
        self.trig_2nd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trig_2nd_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.trig_2nd_btn.clicked.connect(self._toggle_trig_2nd)
        trig_grid.addWidget(self.trig_2nd_btn, 0, 0)

        self.trig_hyp_btn = QPushButton("hyp")
        self.trig_hyp_btn.setProperty("class", "sciFlyoutKey")
        self.trig_hyp_btn.setCheckable(True)
        self.trig_hyp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trig_hyp_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.trig_hyp_btn.clicked.connect(self._toggle_trig_hyp)
        trig_grid.addWidget(self.trig_hyp_btn, 1, 0)

        self.trig_buttons = {}
        trig_keys = [
            (0, 1, "sin"), (0, 2, "cos"), (0, 3, "tan"),
            (1, 1, "sec"), (1, 2, "csc"), (1, 3, "cot")
        ]
        for r, c, base_fn in trig_keys:
            btn = QPushButton(base_fn)
            btn.setProperty("class", "sciFlyoutKey")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda _, fn=base_fn: self._on_trig_key_clicked(fn))
            trig_grid.addWidget(btn, r, c)
            self.trig_buttons[base_fn] = btn

        # 4. Function Popover Drawer (3x2 grid) - Floating overlay over keypad grid
        self.func_popover = QFrame(self)
        self.func_popover.setObjectName("SciFlyoutPanel")
        self.func_popover.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.func_popover.setAutoFillBackground(True)
        self.func_popover.setVisible(False)

        func_shadow = QGraphicsDropShadowEffect(self.func_popover)
        func_shadow.setBlurRadius(20)
        func_shadow.setOffset(0, 6)
        func_shadow.setColor(QColor(0, 0, 0, 160))
        self.func_popover.setGraphicsEffect(func_shadow)

        func_grid = QGridLayout(self.func_popover)
        func_grid.setContentsMargins(4, 4, 4, 4)
        func_grid.setSpacing(3)
        for col in range(3):
            func_grid.setColumnStretch(col, 1)
        for row in range(2):
            func_grid.setRowStretch(row, 1)

        funcs = [
            (0, 0, "|x|", "abs"),
            (0, 1, "⌊x⌋", "floor"),
            (0, 2, "⌈x⌉", "ceil"),
            (1, 0, "rand", "rand"),
            (1, 1, "→dms", "dms"),
            (1, 2, "→deg", "deg")
        ]
        for r, c, label, action in funcs:
            btn = QPushButton(label)
            btn.setProperty("class", "sciFlyoutKey")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda _, act=action: self._on_func_key_clicked(act))
            func_grid.addWidget(btn, r, c)

        # 5. Main Scientific Keypad Grid (5x7)
        self.sci_grid = QGridLayout()
        self.sci_grid.setContentsMargins(0, 0, 0, 0)
        self.sci_grid.setSpacing(2)

        self.sci_key_map = [
            # Row 0: 2nd, pi, e, C, ⌫
            [("2ⁿᵈ", "fnKey", self._toggle_scientific_2nd),
             ("π", "fnKey", lambda: self.digitClicked.emit("π")),
             ("e", "fnKey", lambda: self.digitClicked.emit("e")),
             ("C", "fnKey", self.clearClicked),
             ("⌫", "fnKey", self.backspaceClicked)],
            # Row 1: x², 1/x, |x|, exp, mod
            [("x²", "fnKey", lambda: self._on_sci_2nd_variant("sqr", "cube")),
             ("1/x", "fnKey", lambda: self.unaryFunctionClicked.emit("recip")),
             ("|x|", "fnKey", lambda: self.unaryFunctionClicked.emit("abs")),
             ("exp", "fnKey", lambda: self.operatorClicked.emit("e+")),
             ("mod", "opKey", lambda: self.operatorClicked.emit("mod"))],
            # Row 2: ²√x, (, ), n!, ÷
            [("²√x", "fnKey", lambda: self._on_sci_2nd_variant("sqrt", "cbrt")),
             ("(", "fnKey", lambda: self.parenthesisClicked.emit("(")),
             (")", "fnKey", lambda: self.parenthesisClicked.emit(")")),
             ("n!", "fnKey", lambda: self.unaryFunctionClicked.emit("fact")),
             ("÷", "opKey", lambda: self.operatorClicked.emit("÷"))],
            # Row 3: xʸ, 7, 8, 9, ×
            [("xʸ", "fnKey", lambda: self.operatorClicked.emit("^")),
             ("7", "numKey", lambda: self.digitClicked.emit("7")),
             ("8", "numKey", lambda: self.digitClicked.emit("8")),
             ("9", "numKey", lambda: self.digitClicked.emit("9")),
             ("×", "opKey", lambda: self.operatorClicked.emit("×"))],
            # Row 4: 10ˣ, 4, 5, 6, −
            [("10ˣ", "fnKey", lambda: self._on_sci_2nd_variant("pow10", "pow2")),
             ("4", "numKey", lambda: self.digitClicked.emit("4")),
             ("5", "numKey", lambda: self.digitClicked.emit("5")),
             ("6", "numKey", lambda: self.digitClicked.emit("6")),
             ("−", "opKey", lambda: self.operatorClicked.emit("−"))],
            # Row 5: log, 1, 2, 3, +
            [("log", "fnKey", lambda: self._on_sci_2nd_variant("log", "log2")),
             ("1", "numKey", lambda: self.digitClicked.emit("1")),
             ("2", "numKey", lambda: self.digitClicked.emit("2")),
             ("3", "numKey", lambda: self.digitClicked.emit("3")),
             ("+", "opKey", lambda: self.operatorClicked.emit("+"))],
            # Row 6: ln, +/-, 0, ., =
            [("ln", "fnKey", lambda: self._on_sci_2nd_variant("ln", "exp_e")),
             ("+/-", "numKey", self.negateClicked),
             ("0", "numKey", lambda: self.digitClicked.emit("0")),
             (".", "numKey", lambda: self.digitClicked.emit(".")),
             ("=", "equalsKey", self.equalsClicked)]
        ]

        self._populate_grid(self.sci_grid, self.sci_key_map)
        parent_layout.addLayout(self.sci_grid, stretch=1)

    def _on_angle_mode_clicked(self):
        # Cycles DEG -> RAD -> GRAD -> DEG
        next_map = {"DEG": "RAD", "RAD": "GRAD", "GRAD": "DEG"}
        new_mode = next_map.get(self._angle_mode, "DEG")
        self._angle_mode = new_mode
        self.btn_angle_mode.setText(new_mode)
        self.angleModeToggled.emit(new_mode)

    def _on_fe_clicked(self):
        self._fe_active = self.btn_fe.isChecked()
        self.feToggled.emit(self._fe_active)

    def _toggle_trig_flyout(self):
        is_open = self.btn_trig.isChecked()
        if is_open:
            if hasattr(self, "btn_func"):
                self.btn_func.setChecked(False)
                self.func_popover.setVisible(False)
            btn_pos = self.btn_trig.pos()
            w = 232
            h = 66
            x = max(4, min(btn_pos.x(), self.width() - w - 4))
            self.trig_popover.setGeometry(x, btn_pos.y() + self.btn_trig.height() + 4, w, h)
            self.trig_popover.raise_()
            self.trig_popover.setVisible(True)
        else:
            self.trig_popover.setVisible(False)

    def _toggle_func_flyout(self):
        is_open = self.btn_func.isChecked()
        if is_open:
            if hasattr(self, "btn_trig"):
                self.btn_trig.setChecked(False)
                self.trig_popover.setVisible(False)
            btn_pos = self.btn_func.pos()
            w = 176
            h = 66
            x = max(4, min(btn_pos.x(), self.width() - w - 4))
            self.func_popover.setGeometry(x, btn_pos.y() + self.btn_func.height() + 4, w, h)
            self.func_popover.raise_()
            self.func_popover.setVisible(True)
        else:
            self.func_popover.setVisible(False)

    def _toggle_trig_2nd(self):
        self._is_trig_2nd = self.trig_2nd_btn.isChecked()
        self._update_trig_button_labels()

    def _toggle_trig_hyp(self):
        self._is_trig_hyp = self.trig_hyp_btn.isChecked()
        self._update_trig_button_labels()

    def _update_trig_button_labels(self):
        for base_fn, btn in self.trig_buttons.items():
            fn_label = self._resolve_trig_name(base_fn)
            btn.setText(fn_label)

    def _resolve_trig_name(self, base_fn: str) -> str:
        # Standard: sin, cos, tan, sec, csc, cot
        # 2nd: sin⁻¹, cos⁻¹, tan⁻¹, sec⁻¹, csc⁻¹, cot⁻¹
        # hyp: sinh, cosh, tanh, sech, csch, coth
        # 2nd + hyp: sinh⁻¹, cosh⁻¹, tanh⁻¹, sech⁻¹, csch⁻¹, coth⁻¹
        is_2nd = self._is_trig_2nd
        is_hyp = self._is_trig_hyp

        name = base_fn
        if is_hyp:
            name = f"{base_fn}h"
        if is_2nd:
            name = f"{name}⁻¹"
        return name

    def _on_trig_key_clicked(self, base_fn: str):
        is_2nd = self._is_trig_2nd
        is_hyp = self._is_trig_hyp

        # Resolve function ID for engine
        fn_id = base_fn
        if is_2nd and is_hyp:
            fn_id = f"a{base_fn}h"
        elif is_2nd:
            fn_id = f"a{base_fn}"
        elif is_hyp:
            fn_id = f"{base_fn}h"

        self.unaryFunctionClicked.emit(fn_id)
        # Close popover after execution
        self.btn_trig.setChecked(False)
        self.trig_popover.setVisible(False)

    def _on_func_key_clicked(self, action: str):
        self.unaryFunctionClicked.emit(action)
        self.btn_func.setChecked(False)
        self.func_popover.setVisible(False)

    def _toggle_scientific_2nd(self):
        self._is_2nd_active = not self._is_2nd_active
        btn_2nd = self.button_map.get("2ⁿᵈ")
        if btn_2nd:
            btn_2nd.setChecked(self._is_2nd_active)

        # Update labels of keys that change with 2nd
        swaps = {
            "x²": "x³" if self._is_2nd_active else "x²",
            "²√x": "³√x" if self._is_2nd_active else "²√x",
            "10ˣ": "2ˣ" if self._is_2nd_active else "10ˣ",
            "log": "log₂" if self._is_2nd_active else "log",
            "ln": "eˣ" if self._is_2nd_active else "ln"
        }
        for orig, current in swaps.items():
            btn = self.button_map.get(orig)
            if btn:
                btn.setText(current)

    def _on_sci_2nd_variant(self, primary_fn: str, secondary_fn: str):
        fn = secondary_fn if self._is_2nd_active else primary_fn
        self.unaryFunctionClicked.emit(fn)

    # ─────────────────────────────────────────────────────────────────────────
    # PROGRAMMER MODE
    # ─────────────────────────────────────────────────────────────────────────
    def _build_programmer_grid(self, grid: QGridLayout):
        layout_map = [
            [("Lsh", "fnKey", lambda: self.operatorClicked.emit("<<")),
             ("Rsh", "fnKey", lambda: self.operatorClicked.emit(">>")),
             ("CE", "fnKey", self.clearClicked),
             ("⌫", "fnKey", self.backspaceClicked)],
            [("AND", "fnKey", lambda: self.operatorClicked.emit("AND")),
             ("OR", "fnKey", lambda: self.operatorClicked.emit("OR")),
             ("XOR", "fnKey", lambda: self.operatorClicked.emit("XOR")),
             ("NOT", "fnKey", lambda: self.unaryFunctionClicked.emit("NOT"))],
            [("A", "fnKey", lambda: self.digitClicked.emit("A")),
             ("B", "fnKey", lambda: self.digitClicked.emit("B")),
             ("7", "numKey", lambda: self.digitClicked.emit("7")),
             ("8", "numKey", lambda: self.digitClicked.emit("8")),
             ("9", "numKey", lambda: self.digitClicked.emit("9")),
             ("÷", "opKey", lambda: self.operatorClicked.emit("÷"))],
            [("C", "fnKey", lambda: self.digitClicked.emit("C")),
             ("D", "fnKey", lambda: self.digitClicked.emit("D")),
             ("4", "numKey", lambda: self.digitClicked.emit("4")),
             ("5", "numKey", lambda: self.digitClicked.emit("5")),
             ("6", "numKey", lambda: self.digitClicked.emit("6")),
             ("×", "opKey", lambda: self.operatorClicked.emit("×"))],
            [("E", "fnKey", lambda: self.digitClicked.emit("E")),
             ("F", "fnKey", lambda: self.digitClicked.emit("F")),
             ("1", "numKey", lambda: self.digitClicked.emit("1")),
             ("2", "numKey", lambda: self.digitClicked.emit("2")),
             ("3", "numKey", lambda: self.digitClicked.emit("3")),
             ("−", "opKey", lambda: self.operatorClicked.emit("−"))],
            [("(", "fnKey", lambda: self.parenthesisClicked.emit("(")),
             (")", "fnKey", lambda: self.parenthesisClicked.emit(")")),
             ("+/-", "numKey", self.negateClicked),
             ("0", "numKey", lambda: self.digitClicked.emit("0")),
             ("+", "opKey", lambda: self.operatorClicked.emit("+")),
             ("=", "equalsKey", self.equalsClicked)]
        ]
        self._populate_grid(grid, layout_map)
        self._update_programmer_button_states()

    def set_radix(self, radix: str):
        self.current_radix = radix.upper()
        self._update_programmer_button_states()

    def _update_programmer_button_states(self):
        if self.mode != "Programmer":
            return
        rad = self.current_radix.upper()
        hex_digits = ("A", "B", "C", "D", "E", "F")
        oct_disallowed = ("8", "9")

        for h in hex_digits:
            btn = self.button_map.get(h)
            if btn:
                btn.setEnabled(rad == "HEX")

        for d in range(10):
            ds = str(d)
            btn = self.button_map.get(ds)
            if not btn:
                continue
            if rad == "BIN":
                btn.setEnabled(ds in ("0", "1"))
            elif rad == "OCT":
                btn.setEnabled(ds not in oct_disallowed)
            else:
                btn.setEnabled(True)
    # ─────────────────────────────────────────────────────────────────────────
    # POPULATION & FLASH EFFECT
    # ─────────────────────────────────────────────────────────────────────────
    def _populate_grid(self, grid: QGridLayout, layout_map: list):
        for r, row in enumerate(layout_map):
            for c, item in enumerate(row):
                label, style_class, handler = item
                btn = QPushButton(label)
                if label == "⌫":
                    btn.setText("")
                    btn.setIcon(get_themed_icon("Backspace", self._current_text_color, size=20))
                    btn.setIconSize(QSize(20, 20))
                btn.setProperty("class", f"calcKey {style_class}")
                btn.setObjectName(f"Key_{label}")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setSizePolicy(
                    btn.sizePolicy().Policy.Expanding,
                    btn.sizePolicy().Policy.Expanding
                )
                if handler:
                    if callable(handler):
                        btn.clicked.connect(handler)

                grid.addWidget(btn, r, c)
                self.button_map[label] = btn

    def flash_button(self, label: str):
        key_alias = {
            "/": "÷",
            "*": "×",
            "-": "−",
            "+": "+",
            "Enter": "=",
            "Return": "=",
            "=": "=",
            "Backspace": "⌫"
        }
        resolved = key_alias.get(label, label)
        btn = self.button_map.get(resolved)
        if btn:
            btn.setDown(True)
            QTimer.singleShot(80, lambda b=btn: b.setDown(False))

    def mousePressEvent(self, event):
        if hasattr(self, "trig_popover") and self.trig_popover.isVisible():
            if not self.trig_popover.geometry().contains(event.pos()) and hasattr(self, "btn_trig") and not self.btn_trig.geometry().contains(event.pos()):
                self.btn_trig.setChecked(False)
                self.trig_popover.setVisible(False)
        if hasattr(self, "func_popover") and self.func_popover.isVisible():
            if not self.func_popover.geometry().contains(event.pos()) and hasattr(self, "btn_func") and not self.btn_func.geometry().contains(event.pos()):
                self.btn_func.setChecked(False)
                self.func_popover.setVisible(False)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "btn_trig") and hasattr(self, "trig_popover") and self.trig_popover.isVisible():
            btn_pos = self.btn_trig.pos()
            w = 232
            x = max(4, min(btn_pos.x(), self.width() - w - 4))
            self.trig_popover.move(x, btn_pos.y() + self.btn_trig.height() + 4)
        if hasattr(self, "btn_func") and hasattr(self, "func_popover") and self.func_popover.isVisible():
            btn_pos = self.btn_func.pos()
            w = 176
            x = max(4, min(btn_pos.x(), self.width() - w - 4))
            self.func_popover.move(x, btn_pos.y() + self.btn_func.height() + 4)
