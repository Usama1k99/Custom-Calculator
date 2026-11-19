"""
Dual-Tier & Live Preview Display Widget with Robust Keyboard & Input Sanitization.
Replicates native Windows Calculator input ergonomics:
- '0' is always displayed by default.
- Leading zero is cleanly stripped/replaced upon typing a valid character.
- Character input is strictly restricted to valid sets for Standard, Scientific, and Programmer modes.
- Directional typing with arrow cursor and caret locking to end of display.
"""

import re
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics, QCursor, QKeyEvent
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QApplication
)
from src.core.input_validator import (
    is_char_allowed,
    sanitize_leading_zeros,
    validate_and_sanitize_input,
)


class CalculatorDisplayEdit(QLineEdit):
    """
    Custom QLineEdit tailored for Calculator input validation and ergonomics.
    Enforces allowed characters, removes leading zeros on the fly, and disables arbitrary caret jumps.
    """
    operatorRequested = pyqtSignal(str)
    evaluateRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    clearEntryRequested = pyqtSignal()
    unaryRequested = pyqtSignal(str)
    parenthesisRequested = pyqtSignal(str)

    def __init__(self, text: str = "0", parent=None):
        super().__init__(text, parent)
        self.mode = "Standard"
        self.radix = "DEC"
        self.setObjectName("PrimaryValueDisplay")
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFrame(False)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # Disable mouse dragging / text selection caret jumps (native Win Calc behavior)
        self.mousePressEvent = self._on_mouse_press
        self.mouseMoveEvent = lambda e: None
        self.mouseDoubleClickEvent = lambda e: None

    def _on_mouse_press(self, event):
        self.setFocus()
        self.setCursorPosition(len(self.text()))
        event.accept()

    def set_mode(self, mode: str, radix: str = "DEC"):
        self.mode = mode
        self.radix = radix

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        # Keyboard shortcuts
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                text = self.text()
                if text:
                    QApplication.clipboard().setText(text)
                return
            elif key == Qt.Key.Key_V:
                cb_text = QApplication.clipboard().text()
                sanitized = validate_and_sanitize_input(cb_text, self.mode, self.radix)
                if sanitized:
                    if self.mode != "Programmer":
                        def _cap_digits(m):
                            sign = m.group(1) or ""
                            int_part = m.group(2)
                            frac_part = m.group(3) or ""
                            if frac_part:
                                frac_digits = frac_part[1:]
                                avail = max(0, 16 - len(int_part))
                                return f"{sign}{int_part[:16]}.{frac_digits[:avail]}"
                            return f"{sign}{int_part[:16]}"
                        sanitized = re.sub(r'(-?)(\d+)(\.\d+)?', _cap_digits, sanitized)
                    cur = self.text()
                    if cur == "0":
                        new_val = sanitized
                    else:
                        new_val = sanitize_leading_zeros(cur + sanitized, self.mode)
                    self.setText(new_val)
                    self.setCursorPosition(len(new_val))
                    self.textEdited.emit(new_val)
                return
            elif key == Qt.Key.Key_A:
                self.selectAll()
                return

        # Forward all calculator keystrokes to MainWindow for uniform handling & button flash animations
        win = self.window()
        if win and hasattr(win, "keyPressEvent") and win is not self:
            win.keyPressEvent(event)
            event.accept()
            return

        event.ignore()


