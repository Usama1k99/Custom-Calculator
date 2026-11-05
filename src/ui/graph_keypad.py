"""
Graphing Mode Function Writing Keypad.
Replicates Windows Calculator Graphing keypad:
- Compound dropdowns: Trigonometry, Inequalities, and Functions
- Keypad Grid with variables x, y, constants π, e, and mathematical powers
- Floating popovers over the button grid with auto-dismissal
- Zero emojis across all UI elements.
"""

from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QFontMetrics, QColor
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSizePolicy, QLayout, QGraphicsDropShadowEffect
)
from src.ui.mode_icons import get_themed_icon


class GraphDropdownButton(QPushButton):
    """Compound dropdown button with icon, label, and chevron arrow."""

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
        self.lbl_icon.setFixedSize(16, 16)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(label_text, self)
        self.lbl_text.setStyleSheet("font-size: 12px; font-weight: 500; background: transparent;")
        self.lbl_text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_text)

        self.lbl_chevron = QLabel(self)
        self.lbl_chevron.setFixedSize(10, 10)
        self.lbl_chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_chevron)

        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(30)

        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        self.setMinimumWidth(text_w + 16 + 10 + 28)

    def sizeHint(self) -> QSize:
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        return QSize(text_w + 16 + 10 + 28, 30)

    def update_icons(self, text_color: str):
        self.lbl_icon.setPixmap(get_themed_icon(self.mode_icon_name, text_color, size=16).pixmap(16, 16))
        self.lbl_chevron.setPixmap(get_themed_icon("ChevronDown", text_color, size=10).pixmap(10, 10))
        self.lbl_text.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {text_color}; background: transparent;")
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.label_text)
        self.setMinimumWidth(text_w + 16 + 10 + 28)


