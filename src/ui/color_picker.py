"""
Compact IDE-Style Color Picker Popover for PyQt6.
Mimics modern IDE CSS color inspectors (VS Code / WebStorm) with 2D Sat/Val canvas,
Hue slider, Hex/RGB inputs, and live preview callback.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QMouseEvent, QPen, QBrush
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QFrame, QSpinBox
)


class SatValCanvas(QWidget):
    colorChanged = pyqtSignal(float, float)  # sat (0-1), val (0-1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 140)
        self.hue = 0.6  # 0.0 - 1.0
        self.sat = 0.7  # 0.0 - 1.0
        self.val = 0.9  # 0.0 - 1.0

    def set_hue(self, hue: float):
        self.hue = max(0.0, min(1.0, hue))
        self.update()

    def set_sat_val(self, sat: float, val: float):
        self.sat = max(0.0, min(1.0, sat))
        self.val = max(0.0, min(1.0, val))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Pure hue color
        base_color = QColor.fromHsvF(self.hue, 1.0, 1.0)

        # Horizontal gradient: White -> Base Hue
        grad_h = QLinearGradient(0, 0, w, 0)
        grad_h.setColorAt(0, QColor(255, 255, 255))
        grad_h.setColorAt(1, base_color)
        painter.fillRect(0, 0, w, h, grad_h)

        # Vertical gradient: Transparent -> Black
        grad_v = QLinearGradient(0, 0, 0, h)
        grad_v.setColorAt(0, QColor(0, 0, 0, 0))
        grad_v.setColorAt(1, QColor(0, 0, 0, 255))
        painter.fillRect(0, 0, w, h, grad_v)

        # Draw crosshair indicator
        cx = int(self.sat * w)
        cy = int((1.0 - self.val) * h)

        pen = QPen(QColor(255, 255, 255) if self.val < 0.5 else QColor(0, 0, 0), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), 6, 6)

    def mousePressEvent(self, event: QMouseEvent):
        self._update_from_mouse(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_mouse(event)

    def _update_from_mouse(self, event: QMouseEvent):
        w = max(1, self.width())
        h = max(1, self.height())
        x = max(0, min(w, event.pos().x()))
        y = max(0, min(h, event.pos().y()))

        self.sat = x / w
        self.val = 1.0 - (y / h)
        self.update()
        self.colorChanged.emit(self.sat, self.val)


class HueBar(QWidget):
    hueChanged = pyqtSignal(float)  # hue (0-1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 14)
        self.hue = 0.6

    def set_hue(self, hue: float):
        self.hue = max(0.0, min(1.0, hue))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w, 0)
        steps = 6
        for i in range(steps + 1):
            grad.setColorAt(i / steps, QColor.fromHsvF(i / steps, 1.0, 1.0))

        painter.fillRect(0, 0, w, h, grad)

        # Indicator
        x = int(self.hue * w)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor.fromHsvF(self.hue, 1.0, 1.0)))
        painter.drawRect(max(0, x - 2), 0, 4, h)

    def mousePressEvent(self, event: QMouseEvent):
        self._update_from_mouse(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_mouse(event)

    def _update_from_mouse(self, event: QMouseEvent):
        w = max(1, self.width())
        x = max(0, min(w, event.pos().x()))
        self.hue = x / w
        self.update()
        self.hueChanged.emit(self.hue)


class IDEColorPicker(QDialog):
    """
    Compact IDE-style color picker popover dialog.
    """
    colorSelected = pyqtSignal(str)  # returns Hex string e.g. '#6366F1'

    def __init__(self, initial_hex: str = "#6366F1", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Inspector")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(240, 310)

        self.current_color = QColor(initial_hex if initial_hex.startswith("#") else f"#{initial_hex}")
        if not self.current_color.isValid():
            self.current_color = QColor("#6366F1")

        self._init_ui()
        self._sync_ui_from_color(self.current_color)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 2D Sat/Val Canvas
        self.canvas = SatValCanvas(self)
        self.canvas.colorChanged.connect(self._on_sat_val_changed)
        layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)

        # 1D Hue Bar
        self.hue_bar = HueBar(self)
        self.hue_bar.hueChanged.connect(self._on_hue_changed)
        layout.addWidget(self.hue_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Swatch & Hex input row
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)

        self.preview_box = QFrame()
        self.preview_box.setFixedSize(32, 26)
        self.preview_box.setStyleSheet("border-radius: 4px; border: 1px solid #444;")
        mid_row.addWidget(self.preview_box)

        self.hex_input = QLineEdit()
        self.hex_input.setFixedHeight(26)
        self.hex_input.setMaxLength(9)
        self.hex_input.textChanged.connect(self._on_hex_input_changed)
        mid_row.addWidget(self.hex_input)

        layout.addLayout(mid_row)

        # Quick preset palette
        presets = ["#000000", "#0B0F19", "#18181B", "#10B981", "#6366F1", "#F97316", "#2563EB", "#FFFFFF"]
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for hex_code in presets:
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            btn.setStyleSheet(f"background-color: {hex_code}; border-radius: 3px; border: 1px solid #555;")
            btn.clicked.connect(lambda _, c=hex_code: self._set_color_from_hex(c))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setDefault(True)
        self.apply_btn.clicked.connect(self._on_apply)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.apply_btn)
        layout.addLayout(btn_row)

    def _sync_ui_from_color(self, color: QColor):
        h, s, v, _ = color.getHsvF()
        if h < 0:
            h = 0.0
        self.canvas.set_hue(h)
        self.canvas.set_sat_val(s, v)
        self.hue_bar.set_hue(h)
        hex_str = color.name().upper()
        self.hex_input.blockSignals(True)
        self.hex_input.setText(hex_str)
        self.hex_input.blockSignals(False)
        self.preview_box.setStyleSheet(f"background-color: {hex_str}; border-radius: 4px; border: 1px solid #666;")

    def _on_sat_val_changed(self, sat: float, val: float):
        h = self.hue_bar.hue
        self.current_color = QColor.fromHsvF(h, sat, val)
        self._sync_inputs_only()

    def _on_hue_changed(self, hue: float):
        self.canvas.set_hue(hue)
        self.current_color = QColor.fromHsvF(hue, self.canvas.sat, self.canvas.val)
        self._sync_inputs_only()

    def _sync_inputs_only(self):
        hex_str = self.current_color.name().upper()
        self.hex_input.blockSignals(True)
        self.hex_input.setText(hex_str)
        self.hex_input.blockSignals(False)
        self.preview_box.setStyleSheet(f"background-color: {hex_str}; border-radius: 4px; border: 1px solid #666;")

    def _on_hex_input_changed(self, text: str):
        if not text.startswith("#"):
            text = f"#{text}"
        c = QColor(text)
        if c.isValid():
            self.current_color = c
            h, s, v, _ = c.getHsvF()
            if h >= 0:
                self.canvas.set_hue(h)
                self.hue_bar.set_hue(h)
            self.canvas.set_sat_val(s, v)
            self.preview_box.setStyleSheet(f"background-color: {c.name()}; border-radius: 4px; border: 1px solid #666;")

    def _set_color_from_hex(self, hex_code: str):
        c = QColor(hex_code)
        if c.isValid():
            self.current_color = c
            self._sync_ui_from_color(c)

    def _on_apply(self):
        self.colorSelected.emit(self.current_color.name().upper())
        self.accept()

