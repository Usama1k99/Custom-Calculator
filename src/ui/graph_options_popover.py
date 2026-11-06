"""
Graph Options Popover Overlay.
Matches Windows Calculator Graphing settings:
- Window: X-Min, X-Max, Y-Min, Y-Max, Reset view
- Units: Radians, Degrees, Gradians segmented switch
- Line thickness: Thin (1.5px), Medium (2.5px), Thick (4.0px)
- Graph theme: Always light / Match app theme with vibrant accent radio indicators
Zero emojis across all UI elements.
"""

from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QButtonGroup, QComboBox
)
from src.ui.mode_icons import get_themed_icon, get_themed_svg_path


class GraphOptionsPopover(QFrame):
    """Floating Graph options overlay matching Windows Calculator Graphing settings."""
    optionsChanged = pyqtSignal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent or canvas)
        self.canvas = canvas
        self.setObjectName("GraphOptionsCard")
        self.setFixedSize(310, 430)
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._tokens: Dict[str, str] = {}

        self._init_ui()
        self._apply_popover_styles()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        # ─── 1. TITLE ROW ────────────────────────────────────────────
        header_row = QHBoxLayout()
        self.title_lbl = QLabel("Graph options")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        header_row.addWidget(self.title_lbl, stretch=1)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.setIcon(get_themed_icon("Close", "#AAAAAA", size=12))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self.close_btn.clicked.connect(lambda: self.setVisible(False))
        header_row.addWidget(self.close_btn)
        layout.addLayout(header_row)

        # ─── 2. WINDOW BOUNDS (X-Min, X-Max, Y-Min, Y-Max) ───────────
        win_hdr = QHBoxLayout()
        self.win_lbl = QLabel("Window")
        self.win_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #CCCCCC;")
        win_hdr.addWidget(self.win_lbl, stretch=1)

        self.reset_btn = QPushButton("Reset view")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #38BDF8;
                font-size: 11px;
                font-weight: 500;
                padding: 0;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.reset_btn.clicked.connect(self._reset_view)
        win_hdr.addWidget(self.reset_btn)
        layout.addLayout(win_hdr)

        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(10)

        lbl_style = "font-size: 11px; color: #CCCCCC; font-weight: 600;"
        input_style = """
            QLineEdit {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 4px;
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 8px;
                min-height: 24px;
            }
            QLineEdit:focus {
                border-color: #38BDF8;
            }
        """

        self.lbl_xmin = QLabel("X-Min")
        self.lbl_xmin.setStyleSheet(lbl_style)
        grid.addWidget(self.lbl_xmin, 0, 0)
        self.xmin_input = QLineEdit(f"{self.canvas.x_min:.5g}")
        self.xmin_input.setStyleSheet(input_style)
        self.xmin_input.editingFinished.connect(self._apply_bounds)
        grid.addWidget(self.xmin_input, 1, 0)

        self.lbl_xmax = QLabel("X-Max")
        self.lbl_xmax.setStyleSheet(lbl_style)
        grid.addWidget(self.lbl_xmax, 0, 1)
        self.xmax_input = QLineEdit(f"{self.canvas.x_max:.5g}")
        self.xmax_input.setStyleSheet(input_style)
        self.xmax_input.editingFinished.connect(self._apply_bounds)
        grid.addWidget(self.xmax_input, 1, 1)

        self.lbl_ymin = QLabel("Y-Min")
        self.lbl_ymin.setStyleSheet(lbl_style)
        grid.addWidget(self.lbl_ymin, 2, 0)
        self.ymin_input = QLineEdit(f"{self.canvas.y_min:.5g}")
        self.ymin_input.setStyleSheet(input_style)
        self.ymin_input.editingFinished.connect(self._apply_bounds)
        grid.addWidget(self.ymin_input, 3, 0)

        self.lbl_ymax = QLabel("Y-Max")
        self.lbl_ymax.setStyleSheet(lbl_style)
        grid.addWidget(self.lbl_ymax, 2, 1)
        self.ymax_input = QLineEdit(f"{self.canvas.y_max:.5g}")
        self.ymax_input.setStyleSheet(input_style)
        self.ymax_input.editingFinished.connect(self._apply_bounds)
        grid.addWidget(self.ymax_input, 3, 1)

        layout.addLayout(grid)

        # ─── 3. UNITS (RADIANS, DEGREES, GRADIANS) ───────────────────
        self.units_lbl = QLabel("Units")
        self.units_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #CCCCCC; margin-top: 4px;")
        layout.addWidget(self.units_lbl)

        units_row = QHBoxLayout()
        units_row.setSpacing(4)
        self.unit_btns = {}
        for unit_name in ("Radians", "Degrees", "Gradians"):
            btn = QPushButton(unit_name)
            btn.setCheckable(True)
            btn.setChecked(unit_name == "Radians")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 4px;
                    color: #DDDDDD;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 5px 0;
                }
                QPushButton:checked {
                    background: rgba(56, 189, 248, 0.25);
                    border-color: #38BDF8;
                    color: #38BDF8;
                    font-weight: 600;
                }
            """)
            btn.clicked.connect(lambda _, u=unit_name: self._on_unit_selected(u))
            units_row.addWidget(btn)
            self.unit_btns[unit_name] = btn

        layout.addLayout(units_row)

        # ─── 4. LINE THICKNESS ───────────────────────────────────────
        self.thick_lbl = QLabel("Line thickness")
        self.thick_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #CCCCCC; margin-top: 4px;")
        layout.addWidget(self.thick_lbl)

        self.thick_combo = QComboBox()
        self.thick_combo.setObjectName("ThickCombo")
        self.thick_combo.addItems(["Thin (1.5px)", "Medium (2.5px)", "Thick (4.0px)"])
        self.thick_combo.setCurrentIndex(1)
        self.thick_combo.currentIndexChanged.connect(self._on_thickness_changed)
        layout.addWidget(self.thick_combo)

        # ─── 5. GRAPH THEME (ALWAYS LIGHT / MATCH APP THEME) ─────────
        self.theme_lbl = QLabel("Graph theme")
        self.theme_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #CCCCCC; margin-top: 4px;")
        layout.addWidget(self.theme_lbl)

        self.radio_match_app = QRadioButton("Match app theme")
        self.radio_match_app.setChecked(True)
        self.radio_match_app.toggled.connect(self._on_theme_toggled)

        self.radio_always_light = QRadioButton("Always light")
        self.radio_always_light.toggled.connect(self._on_theme_toggled)

        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.radio_always_light)
        self.theme_group.addButton(self.radio_match_app)

        layout.addWidget(self.radio_always_light)
        layout.addWidget(self.radio_match_app)

    def set_theme_tokens(self, tokens: Dict[str, str]):
        self._tokens = dict(tokens)
        self._apply_popover_styles()

    def _apply_popover_styles(self):
        t = self._tokens
        accent = t.get("accent_primary", "#38BDF8")
        bg_card = t.get("bg_surface", "rgba(28, 28, 30, 0.96)")
        border_col = t.get("border_subtle", "rgba(255, 255, 255, 0.15)")
        text_pri = t.get("text_primary", "#FFFFFF")
        text_sec = t.get("text_secondary", "#CCCCCC")

        chevron_down_path = get_themed_svg_path("ChevronDown", text_sec)
        self.setStyleSheet(f"""
            QFrame#GraphOptionsCard {{
                background-color: {bg_card};
                border: 1px solid {border_col};
                border-radius: 8px;
            }}
            QComboBox#ThickCombo {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid {border_col};
                border-radius: 4px;
                color: {text_pri};
                font-size: 11px;
                padding: 4px 24px 4px 8px;
            }}
            QComboBox#ThickCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }}
            QComboBox#ThickCombo::down-arrow {{
                image: url({chevron_down_path});
                width: 10px;
                height: 10px;
            }}
            QRadioButton {{
                color: {text_pri};
                font-size: 12px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid rgba(255, 255, 255, 0.35);
                background: rgba(255, 255, 255, 0.08);
            }}
            QRadioButton::indicator:checked {{
                background-color: {accent};
                border: 3px solid #1C1C1E;
            }}
        """)

        if hasattr(self, "close_btn"):
            self.close_btn.setIcon(get_themed_icon("Close", text_sec, size=12))

    def _reset_view(self):
        self.canvas.reset_view()
        self.update_displayed_bounds()

    def update_displayed_bounds(self):
        self.xmin_input.setText(f"{self.canvas.x_min:.5g}")
        self.xmax_input.setText(f"{self.canvas.x_max:.5g}")
        self.ymin_input.setText(f"{self.canvas.y_min:.5g}")
        self.ymax_input.setText(f"{self.canvas.y_max:.5g}")

    def _apply_bounds(self):
        try:
            xmin = float(self.xmin_input.text().strip())
            xmax = float(self.xmax_input.text().strip())
            ymin = float(self.ymin_input.text().strip())
            ymax = float(self.ymax_input.text().strip())
            if xmin < xmax and ymin < ymax:
                self.canvas.x_min = xmin
                self.canvas.x_max = xmax
                self.canvas.y_min = ymin
                self.canvas.y_max = ymax
                self.canvas.update()
                self.optionsChanged.emit()
        except ValueError:
            pass

    def _on_unit_selected(self, selected_unit: str):
        for name, btn in self.unit_btns.items():
            btn.setChecked(name == selected_unit)
        self.optionsChanged.emit()

    def _on_thickness_changed(self, idx: int):
        thickness_map = {0: 1.5, 1: 2.5, 2: 4.0}
        self.canvas.curve_line_width = thickness_map.get(idx, 2.5)
        self.canvas.update()

    def _on_theme_toggled(self):
        self.canvas.always_light = self.radio_always_light.isChecked()
        self.canvas.update_theme()
