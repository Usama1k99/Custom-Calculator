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
            if hasattr(self, "_anim") and self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"offset")
            self._anim.setDuration(110)
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(end_val)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
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


class TransparencyToggle(QWidget):
    """
    iOS / Fluent styled pill toggle switch with smooth animated sliding thumb,
    rendering Transparency layers vector icon on the left (ON) and
    Solid / Opaque vector icon on the right (OFF). Zero emojis.
    """
    transparencyToggled = pyqtSignal(bool)  # Emits True for transparency enabled, False for solid
    blurToggled = transparencyToggled       # Backward compatibility alias

    def __init__(self, is_transparency: bool = True, parent=None):
        super().__init__(parent)
        self._is_transparency = is_transparency
        self._offset = 1.0 if is_transparency else 0.0
        self._accent_color = "#F92672"
        self._bg_off_track = "#4B5563"
        self.setFixedSize(64, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # SVG Renderers for crisp vector icons (zero emojis)
        # Transparency ON: 4-Quadrant Minimalist Checkerboard Window (Pair B)
        trans_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
  <rect x="3" y="3" width="18" height="18" rx="3.5" stroke="#FFFFFF" stroke-width="2"/>
  <path d="M12 3v18M3 12h18" stroke="#FFFFFF" stroke-width="1.8"/>
  <rect x="3.5" y="3.5" width="8" height="8" fill="#FFFFFF" rx="1.5" fill-opacity="0.5"/>
  <rect x="12.5" y="12.5" width="8" height="8" fill="#FFFFFF" rx="1.5" fill-opacity="0.5"/>
</svg>"""
        self._trans_renderer = QSvgRenderer(QByteArray(trans_svg.encode("utf-8")))
        self._update_solid_renderer()

    def _update_solid_renderer(self):
        # Dynamically tint solid icon according to track brightness for optimal contrast
        c = QColor(self._bg_off_track)
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
        icon_color = "#4B5563" if lum > 0.55 else "#9CA3AF"
        # Transparency OFF (Solid): Solid Opaque Window Pane (Pair B)
        solid_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
  <rect x="3.5" y="3.5" width="17" height="17" rx="3" fill="{icon_color}" fill-opacity="0.75" stroke="{icon_color}" stroke-width="1.5"/>
</svg>"""
        self._solid_renderer = QSvgRenderer(QByteArray(solid_svg.encode("utf-8")))

    def set_accent_color(self, hex_color: str):
        self._accent_color = hex_color
        self.update()

    def set_off_track_color(self, hex_color: str):
        self._bg_off_track = hex_color
        self._update_solid_renderer()
        self.update()

    @pyqtProperty(float)
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, val: float):
        self._offset = max(0.0, min(1.0, val))
        self.update()

    def is_transparency(self) -> bool:
        return self._is_transparency

    def is_blur(self) -> bool:
        return self.is_transparency()

    def set_transparency(self, is_transparency: bool, animate: bool = True):
        if self._is_transparency == is_transparency and animate:
            return
        self._is_transparency = is_transparency
        end_val = 1.0 if is_transparency else 0.0
        if animate:
            if hasattr(self, "_anim") and self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"offset")
            self._anim.setDuration(110)
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(end_val)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            self._anim.start()
        else:
            self._offset = end_val
            self.update()
        self.transparencyToggled.emit(is_transparency)

    def set_blur(self, is_blur: bool, animate: bool = True):
        self.set_transparency(is_blur, animate)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_transparency(not self._is_transparency)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.set_transparency(not self._is_transparency)
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

        # Render Transparency layers icon on the left (revealed when thumb is on the right)
        trans_rect = QRectF(9.5, (h - 15) / 2.0, 15, 15)
        painter.setOpacity(max(0.0, min(1.0, (self._offset - 0.2) / 0.8)))
        self._trans_renderer.render(painter, trans_rect)

        # Render Solid icon on the right (revealed when thumb is on the left)
        solid_rect = QRectF(w - 24.5, (h - 15) / 2.0, 15, 15)
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


# Backward compatibility alias
BlurEffectToggle = TransparencyToggle