class GraphKeypadWidget(QWidget):
    """Keypad dedicated to composing mathematical function expressions for Graphing mode."""
    insertToken = pyqtSignal(str)
    backspaceClicked = pyqtSignal()
    clearClicked = pyqtSignal()
    enterClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GraphKeypadFrame")
        self._current_text_color = "#FFFFFF"
        self._is_2nd_active = False
        self._is_trig_2nd = False
        self._is_trig_hyp = False

        self._init_ui()

    def _init_ui(self):
        parent_layout = QVBoxLayout(self)
        parent_layout.setContentsMargins(4, 4, 4, 4)
        parent_layout.setSpacing(4)

        # ─── 1. DROPDOWNS ROW: TRIGONOMETRY, INEQUALITIES, FUNCTIONS ───
        dropdown_row = QHBoxLayout()
        dropdown_row.setContentsMargins(0, 0, 0, 2)
        dropdown_row.setSpacing(4)

        self.btn_trig = GraphDropdownButton("Trigonometry", "Trigonometry", self)
        self.btn_trig.clicked.connect(self._toggle_trig_flyout)
        dropdown_row.addWidget(self.btn_trig)

        self.btn_ineq = GraphDropdownButton("Angle", "Inequalities", self)
        self.btn_ineq.clicked.connect(self._toggle_ineq_flyout)
        dropdown_row.addWidget(self.btn_ineq)

        self.btn_func = GraphDropdownButton("Function", "Function", self)
        self.btn_func.clicked.connect(self._toggle_func_flyout)
        dropdown_row.addWidget(self.btn_func)

        dropdown_row.addStretch()
        parent_layout.addLayout(dropdown_row)

        # ─── 2. FLOATING POPOVERS ─────────────────────────────────────
        # Trigonometry Popover (4 cols x 2 rows)
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

        # Inequalities Popover (2 cols x 2 rows: <, >, <=, >=)
        self.ineq_popover = QFrame(self)
        self.ineq_popover.setObjectName("SciFlyoutPanel")
        self.ineq_popover.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.ineq_popover.setAutoFillBackground(True)
        self.ineq_popover.setVisible(False)

        ineq_shadow = QGraphicsDropShadowEffect(self.ineq_popover)
        ineq_shadow.setBlurRadius(20)
        ineq_shadow.setOffset(0, 6)
        ineq_shadow.setColor(QColor(0, 0, 0, 160))
        self.ineq_popover.setGraphicsEffect(ineq_shadow)

        ineq_grid = QGridLayout(self.ineq_popover)
        ineq_grid.setContentsMargins(4, 4, 4, 4)
        ineq_grid.setSpacing(3)
        for col in range(2):
            ineq_grid.setColumnStretch(col, 1)
        for row in range(2):
            ineq_grid.setRowStretch(row, 1)

        ineq_keys = [
            (0, 0, "<"), (0, 1, ">"),
            (1, 0, "≤"), (1, 1, "≥")
        ]
        for r, c, sym in ineq_keys:
            btn = QPushButton(sym)
            btn.setProperty("class", "sciFlyoutKey")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda _, s=sym: self._on_ineq_key_clicked(s))
            ineq_grid.addWidget(btn, r, c)

        # Functions Popover (3 cols x 2 rows: |x|, floor, ceil, rand, dms, deg)
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

        func_keys = [
            (0, 0, "|x|", "abs("), (0, 1, "⌊x⌋", "floor("), (0, 2, "⌈x⌉", "ceil("),
            (1, 0, "rand", "rand()"), (1, 1, "dms", "dms("), (1, 2, "deg", "deg(")
        ]
        for r, c, lbl, action in func_keys:
            btn = QPushButton(lbl)
            btn.setProperty("class", "sciFlyoutKey")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda _, act=action: self._on_func_key_clicked(act))
            func_grid.addWidget(btn, r, c)

        # ─── 3. 5x7 KEYPAD GRID ───────────────────────────────────────
        self.key_grid = QGridLayout()
        self.key_grid.setSpacing(3)
        self.button_map = {}

        # 7 rows of 5 columns matching Windows Calculator Graphing keypad
        self.layout_spec = [
            # Row 0: 2nd, pi, e, C, backspace
            [("2ⁿᵈ", "fnKey", self._toggle_2nd),
             ("π", "fnKey", lambda: self.insertToken.emit("pi")),
             ("e", "fnKey", lambda: self.insertToken.emit("e")),
             ("C", "fnKey", self.clearClicked),
             ("⌫", "fnKey", self.backspaceClicked)],
            # Row 1: x^2, 1/x, |x|, x, y
            [("x²", "fnKey", lambda: self._on_2nd_variant("^2", "^3")),
             ("1/x", "fnKey", lambda: self.insertToken.emit("1/(")),
             ("|x|", "fnKey", lambda: self.insertToken.emit("abs(")),
             ("x", "fnKey", lambda: self.insertToken.emit("x")),
             ("y", "fnKey", lambda: self.insertToken.emit("y"))],
            # Row 2: sqrt, (, ), =, /
            [("²√x", "fnKey", lambda: self._on_2nd_variant("sqrt(", "cbrt(")),
             ("(", "fnKey", lambda: self.insertToken.emit("(")),
             (")", "fnKey", lambda: self.insertToken.emit(")")),
             ("=", "fnKey", lambda: self.insertToken.emit("=")),
             ("÷", "opKey", lambda: self.insertToken.emit("/"))],
            # Row 3: x^y, 7, 8, 9, *
            [("xʸ", "fnKey", lambda: self.insertToken.emit("^")),
             ("7", "numKey", lambda: self.insertToken.emit("7")),
             ("8", "numKey", lambda: self.insertToken.emit("8")),
             ("9", "numKey", lambda: self.insertToken.emit("9")),
             ("×", "opKey", lambda: self.insertToken.emit("*"))],
            # Row 4: 10^x, 4, 5, 6, -
            [("10ˣ", "fnKey", lambda: self._on_2nd_variant("10^", "2^")),
             ("4", "numKey", lambda: self.insertToken.emit("4")),
             ("5", "numKey", lambda: self.insertToken.emit("5")),
             ("6", "numKey", lambda: self.insertToken.emit("6")),
             ("−", "opKey", lambda: self.insertToken.emit("-"))],
            # Row 5: log, 1, 2, 3, +
            [("log", "fnKey", lambda: self._on_2nd_variant("log(", "log2(")),
             ("1", "numKey", lambda: self.insertToken.emit("1")),
             ("2", "numKey", lambda: self.insertToken.emit("2")),
             ("3", "numKey", lambda: self.insertToken.emit("3")),
             ("+", "opKey", lambda: self.insertToken.emit("+"))],
            # Row 6: ln, +/-, 0, ., Enter (commit)
            [("ln", "fnKey", lambda: self._on_2nd_variant("ln(", "exp(")),
             ("(-)", "fnKey", lambda: self.insertToken.emit("-")),
             ("0", "numKey", lambda: self.insertToken.emit("0")),
             (".", "numKey", lambda: self.insertToken.emit(".")),
             ("↵", "equalsKey", self.enterClicked)]
        ]

        for r_idx, row in enumerate(self.layout_spec):
            for c_idx, (label, cls_name, action) in enumerate(row):
                btn = QPushButton(label)
                btn.setProperty("class", cls_name)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                btn.setMinimumHeight(30)
                btn.clicked.connect(action)
                self.key_grid.addWidget(btn, r_idx, c_idx)
                self.button_map[label] = btn

        parent_layout.addLayout(self.key_grid, stretch=1)
        self.update_theme_icons("#FFFFFF")

    def _toggle_2nd(self):
        self._is_2nd_active = not self._is_2nd_active
        btn = self.button_map.get("2ⁿᵈ")
        if btn:
            btn.setChecked(self._is_2nd_active)

    def _on_2nd_variant(self, normal_act: str, second_act: str):
        token = second_act if self._is_2nd_active else normal_act
        self.insertToken.emit(token)

    def _toggle_trig_flyout(self):
        is_open = self.btn_trig.isChecked()
        if is_open:
            self.btn_ineq.setChecked(False)
            self.ineq_popover.setVisible(False)
            self.btn_func.setChecked(False)
            self.func_popover.setVisible(False)

            pos = self.btn_trig.pos()
            w, h = 232, 66
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.trig_popover.setGeometry(x, pos.y() + self.btn_trig.height() + 4, w, h)
            self.trig_popover.raise_()
            self.trig_popover.setVisible(True)
        else:
            self.trig_popover.setVisible(False)

    def _toggle_ineq_flyout(self):
        is_open = self.btn_ineq.isChecked()
        if is_open:
            self.btn_trig.setChecked(False)
            self.trig_popover.setVisible(False)
            self.btn_func.setChecked(False)
            self.func_popover.setVisible(False)

            pos = self.btn_ineq.pos()
            w, h = 112, 66
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.ineq_popover.setGeometry(x, pos.y() + self.btn_ineq.height() + 4, w, h)
            self.ineq_popover.raise_()
            self.ineq_popover.setVisible(True)
        else:
            self.ineq_popover.setVisible(False)

    def _toggle_func_flyout(self):
        is_open = self.btn_func.isChecked()
        if is_open:
            self.btn_trig.setChecked(False)
            self.trig_popover.setVisible(False)
            self.btn_ineq.setChecked(False)
            self.ineq_popover.setVisible(False)

            pos = self.btn_func.pos()
            w, h = 176, 66
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.func_popover.setGeometry(x, pos.y() + self.btn_func.height() + 4, w, h)
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
            name = base_fn
            if self._is_trig_hyp:
                name = f"{base_fn}h"
            if self._is_trig_2nd:
                name = f"{name}⁻¹"
            btn.setText(name)

    def _on_trig_key_clicked(self, base_fn: str):
        fn_id = base_fn
        if self._is_trig_2nd and self._is_trig_hyp:
            fn_id = f"a{base_fn}h"
        elif self._is_trig_2nd:
            fn_id = f"a{base_fn}"
        elif self._is_trig_hyp:
            fn_id = f"{base_fn}h"
        self.insertToken.emit(f"{fn_id}(")
        self.btn_trig.setChecked(False)
        self.trig_popover.setVisible(False)

    def _on_ineq_key_clicked(self, sym: str):
        self.insertToken.emit(f" {sym} ")
        self.btn_ineq.setChecked(False)
        self.ineq_popover.setVisible(False)

    def _on_func_key_clicked(self, act: str):
        self.insertToken.emit(act)
        self.btn_func.setChecked(False)
        self.func_popover.setVisible(False)

    def update_theme_icons(self, text_color: str):
        self._current_text_color = text_color
        self.btn_trig.update_icons(text_color)
        self.btn_ineq.update_icons(text_color)
        self.btn_func.update_icons(text_color)

    def mousePressEvent(self, event):
        for popover, btn in [(self.trig_popover, self.btn_trig), (self.ineq_popover, self.btn_ineq), (self.func_popover, self.btn_func)]:
            if popover.isVisible():
                if not popover.geometry().contains(event.pos()) and not btn.geometry().contains(event.pos()):
                    btn.setChecked(False)
                    popover.setVisible(False)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "btn_trig") and hasattr(self, "trig_popover") and self.trig_popover.isVisible():
            pos = self.btn_trig.pos()
            w = 232
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.trig_popover.move(x, pos.y() + self.btn_trig.height() + 4)
        if hasattr(self, "btn_ineq") and hasattr(self, "ineq_popover") and self.ineq_popover.isVisible():
            pos = self.btn_ineq.pos()
            w = 112
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.ineq_popover.move(x, pos.y() + self.btn_ineq.height() + 4)
        if hasattr(self, "btn_func") and hasattr(self, "func_popover") and self.func_popover.isVisible():
            pos = self.btn_func.pos()
            w = 176
            x = max(4, min(pos.x(), self.width() - w - 4))
            self.func_popover.move(x, pos.y() + self.btn_func.height() + 4)