class DualTierDisplay(QFrame):
    expressionClicked = pyqtSignal(str)
    userTyped = pyqtSignal(str)
    operatorClicked = pyqtSignal(str)
    equalsClicked = pyqtSignal()
    clearClicked = pyqtSignal()
    clearEntryClicked = pyqtSignal()
    unaryClicked = pyqtSignal(str)
    parenthesisClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DisplayArea")
        self.setFixedHeight(125)
        self.mode = "Standard"
        self.radix = "DEC"

        self._init_ui()

    def set_mode(self, mode: str, radix: str = "DEC"):
        self.mode = mode
        self.radix = radix
        if hasattr(self, "primary_display"):
            self.primary_display.set_mode(mode, radix)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 4)
        layout.setSpacing(2)

        # ─── TIER 1: EXPRESSION TRAIL (PINNED / ACTIVE) ──────────────────────
        self.expression_label = QLabel("")
        self.expression_label.setObjectName("ExpressionTrail")
        self.expression_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.expression_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.expression_label.setToolTip("Click to restore this formula")
        self.expression_label.mousePressEvent = self._on_ribbon_clicked
        layout.addWidget(self.expression_label)

        # ─── TIER 2: LIVE GHOST PREVIEW (DEDICATED SEPARATE ROW) ─────────────
        self.ghost_preview = QLabel("")
        self.ghost_preview.setObjectName("GhostPreviewLine")
        self.ghost_preview.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ghost_preview.setFixedHeight(20)
        layout.addWidget(self.ghost_preview)

        # ─── TIER 3: PRIMARY ACTIVE VALUE (WINDOWS CALC FLOW) ───────────────
        self.primary_display = CalculatorDisplayEdit("0", self)
        self.primary_display.textEdited.connect(self._on_text_edited)
        self.primary_display.operatorRequested.connect(self.operatorClicked)
        self.primary_display.evaluateRequested.connect(self.equalsClicked)
        self.primary_display.clearRequested.connect(self.clearClicked)
        self.primary_display.clearEntryRequested.connect(self.clearEntryClicked)
        self.primary_display.unaryRequested.connect(self.unaryClicked)
        self.primary_display.parenthesisRequested.connect(self.parenthesisClicked)

        self._auto_scale_font("0")
        layout.addWidget(self.primary_display, stretch=1)

    def _on_text_edited(self, new_text: str):
        sanitized = validate_and_sanitize_input(new_text, self.mode, self.radix)
        if self.primary_display.text() != sanitized:
            self.primary_display.blockSignals(True)
            self.primary_display.setText(sanitized)
            self.primary_display.setCursorPosition(len(sanitized))
            self.primary_display.blockSignals(False)
        self.userTyped.emit(sanitized)

    def _is_error_text(self, text: str) -> bool:
        err_keywords = ("invalid", "cannot", "undefined", "overflow", "error")
        return any(kw in text.lower() for kw in err_keywords)

    def _update_display_mode(self, text: str):
        is_error = self._is_error_text(text)
        prev_is_error = bool(self.primary_display.property("is_error"))
        self.primary_display.setReadOnly(is_error)
        self.primary_display.setProperty("is_error", is_error)
        self.primary_display.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        if prev_is_error != is_error:
            self.primary_display.style().unpolish(self.primary_display)
            self.primary_display.style().polish(self.primary_display)

    def set_drafting_state(self, expression_trail: str, active_token: str, live_preview: str = ""):
        # If user is entering the second/subsequent operand after an operator, display complete formula in ribbon
        KNOWN_TRAILING_OPS = ("+", "-", "*", "/", "×", "÷", "−", "AND", "OR", "XOR", "<<", ">>", "mod", "%")
        if expression_trail:
            trimmed = expression_trail.rstrip()
            if active_token and any(trimmed.endswith(op) for op in KNOWN_TRAILING_OPS):
                displayed_trail = f"{expression_trail}{active_token}".strip()
            else:
                displayed_trail = expression_trail.strip()
        else:
            displayed_trail = ""

        self.expression_label.setText(self._truncate_left(displayed_trail, 45))

        if live_preview and live_preview != active_token:
            self.ghost_preview.setText(f"= {live_preview}")
        else:
            self.ghost_preview.setText("")

        if active_token:
            val = active_token
            self._update_display_mode(val)
            if self.primary_display.text() != val:
                self.primary_display.blockSignals(True)
                self.primary_display.setText(val)
                self.primary_display.setCursorPosition(len(val))
                self.primary_display.blockSignals(False)
            self._auto_scale_font(self.primary_display.text())
        elif not expression_trail:
            # Clean initial / cleared state
            val = "0"
            self._update_display_mode(val)
            if self.primary_display.text() != val:
                self.primary_display.blockSignals(True)
                self.primary_display.setText(val)
                self.primary_display.setCursorPosition(len(val))
                self.primary_display.blockSignals(False)
            self._auto_scale_font(self.primary_display.text())

    def set_evaluated_state(self, expression_used: str, final_result: str):
        ribbon_text = expression_used.strip()
        if not ribbon_text.endswith("="):
            ribbon_text = f"{ribbon_text} ="

        self.expression_label.setText(self._truncate_left(ribbon_text, 45))
        self.ghost_preview.setText("")

        self._update_display_mode(final_result)

        self.primary_display.blockSignals(True)
        self.primary_display.setText(final_result)
        self.primary_display.setCursorPosition(len(final_result))
        self.primary_display.blockSignals(False)

        self._auto_scale_font(final_result)

    def _truncate_left(self, text: str, max_chars: int) -> str:
        if len(text) > max_chars:
            return f"... {text[-(max_chars - 4):]}"
        return text

    def _auto_scale_font(self, text: str):
        if self._is_error_text(text):
            font = self.primary_display.font()
            font.setPointSize(26 if len(text) <= 16 else 18)
            self.primary_display.setFont(font)
            return

        length = len(text)
        if length <= 9:
            font_size = 44
        elif length <= 13:
            font_size = 34
        elif length <= 18:
            font_size = 26
        elif length <= 24:
            font_size = 20
        elif length <= 32:
            font_size = 15
        else:
            font_size = 12

        # Use QFontMetrics to ensure text never overflows the width of the display edit
        available_w = self.primary_display.width() - 24
        if available_w > 50:
            test_font = self.primary_display.font()
            test_font.setPointSize(font_size)
            fm = QFontMetrics(test_font)
            while font_size > 11 and fm.horizontalAdvance(text) > available_w:
                font_size -= 1
                test_font.setPointSize(font_size)
                fm = QFontMetrics(test_font)

        font = self.primary_display.font()
        if font_size > 0:
            font.setPointSize(font_size)
            self.primary_display.setFont(font)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "primary_display"):
            self._auto_scale_font(self.primary_display.text())

    def _on_ribbon_clicked(self, event):
        text = self.expression_label.text().replace("...", "").replace("=", "").strip()
        if text:
            self.expressionClicked.emit(text)

    def copy_to_clipboard(self):
        text = self.primary_display.text()
        if text:
            QApplication.clipboard().setText(text)
