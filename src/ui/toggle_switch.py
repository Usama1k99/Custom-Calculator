"""
Modern Animated Slidable Toggle Switch for Dark / Light Mode.
Implements pill-shaped capsule track with animated sliding thumb and
vector Sun and Moon icons (zero emojis).
"""

from PyQt6.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, pyqtSignal, Qt, QRectF, QByteArray
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtSvg import QSvgRenderer
from src.ui.mode_icons import MODE_SVGS


class ThemeModeToggle(QWidget):
    """
    iOS / Fluent styled pill toggle switch with smooth animated sliding thumb,
    rendering Sun SVG on the left and Moon SVG on the right.
    """
    modeToggled = pyqtSignal(bool)  # Emits True for dark mode, False for light mode

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._offset = 1.0 if is_dark else 0.0
        self._accent_color = "#F92672"
        self._bg_light_track = "#D6D6D6"
        self.setFixedSize(64, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # SVG Renderers for crisp vector icons
        sun_svg = MODE_SVGS.get("Sun", "").replace("currentColor", "#F59E0B")
        moon_svg = MODE_SVGS.get("Moon", "").replace("currentColor", "#FFFFFF")
        self._sun_renderer = QSvgRenderer(QByteArray(sun_svg.encode("utf-8")))
        self._moon_renderer = QSvgRenderer(QByteArray(moon_svg.encode("utf-8")))

    def set_accent_color(self, hex_color: str):
        self._accent_color = hex_color
        self.update()

    @pyqtProperty(float)
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, val: float):
        self._offset = max(0.0, min(1.0, val))
        self.update()

    def is_dark(self) -> bool:
        return self._is_dark

    def set_dark_mode(self, is_dark: bool, animate: bool = True):
        if self._is_dark == is_dark and animate:
            return
        self._is_dark = is_dark
        end_val = 1.0 if is_dark else 0.0
        if animate:
            self._anim = QPropertyAnimation(self, b"offset")
            self._anim.setDuration(160)
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(end_val)
            self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._anim.start()
        else:
            self._offset = end_val
            self.update()
        self.modeToggled.emit(is_dark)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_dark_mode(not self._is_dark)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.set_dark_mode(not self._is_dark)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Interpolate track background color
        c_light = QColor(self._bg_light_track)
        c_dark = QColor(self._accent_color)
        r = int(c_light.red() + (c_dark.red() - c_light.red()) * self._offset)
        g = int(c_light.green() + (c_dark.green() - c_light.green()) * self._offset)
        b = int(c_light.blue() + (c_dark.blue() - c_light.blue()) * self._offset)
        track_color = QColor(r, g, b)

        # Draw Pill Track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # Draw Subtle Track Inner Border
        border_pen = QPen(QColor(0, 0, 0, 30 if self._offset < 0.5 else 60), 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

        # Render Moon icon on the left (revealed when thumb is on the right in Dark Mode)
        moon_rect = QRectF(9, (h - 16) / 2.0, 16, 16)
        painter.setOpacity(max(0.0, min(1.0, (self._offset - 0.2) / 0.8)))
        self._moon_renderer.render(painter, moon_rect)

        # Render Sun icon on the right (revealed when thumb is on the left in Light Mode)
        sun_rect = QRectF(w - 25, (h - 16) / 2.0, 16, 16)
        painter.setOpacity(max(0.0, min(1.0, (0.8 - self._offset) / 0.8)))
        self._sun_renderer.render(painter, sun_rect)

        painter.setOpacity(1.0)

        # Draw Circular Sliding Thumb
        thumb_diameter = h - 6.0
        thumb_margin = 3.0
        thumb_travel = w - thumb_diameter - (thumb_margin * 2.0)
        thumb_x = thumb_margin + (self._offset * thumb_travel)
        thumb_y = thumb_margin

        # Thumb drop shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        painter.drawEllipse(QRectF(thumb_x, thumb_y + 1.0, thumb_diameter, thumb_diameter))

        # Thumb body
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_diameter, thumb_diameter))

        painter.end()
