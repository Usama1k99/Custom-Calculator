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
from PyQt6.QtGui import QFont, QCursor, QKeyEvent
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

        # Evaluation & Clear Keys
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Equal):
            self.evaluateRequested.emit()
            return
        elif key == Qt.Key.Key_Escape:
            self.clearRequested.emit()
            return
        elif key == Qt.Key.Key_Delete:
            self.clearEntryRequested.emit()
            return
        elif key == Qt.Key.Key_Backspace:
            if self.isReadOnly():
                self.clearRequested.emit()
                return
            cur = self.text()
            if cur == "0":
                return
            new_val = cur[:-1] if len(cur) > 1 else "0"
            if not new_val or new_val == "-":
                new_val = "0"
            new_val = sanitize_leading_zeros(new_val, self.mode)
            self.setText(new_val)
            self.setCursorPosition(len(new_val))
            self.textEdited.emit(new_val)
            return

        # Operator keys in Standard mode (trigger calculation operator, don't write symbol into operand)
        if self.mode == "Standard":
            op_map = {
                Qt.Key.Key_Plus: "+",
                Qt.Key.Key_Minus: "−",
                Qt.Key.Key_Asterisk: "×",
                Qt.Key.Key_Slash: "÷",
                Qt.Key.Key_Percent: "%",
            }
            if key in op_map:
                self.operatorRequested.emit(op_map[key])
                return

        # Operator keys in Programmer mode
        if self.mode == "Programmer":
            prog_op_map = {
                Qt.Key.Key_Plus: "+",
                Qt.Key.Key_Minus: "−",
                Qt.Key.Key_Asterisk: "×",
                Qt.Key.Key_Slash: "÷",
                Qt.Key.Key_Percent: "%",
                Qt.Key.Key_Ampersand: "AND",
                Qt.Key.Key_Bar: "OR",
                Qt.Key.Key_AsciiCircum: "XOR",
                Qt.Key.Key_AsciiTilde: "NOT",
            }
            if key in prog_op_map:
                self.operatorRequested.emit(prog_op_map[key])
                return

        char = event.text()
        if not char:
            event.ignore()
            return

        # Decimal point mapping
        if char in (",", "."):
            if self.mode == "Programmer":
                event.ignore()
                return
            char = "."

        # Check whitelist for current mode & radix
        if not is_char_allowed(char, self.mode, self.radix):
            event.ignore()
            return

        # Programmer mode hex uppercase normalization
        if self.mode == "Programmer" and self.radix.upper() == "HEX":
            char = char.upper()

        cur = self.text()
        if self.isReadOnly() or cur in ("0", "-0"):
            if cur == "-0":
                if char == ".":
                    new_val = "-0."
                elif char == "0":
                    new_val = "-0"
                else:
                    new_val = f"-{char}"
            else:  # cur == "0" or error text
                if char == ".":
                    new_val = "0."
                elif char == "0":
                    new_val = "0"
                elif self.mode == "Scientific" and char in ("(", "["):
                    new_val = char
                else:
                    # Clean replacement of leading zero with the entered character
                    new_val = char
        else:
            if char == ".":
                # Disallow duplicate decimal point in current token
                tokens = re.split(r'[\s\+\-\*\/\^\%\(\)]+', cur)
                last_tok = tokens[-1] if tokens else ""
                if "." in last_tok:
                    event.ignore()
                    return
                new_val = cur + "."
            else:
                if cur.endswith(" 0") and char.isalnum() and char != "0":
                    new_val = cur[:-1] + char
                elif cur.endswith("(0") and char.isalnum() and char != "0":
                    new_val = cur[:-1] + char
                elif cur.endswith(" 0") and char == "0":
                    event.ignore()
                    return
                else:
                    new_val = cur + char

        new_val = sanitize_leading_zeros(new_val, self.mode)
        self.setText(new_val)
        self.setCursorPosition(len(new_val))
        self.textEdited.emit(new_val)
        event.accept()


class DualTierDisplay(QFrame):
    expressionClicked = pyqtSignal(str)
    userTyped = pyqtSignal(str)
    operatorClicked = pyqtSignal(str)
    equalsClicked = pyqtSignal()
    clearClicked = pyqtSignal()
    clearEntryClicked = pyqtSignal()

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
        # If user is entering the second/subsequent operand, display complete formula in ribbon
        if expression_trail:
            displayed_trail = f"{expression_trail}{active_token}".strip()
        else:
            displayed_trail = ""

        self.expression_label.setText(self._truncate_left(displayed_trail, 45))

        if live_preview and live_preview != active_token:
            self.ghost_preview.setText(f"= {live_preview}")
        else:
            self.ghost_preview.setText("")

        val = active_token if active_token else "0"
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
            font.setPointSize(26 if len(text) <= 16 else 20)
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
        else:
            font_size = 16

        font = self.primary_display.font()
        if font_size > 0:
            font.setPointSize(font_size)
            self.primary_display.setFont(font)

    def _on_ribbon_clicked(self, event):
        text = self.expression_label.text().replace("...", "").replace("=", "").strip()
        if text:
            self.expressionClicked.emit(text)

    def copy_to_clipboard(self):
        text = self.primary_display.text()
        if text:
            QApplication.clipboard().setText(text)
