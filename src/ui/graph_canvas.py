"""
High-Performance Interactive Cartesian Coordinate Graph Canvas.
Renders 2D mathematical functions with:
- Antialiased Cartesian grid lines with dynamic zoom-adaptive intervals
- Smooth mouse drag panning & wheel zooming centered on cursor
- Multiple simultaneous function curves with distinct vibrant color palettes
- Asymptote and discontinuity protection (no spurious vertical lines)
- Interactive Curve Tracing: snaps glowing marker to curve with real-time (x, y) HUD tooltip
- Key Graph Features: highlights roots (x-intercepts) and y-intercepts
- Zero emojis across all UI elements.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPainterPath, QMouseEvent, QWheelEvent, QIcon
)
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from src.core.graph_engine import GraphFunction
from src.ui.graph_options_popover import GraphOptionsPopover
from src.ui.mode_icons import get_themed_icon


# Vibrant color palette for simultaneous functions
CURVE_PALETTE = [
    "#38BDF8",  # Sky Blue / Cyan
    "#F97316",  # Bright Amber / Orange
    "#F43F5E",  # Rose Pink
    "#10B981",  # Vivid Emerald
    "#A855F7",  # Bright Violet
    "#EAB308",  # Gold Yellow
]


class GraphCanvas(QWidget):
    tracePointChanged = pyqtSignal(float, float, str)  # (x, y, func_label)
    viewBoundsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GraphCanvas")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Coordinate view window bounds
        self.x_min = -10.0
        self.x_max = 10.0
        self.y_min = -10.0
        self.y_max = 10.0

        self.functions: List[GraphFunction] = []
        self.parameters: Dict[str, float] = {}
        self.curve_line_width = 2.5
        self.always_light = False
        self._raw_theme_tokens: Dict[str, str] = {}

        # Interaction state
        self._is_dragging = False
        self._last_mouse_pos = QPoint()
        self._cursor_math_pos: Optional[QPointF] = None
        self._trace_active = True
        self._active_trace_point: Optional[Tuple[float, float, str, str]] = None  # (x, y, name, color)

        # Visual Theme tokens (Default Dark)
        self.theme_colors = {
            "bg": "#1C1C1E",
            "grid_major": "rgba(255, 255, 255, 0.12)",
            "grid_minor": "rgba(255, 255, 255, 0.05)",
            "axis": "#888888",
            "text": "#AAAAAA",
            "hud_bg": "#2A2A2D",
            "hud_border": "rgba(255, 255, 255, 0.18)"
        }

        self._init_overlay_toolbar()
        self.options_popover = GraphOptionsPopover(self, parent=self)

    def _init_overlay_toolbar(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        layout.setSpacing(6)

        # Overlay Toolbar Frame
        toolbar = QFrame(self)
        toolbar.setObjectName("GraphToolbar")
        toolbar.setStyleSheet("""
            QFrame#GraphToolbar {
                background: rgba(30, 30, 30, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 2px;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #CCCCCC;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 26px;
                min-height: 26px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.25);
            }
        """)

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(4)

        # Options / Settings Button (vector icon, zero emojis)
        self.btn_options = QPushButton(toolbar)
        self.btn_options.setIcon(get_themed_icon("Settings", self.theme_colors.get("text", "#CCCCCC"), size=16))
        self.btn_options.setIconSize(QSize(16, 16))
        self.btn_options.setToolTip("Graph options (Window, Units, Theme)")
        self.btn_options.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_options.clicked.connect(self._toggle_options_popover)
        tb_layout.addWidget(self.btn_options)

        btn_zoom_in = QPushButton("+", toolbar)
        btn_zoom_in.setToolTip("Zoom In")
        btn_zoom_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_in.clicked.connect(lambda: self.zoom(0.75))
        tb_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("-", toolbar)
        btn_zoom_out.setToolTip("Zoom Out")
        btn_zoom_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zoom_out.clicked.connect(lambda: self.zoom(1.33))
        tb_layout.addWidget(btn_zoom_out)

        btn_reset = QPushButton("Reset", toolbar)
        btn_reset.setToolTip("Reset View [-10, 10]")
        btn_reset.setStyleSheet("font-size: 11px; padding: 0 4px;")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_view)
        tb_layout.addWidget(btn_reset)

        layout.addWidget(toolbar)

    def _toggle_options_popover(self):
        is_visible = not self.options_popover.isVisible()
        if is_visible:
            self.options_popover.update_displayed_bounds()
            # Position popover below the top toolbar
            pw = 310
            ph = 430
            px = max(10, self.width() - pw - 12)
            self.options_popover.setGeometry(px, 48, pw, ph)
            self.options_popover.raise_()
            self.options_popover.setVisible(True)
        else:
            self.options_popover.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "options_popover") and self.options_popover.isVisible():
            pw = self.options_popover.width()
            px = max(10, self.width() - pw - 12)
            self.options_popover.move(px, 48)

    def set_theme_tokens(self, tokens: Dict[str, str]):
        self._raw_theme_tokens = dict(tokens)
        self.update_theme()

    def update_theme(self):
        if getattr(self, "always_light", False):
            self.theme_colors["bg"] = "#FFFFFF"
            self.theme_colors["grid_major"] = "rgba(0, 0, 0, 0.12)"
            self.theme_colors["grid_minor"] = "rgba(0, 0, 0, 0.05)"
            self.theme_colors["axis"] = "#333333"
            self.theme_colors["text"] = "#555555"
            self.theme_colors["hud_bg"] = "#F0F0F0"
            self.theme_colors["hud_border"] = "rgba(0, 0, 0, 0.18)"
        else:
            tokens = self._raw_theme_tokens
            self.theme_colors["bg"] = tokens.get("bg_surface", "#1C1C1E")
            self.theme_colors["grid_major"] = tokens.get("border_subtle", "rgba(255, 255, 255, 0.12)")
            self.theme_colors["grid_minor"] = "rgba(255, 255, 255, 0.05)"
            self.theme_colors["axis"] = tokens.get("text_secondary", "#888888")
            self.theme_colors["text"] = tokens.get("text_secondary", "#AAAAAA")
            self.theme_colors["hud_bg"] = tokens.get("bg_card", "#2A2A2D")
            self.theme_colors["hud_border"] = "rgba(255, 255, 255, 0.18)"

        if hasattr(self, "btn_options"):
            text_color = self.theme_colors.get("text", "#CCCCCC")
            self.btn_options.setIcon(get_themed_icon("Settings", text_color, size=16))
        if hasattr(self, "options_popover"):
            self.options_popover.set_theme_tokens(self._raw_theme_tokens)
        self.update()

    def set_functions(self, funcs: List[GraphFunction]):
        self.functions = funcs
        self.update()

    def set_parameters(self, params: Dict[str, float]):
        self.parameters = dict(params)
        self.update()

    def reset_view(self):
        self.x_min, self.x_max = -10.0, 10.0
        self.y_min, self.y_max = -10.0, 10.0
        self.viewBoundsChanged.emit()
        self.update()

    def zoom(self, factor: float, center_x: Optional[float] = None, center_y: Optional[float] = None):
        """Zooms around a given mathematical center point (or viewport center)."""
        if center_x is None:
            center_x = (self.x_min + self.x_max) / 2.0
        if center_y is None:
            center_y = (self.y_min + self.y_max) / 2.0

        half_w = (self.x_max - self.x_min) * 0.5 * factor
        half_h = (self.y_max - self.y_min) * 0.5 * factor

        # Prevent extreme zoom limits
        if half_w < 1e-4 or half_w > 1e6:
            return

        self.x_min = center_x - half_w
        self.x_max = center_x + half_w
        self.y_min = center_y - half_h
        self.y_max = center_y + half_h

        self.viewBoundsChanged.emit()
        self.update()

    # ─── COORDINATE CONVERSION ───────────────────────────────────────
    def math_to_pixel(self, x: float, y: float) -> QPointF:
        w = max(1, self.width())
        h = max(1, self.height())
        px = ((x - self.x_min) / (self.x_max - self.x_min)) * w
        py = ((self.y_max - y) / (self.y_max - self.y_min)) * h
        return QPointF(px, py)

    def pixel_to_math(self, px: float, py: float) -> Tuple[float, float]:
        w = max(1, self.width())
        h = max(1, self.height())
        x = self.x_min + (px / w) * (self.x_max - self.x_min)
        y = self.y_max - (py / h) * (self.y_max - self.y_min)
        return x, y

    # ─── MOUSE INTERACTION: PANNING & TRACING ────────────────────────
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()
        if self._is_dragging:
            dx_px = pos.x() - self._last_mouse_pos.x()
            dy_px = pos.y() - self._last_mouse_pos.y()
            self._last_mouse_pos = pos

            w = max(1, self.width())
            h = max(1, self.height())
            dx_math = dx_px * (self.x_max - self.x_min) / w
            dy_math = dy_px * (self.y_max - self.y_min) / h

            self.x_min -= dx_math
            self.x_max -= dx_math
            self.y_min += dy_math
            self.y_max += dy_math

            self.viewBoundsChanged.emit()
            self.update()
        else:
            # Curve Tracing
            mx, my = self.pixel_to_math(pos.x(), pos.y())
            self._cursor_math_pos = QPointF(mx, my)
            self._update_trace_point(mx, my, pos)
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 0.85 if delta > 0 else 1.18
        mouse_math_x, mouse_math_y = self.pixel_to_math(event.position().x(), event.position().y())
        self.zoom(factor, center_x=mouse_math_x, center_y=mouse_math_y)

    def _update_trace_point(self, mx: float, my: float, pixel_pos: QPoint):
        if not self._trace_active or not self.functions:
            self._active_trace_point = None
            return

        best_dist = 40.0  # Threshold in pixels
        best_point = None

        for idx, fn in enumerate(self.functions):
            if not fn.is_visible or not fn.compiled_code:
                continue

            y_val = fn.evaluate(mx, self.parameters)
            if y_val is not None:
                pt_px = self.math_to_pixel(mx, y_val)
                dist = abs(pt_px.y() - pixel_pos.y())
                if dist < best_dist:
                    best_dist = dist
                    func_name = f"f{idx+1}(x)" if len(self.functions) > 1 else "f(x)"
                    best_point = (mx, y_val, func_name, fn.color)

        self._active_trace_point = best_point
        if best_point:
            self.tracePointChanged.emit(best_point[0], best_point[1], best_point[2])

    # ─── PAINTING / RENDERING ────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Background
        painter.fillRect(self.rect(), QColor(self.theme_colors["bg"]))

        # 2. Cartesian Grid & Axes
        self._draw_grid_and_axes(painter)

        # 3. Mathematical Curves
        self._draw_functions(painter)

        # 4. Key Landmarks (Roots and y-intercept)
        self._draw_key_points(painter)

        # 5. Interactive Trace Marker & Coordinate Pill
        if self._active_trace_point:
            self._draw_trace_hud(painter, self._active_trace_point)

    def _calculate_nice_step(self, raw_step: float) -> float:
        """Finds clean human-readable step intervals: 1, 2, 5 * 10^k."""
        if raw_step <= 0:
            return 1.0
        exp = math.floor(math.log10(raw_step))
        frac = raw_step / (10 ** exp)
        if frac < 1.5:
            nice = 1.0
        elif frac < 3.0:
            nice = 2.0
        elif frac < 7.0:
            nice = 5.0
        else:
            nice = 10.0
        return nice * (10 ** exp)

    def _draw_grid_and_axes(self, painter: QPainter):
        w = self.width()
        h = self.height()

        x_span = self.x_max - self.x_min
        y_span = self.y_max - self.y_min

        # Compute optimal step sizes
        step_x = self._calculate_nice_step(x_span / 8.0)
        step_y = self._calculate_nice_step(y_span / 8.0)

        pen_major = QPen(QColor(self.theme_colors["grid_major"]), 1)
        pen_minor = QPen(QColor(self.theme_colors["grid_minor"]), 1)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        # ─── VERTICAL GRID LINES ─────────────────────────────────────
        first_x = math.floor(self.x_min / step_x) * step_x
        curr_x = first_x
        while curr_x <= self.x_max:
            px = self.math_to_pixel(curr_x, 0).x()
            painter.setPen(pen_major)
            painter.drawLine(QPointF(px, 0), QPointF(px, h))

            # Numerical Label along bottom or axis
            if abs(curr_x) > 1e-6:
                lbl = f"{curr_x:.4g}"
                painter.setPen(QColor(self.theme_colors["text"]))
                axis_y = self.math_to_pixel(0, 0).y()
                # Place label near x-axis if on screen, else near bottom
                text_y = min(max(axis_y + 14, 16), h - 6)
                painter.drawText(int(px + 4), int(text_y), lbl)

            curr_x += step_x

        # ─── HORIZONTAL GRID LINES ───────────────────────────────────
        first_y = math.floor(self.y_min / step_y) * step_y
        curr_y = first_y
        while curr_y <= self.y_max:
            py = self.math_to_pixel(0, curr_y).y()
            painter.setPen(pen_major)
            painter.drawLine(QPointF(0, py), QPointF(w, py))

            # Numerical Label along y-axis
            if abs(curr_y) > 1e-6:
                lbl = f"{curr_y:.4g}"
                painter.setPen(QColor(self.theme_colors["text"]))
                axis_x = self.math_to_pixel(0, 0).x()
                text_x = min(max(axis_x + 6, 6), w - 40)
                painter.drawText(int(text_x), int(py - 4), lbl)

            curr_y += step_y

        # ─── PRIMARY AXES (X=0 and Y=0) ──────────────────────────────
        pen_axis = QPen(QColor(self.theme_colors["axis"]), 2)
        painter.setPen(pen_axis)

        # X-Axis line
        origin_pt = self.math_to_pixel(0, 0)
        ox, oy = origin_pt.x(), origin_pt.y()

        if 0 <= oy <= h:
            painter.drawLine(QPointF(0, oy), QPointF(w, oy))
        if 0 <= ox <= w:
            painter.drawLine(QPointF(ox, 0), QPointF(ox, h))

        # Origin '0' mark
        if 0 <= ox <= w and 0 <= oy <= h:
            painter.setPen(QColor(self.theme_colors["text"]))
            painter.drawText(int(ox - 14), int(oy + 14), "0")

    def _draw_functions(self, painter: QPainter):
        for fn in self.functions:
            if not fn.is_visible or not fn.compiled_code:
                continue

            segments = fn.evaluate_range(self.x_min, self.x_max, num_points=700, params=self.parameters)
            pen_curve = QPen(QColor(fn.color), getattr(self, "curve_line_width", 2.5))
            pen_curve.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen_curve.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen_curve)

            for seg in segments:
                if len(seg) < 2:
                    continue
                path = QPainterPath()
                first = self.math_to_pixel(seg[0][0], seg[0][1])
                path.moveTo(first)
                for x, y in seg[1:]:
                    pt = self.math_to_pixel(x, y)
                    path.lineTo(pt)
                painter.drawPath(path)

    def _draw_key_points(self, painter: QPainter):
        """Draws highlighted landmark circles at critical points (Roots and y-intercept)."""
        painter.setBrush(QBrush(QColor("#FFFFFF")))

        for fn in self.functions:
            if not fn.is_visible or not fn.compiled_code:
                continue

            features = fn.find_key_features(self.x_min, self.x_max, params=self.parameters)

            # Roots (x-intercepts)
            pen_root = QPen(QColor(fn.color), 2)
            painter.setPen(pen_root)
            for rx, ry in features.get("roots", []):
                pt = self.math_to_pixel(rx, ry)
                painter.drawEllipse(pt, 4.0, 4.0)

            # y-intercept
            y_int = features.get("y_intercept")
            if y_int:
                pt = self.math_to_pixel(y_int[0], y_int[1])
                painter.drawEllipse(pt, 4.0, 4.0)

    def _draw_trace_hud(self, painter: QPainter, trace_point: Tuple[float, float, str, str]):
        x_val, y_val, label, color_hex = trace_point
        pt_px = self.math_to_pixel(x_val, y_val)

        # 1. Snapped glowing marker dot
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.drawEllipse(pt_px, 5.5, 5.5)

        # 2. Sleek Floating Coordinate Tooltip Pill
        coord_text = f"{label}: ({x_val:.3g}, {y_val:.3g})"
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        txt_w = fm.horizontalAdvance(coord_text) + 16
        txt_h = 24

        pill_x = min(max(pt_px.x() - txt_w / 2.0, 10), self.width() - txt_w - 10)
        pill_y = pt_px.y() - 34
        if pill_y < 40:
            pill_y = pt_px.y() + 14

        pill_rect = QRectF(pill_x, pill_y, txt_w, txt_h)
        painter.setPen(QPen(QColor(self.theme_colors["hud_border"]), 1))
        painter.setBrush(QBrush(QColor(self.theme_colors["hud_bg"])))
        painter.drawRoundedRect(pill_rect, 5.0, 5.0)

        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, coord_text)

