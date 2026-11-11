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


class BlurEffectToggle(QWidget):
    """
    iOS / Fluent styled pill toggle switch with smooth animated sliding thumb,
    rendering Frosted / Blur sparkle vector icon on the left (ON) and
    Solid / Disabled vector icon on the right (OFF). Zero emojis.
    """
    blurToggled = pyqtSignal(bool)  # Emits True for blur enabled, False for solid

    def __init__(self, is_blur: bool = True, parent=None):
        super().__init__(parent)
        self._is_blur = is_blur
        self._offset = 1.0 if is_blur else 0.0
        self._accent_color = "#F92672"
        self._bg_off_track = "#4B5563"
        self.setFixedSize(64, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # SVG Renderers for crisp vector icons (zero emojis)
        blur_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>
</svg>"""
        solid_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#9CA3AF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="8"/>
  <line x1="6.3" y1="6.3" x2="17.7" y2="17.7"/>
</svg>"""
        self._blur_renderer = QSvgRenderer(QByteArray(blur_svg.encode("utf-8")))
        self._solid_renderer = QSvgRenderer(QByteArray(solid_svg.encode("utf-8")))

    def set_accent_color(self, hex_color: str):
        self._accent_color = hex_color
        self.update()

    def set_off_track_color(self, hex_color: str):
        self._bg_off_track = hex_color
        self.update()

    @pyqtProperty(float)
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, val: float):
        self._offset = max(0.0, min(1.0, val))
        self.update()

    def is_blur(self) -> bool:
        return self._is_blur

    def set_blur(self, is_blur: bool, animate: bool = True):
        if self._is_blur == is_blur and animate:
            return
        self._is_blur = is_blur
        end_val = 1.0 if is_blur else 0.0
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
        self.blurToggled.emit(is_blur)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_blur(not self._is_blur)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.set_blur(not self._is_blur)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Interpolate track background color
        c_off = QColor(self._bg_off_track)
        c_on = QColor(self._accent_color)
        r = int(c_off.red() + (c_on.red() - c_off.red()) * self._offset)
        g = int(c_off.green() + (c_on.green() - c_off.green()) * self._offset)
        b = int(c_off.blue() + (c_on.blue() - c_off.blue()) * self._offset)
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

        # Render Blur sparkle icon on the left (revealed when thumb is on the right in Blur ON)
        blur_rect = QRectF(9, (h - 16) / 2.0, 16, 16)
        painter.setOpacity(max(0.0, min(1.0, (self._offset - 0.2) / 0.8)))
        self._blur_renderer.render(painter, blur_rect)

        # Render Solid icon on the right (revealed when thumb is on the left in Blur OFF)
        solid_rect = QRectF(w - 25, (h - 14) / 2.0, 14, 14)
        painter.setOpacity(max(0.0, min(1.0, (0.8 - self._offset) / 0.8)))
        self._solid_renderer.render(painter, solid_rect)

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
