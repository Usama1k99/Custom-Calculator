"""
Complete Windows Calculator-Style Graphing View Container.
Combines:
- Responsive Dual-Pane & Mobile Tabbed Layout:
  * When window width >= 680px: Graph Canvas on left, Function Writing Mode & Keypad on right.
  * When window width < 680px: Seamless top switcher [ Graph ] | [ Functions ].
- Multi-function Equation Deck with colored badges (f₁, f₂, ...) and active card selection
- Full Graphing Keypad with Trigonometry, Inequalities, and Functions dropdowns
- Interactive Graph Canvas (pan, zoom, trace coordinates HUD, Graph Options popover)
- Key Graph Features (KGF) analyzer: Roots, y-intercepts, and Extrema
- Dynamic parameter detection with interactive live sliders (e.g. m, b, a)
- Zero emojis across all UI elements.
"""

from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QScrollArea, QSlider, QStackedWidget
)
from src.core.graph_engine import GraphFunction
from src.ui.graph_canvas import GraphCanvas, CURVE_PALETTE
from src.ui.graph_keypad import GraphKeypadWidget
from src.ui.mode_icons import get_themed_icon


class FunctionRowWidget(QFrame):
    """
    Equation card matching Windows Calculator Graphing card:
    - Colored badge on the left (e.g. [f₁], [f₂], or [f])
    - Equation input field
    - Visibility toggle (V) and Delete button (✕)
    - Active selection highlight
    """
    equationChanged = pyqtSignal()
    visibilityToggled = pyqtSignal()
    deleteRequested = pyqtSignal()
    focused = pyqtSignal()

    def __init__(self, index: int, initial_expr: str = "", color: str = "#38BDF8", parent=None):
        super().__init__(parent)
        self.index = index
        self.graph_fn = GraphFunction(initial_expr, color=color)
        self.setObjectName("FunctionCard")
        self.setProperty("is_active", False)
        self._current_text_color = "#FFFFFF"

        self._init_ui()

    def update_theme_icons(self, text_color: str):
        self._current_text_color = text_color
        if hasattr(self, "btn_vis"):
            c = text_color if self.graph_fn.is_visible else "#666666"
            icon_name = "Eye" if self.graph_fn.is_visible else "EyeOff"
            self.btn_vis.setIcon(get_themed_icon(icon_name, c, size=14))
        if hasattr(self, "btn_del"):
            self.btn_del.setIcon(get_themed_icon("Close", "#EF4444", size=12))

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Left Function Badge (e.g. f₁ or f)
        self.badge = QLabel(f"f{self.index+1}" if self.graph_fn.raw_expression else "f")
        self.badge.setObjectName("FunctionBadge")
        self.badge.setFixedSize(32, 32)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_badge_color()
        layout.addWidget(self.badge)

        # Function Label: f1(x) = (for backwards compatibility with existing tests)
        self.lbl_fn = QLabel(f"f{self.index+1}(x) =")
        self.lbl_fn.setVisible(False)
        layout.addWidget(self.lbl_fn)

        # Equation Text Field
        self.expr_input = QLineEdit(self.graph_fn.raw_expression)
        self.expr_input.setObjectName("FunctionExprInput")
        self.expr_input.setPlaceholderText("Enter an expression")
        self.expr_input.setStyleSheet("""
            QLineEdit#FunctionExprInput {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                font-weight: 500;
                padding: 2px 4px;
            }
        """)
        self.expr_input.textChanged.connect(self._on_text_changed)
        self.expr_input.mousePressEvent = lambda e: (self.focused.emit(), QLineEdit.mousePressEvent(self.expr_input, e))
        layout.addWidget(self.expr_input, stretch=1)

        # Visibility Toggle Button (Eye / EyeOff vector icon, zero emojis)
        self.btn_vis = QPushButton()
        self.btn_vis.setToolTip("Toggle Curve Visibility")
        self.btn_vis.setFixedSize(26, 26)
        self.btn_vis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vis.setIconSize(QSize(14, 14))
        icon_name = "Eye" if self.graph_fn.is_visible else "EyeOff"
        self.btn_vis.setIcon(get_themed_icon(icon_name, self._current_text_color, size=14))
        self.btn_vis.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.16); }
        """)
        self.btn_vis.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.btn_vis)

        # Delete Button (Close SVG vector icon, zero emojis)
        self.btn_del = QPushButton()
        self.btn_del.setToolTip("Remove Equation")
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setIconSize(QSize(12, 12))
        self.btn_del.setIcon(get_themed_icon("Close", "#EF4444", size=12))
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.25); }
        """)
        self.btn_del.clicked.connect(self.deleteRequested.emit)
        layout.addWidget(self.btn_del)

        self._apply_card_styles()

    def set_active(self, active: bool):
        self.setProperty("is_active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        if active:
            self.expr_input.setFocus()

    def _update_badge_color(self):
        c = self.graph_fn.color if self.graph_fn.raw_expression else "rgba(255, 255, 255, 0.12)"
        fg = "#FFFFFF" if self.graph_fn.raw_expression else "#AAAAAA"
        self.badge.setStyleSheet(f"""
            QLabel#FunctionBadge {{
                background-color: {c};
                color: {fg};
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                font-style: italic;
            }}
        """)

    def _apply_card_styles(self):
        self.setStyleSheet("""
            QFrame#FunctionCard {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QFrame#FunctionCard[is_active="true"] {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid #38BDF8;
            }
        """)

    def _on_text_changed(self, new_text: str):
        self.graph_fn = GraphFunction(new_text, color=self.graph_fn.color)
        self.badge.setText(f"f{self.index+1}" if new_text.strip() else "f")
        self._update_badge_color()
        self.equationChanged.emit()

    def _toggle_visibility(self):
        self.graph_fn.is_visible = not self.graph_fn.is_visible
        c = self._current_text_color if self.graph_fn.is_visible else "#666666"
        icon_name = "Eye" if self.graph_fn.is_visible else "EyeOff"
        self.btn_vis.setIcon(get_themed_icon(icon_name, c, size=14))
        self.btn_vis.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); border: none; border-radius: 4px; }"
            if self.graph_fn.is_visible else
            "QPushButton { background: rgba(255, 255, 255, 0.02); border: none; border-radius: 4px; }"
        )
        self.visibilityToggled.emit()


class GraphingView(QFrame):
    """
    Primary Graphing Mode View containing Interactive Canvas,
    Function Writing Deck, Keypad, and Key Graph Features (KGF).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GraphingView")
        self.parameter_values: Dict[str, float] = {}
        self.parameter_sliders: Dict[str, Tuple[QSlider, QLabel]] = {}
        self.function_rows: List[FunctionRowWidget] = []
        self.active_row_idx = 0

        self._init_ui()

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(4, 4, 4, 4)
        self.root_layout.setSpacing(4)

        # ─── 1. TOP MOBILE/NARROW MODE SELECTOR BAR (VISIBLE WHEN < 680PX) ───
        self.mode_selector_bar = QWidget()
        self.mode_selector_bar.setObjectName("GraphModeBar")
        bar_layout = QHBoxLayout(self.mode_selector_bar)
        bar_layout.setContentsMargins(4, 2, 4, 2)
        bar_layout.setSpacing(6)

        self.tab_btn_graph = QPushButton("Graph")
        self.tab_btn_graph.setCheckable(True)
        self.tab_btn_graph.setChecked(True)
        self.tab_btn_graph.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_btn_graph.clicked.connect(lambda: self._set_narrow_page(0))
        bar_layout.addWidget(self.tab_btn_graph)

        self.tab_btn_funcs = QPushButton("Edit Functions")
        self.tab_btn_funcs.setCheckable(True)
        self.tab_btn_funcs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_btn_funcs.clicked.connect(lambda: self._set_narrow_page(1))
        bar_layout.addWidget(self.tab_btn_funcs)

        bar_layout.addStretch()
        self.root_layout.addWidget(self.mode_selector_bar)

        # ─── 2. MAIN CONTAINER ───────────────────────────────────────
        self.body_container = QWidget()
        self.body_layout = QHBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)

        # ─── LEFT PANE: GRAPH CANVAS & KGF SUMMARY ───────────────────
        self.left_pane = QWidget()
        left_layout = QVBoxLayout(self.left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.canvas = GraphCanvas(self.left_pane)
        self.canvas.tracePointChanged.connect(self._on_trace_point_changed)
        left_layout.addWidget(self.canvas, stretch=1)

        # Key Graph Features (KGF) Summary Card
        self.kgf_card = QFrame()
        self.kgf_card.setObjectName("KGFCard")
        kgf_layout = QVBoxLayout(self.kgf_card)
        kgf_layout.setContentsMargins(8, 4, 8, 4)
        kgf_layout.setSpacing(2)

        kgf_header = QHBoxLayout()
        kgf_title = QLabel("KEY GRAPH FEATURES")
        kgf_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #888; letter-spacing: 0.6px;")
        kgf_header.addWidget(kgf_title, stretch=1)

        self.btn_kgf_toggle = QPushButton("Details")
        self.btn_kgf_toggle.setCheckable(True)
        self.btn_kgf_toggle.setChecked(True)
        self.btn_kgf_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kgf_toggle.setStyleSheet("font-size: 10px; color: #38BDF8; background: transparent; border: none;")
        self.btn_kgf_toggle.clicked.connect(self._toggle_kgf_panel)
        kgf_header.addWidget(self.btn_kgf_toggle)
        kgf_layout.addLayout(kgf_header)

        self.kgf_details = QLabel("Roots: none | y-intercept: none")
        self.kgf_details.setStyleSheet("font-size: 11px; color: #DDD;")
        self.kgf_details.setWordWrap(True)
        kgf_layout.addWidget(self.kgf_details)

        left_layout.addWidget(self.kgf_card)
        self.body_layout.addWidget(self.left_pane, stretch=1)

        # ─── RIGHT PANE: FUNCTION WRITING DECK & KEYPAD ───────────────
        self.right_pane = QWidget()
        self.right_pane.setObjectName("GraphRightPane")
        self.right_pane.setMinimumWidth(310)
        self.right_pane.setMaximumWidth(400)
        right_layout = QVBoxLayout(self.right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Deck Container for Cards
        self.deck_container = QFrame()
        self.deck_container.setObjectName("EquationDeck")
        deck_v = QVBoxLayout(self.deck_container)
        deck_v.setContentsMargins(4, 4, 4, 4)
        deck_v.setSpacing(4)

        # Cards Scroll Area
        self.fn_scroll = QScrollArea()
        self.fn_scroll.setWidgetResizable(True)
        self.fn_scroll.setFixedHeight(120)
        self.fn_scroll.setStyleSheet("background: transparent; border: none;")

        self.fn_container = QWidget()
        self.fn_layout = QVBoxLayout(self.fn_container)
        self.fn_layout.setContentsMargins(0, 0, 0, 0)
        self.fn_layout.setSpacing(4)
        self.fn_layout.addStretch()

        self.fn_scroll.setWidget(self.fn_container)
        deck_v.addWidget(self.fn_scroll)

        # Add Function Button
        add_row = QHBoxLayout()
        self.btn_add_fn = QPushButton("+ Add Function")
        self.btn_add_fn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_fn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 5px 12px;
                color: #DDD;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.14); color: #FFF; }
        """)
        self.btn_add_fn.clicked.connect(lambda: self._add_function_row(""))
        add_row.addWidget(self.btn_add_fn)
        add_row.addStretch()
        deck_v.addLayout(add_row)

        # Dynamic Parameter Sliders Container
        self.sliders_container = QWidget()
        self.sliders_layout = QVBoxLayout(self.sliders_container)
        self.sliders_layout.setContentsMargins(0, 2, 0, 0)
        self.sliders_layout.setSpacing(4)
        self.sliders_container.setVisible(False)
        deck_v.addWidget(self.sliders_container)

        right_layout.addWidget(self.deck_container)

        # Graph Keypad Grid
        self.keypad = GraphKeypadWidget(self.right_pane)
        self.keypad.insertToken.connect(self._on_keypad_token)
        self.keypad.backspaceClicked.connect(self._on_keypad_backspace)
        self.keypad.clearClicked.connect(self._on_keypad_clear)
        self.keypad.enterClicked.connect(self._on_keypad_enter)
        right_layout.addWidget(self.keypad, stretch=1)

        self.body_layout.addWidget(self.right_pane)
        self.root_layout.addWidget(self.body_container, stretch=1)

        # Initial seed equation
        self._add_function_row("x^2 - 4")
        self._apply_theme_styles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _update_responsive_layout(self):
        """
        Responsive adaptation:
        If window width >= 500px: Side-by-side (Canvas on left, Functions + Keypad on right).
        If window width < 500px: Tabbed switcher at top, showing one view at a time.
        """
        w = self.width()
        if w >= 500:
            self.mode_selector_bar.setVisible(False)
            self.left_pane.setVisible(True)
            self.right_pane.setVisible(True)
        else:
            self.mode_selector_bar.setVisible(True)
            if self.tab_btn_graph.isChecked():
                self.left_pane.setVisible(True)
                self.right_pane.setVisible(False)
            else:
                self.left_pane.setVisible(False)
                self.right_pane.setVisible(True)

    def _set_narrow_page(self, page_idx: int):
        self.tab_btn_graph.setChecked(page_idx == 0)
        self.tab_btn_funcs.setChecked(page_idx == 1)
        self._update_responsive_layout()

    def _add_function_row(self, initial_expr: str = "") -> FunctionRowWidget:
        if len(self.function_rows) >= 6:
            return self.function_rows[-1]

        idx = len(self.function_rows)
        color = CURVE_PALETTE[idx % len(CURVE_PALETTE)]
        row = FunctionRowWidget(idx, initial_expr=initial_expr, color=color, parent=self)
        row.equationChanged.connect(self._recompute_and_redraw)
        row.visibilityToggled.connect(self._recompute_and_redraw)
        row.deleteRequested.connect(lambda r=row: self._remove_function_row(r))
        row.focused.connect(lambda r=row: self._set_active_row(r))

        self.function_rows.append(row)
        self.fn_layout.insertWidget(self.fn_layout.count() - 1, row)

        self._set_active_row(row)
        self._recompute_and_redraw()
        return row

    def _remove_function_row(self, row: FunctionRowWidget):
        if row in self.function_rows:
            self.function_rows.remove(row)
            row.deleteLater()

            # Re-index remaining rows
            for i, r in enumerate(self.function_rows):
                r.index = i
                r.lbl_fn.setText(f"f{i+1}(x) =")
                r.badge.setText(f"f{i+1}" if r.graph_fn.raw_expression else "f")
                r._update_badge_color()

            if self.function_rows:
                self._set_active_row(self.function_rows[-1])
            else:
                # Always maintain at least one equation card
                self._add_function_row("")

            self._recompute_and_redraw()

    def _set_active_row(self, target_row: FunctionRowWidget):
        for idx, row in enumerate(self.function_rows):
            is_target = (row == target_row)
            row.set_active(is_target)
            if is_target:
                self.active_row_idx = idx

    def _get_active_row(self) -> Optional[FunctionRowWidget]:
        if 0 <= self.active_row_idx < len(self.function_rows):
            return self.function_rows[self.active_row_idx]
        if self.function_rows:
            return self.function_rows[0]
        return None

    def _on_keypad_token(self, token: str):
        row = self._get_active_row()
        if row:
            curr = row.expr_input.text()
            pos = row.expr_input.cursorPosition()
            new_text = curr[:pos] + token + curr[pos:]
            row.expr_input.setText(new_text)
            row.expr_input.setCursorPosition(pos + len(token))

    def _on_keypad_backspace(self):
        row = self._get_active_row()
        if row:
            curr = row.expr_input.text()
            pos = row.expr_input.cursorPosition()
            if pos > 0:
                new_text = curr[:pos-1] + curr[pos:]
                row.expr_input.setText(new_text)
                row.expr_input.setCursorPosition(pos - 1)

    def _on_keypad_clear(self):
        row = self._get_active_row()
        if row:
            row.expr_input.clear()

    def _on_keypad_enter(self):
        self._recompute_and_redraw()
        # If active row has an expression, automatically add a blank row ready for next formula
        row = self._get_active_row()
        if row and row.graph_fn.raw_expression.strip():
            # Check if there's already an empty row
            empty_row = next((r for r in self.function_rows if not r.graph_fn.raw_expression.strip()), None)
            if not empty_row and len(self.function_rows) < 6:
                self._add_function_row("")

    def _recompute_and_redraw(self):
        active_fns = [r.graph_fn for r in self.function_rows]
        self.canvas.set_functions(active_fns)

        all_params = set()
        for fn in active_fns:
            all_params.update(fn.parameters)

        self._update_parameter_sliders(all_params)
        self._update_kgf_summary()

    def _update_parameter_sliders(self, detected_params: set):
        for param in list(self.parameter_sliders.keys()):
            if param not in detected_params:
                slider, lbl = self.parameter_sliders.pop(param)
                slider.parent().deleteLater()
                if param in self.parameter_values:
                    del self.parameter_values[param]

        for param in detected_params:
            if param not in self.parameter_sliders:
                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(4, 2, 4, 2)
                row.setSpacing(6)

                lbl = QLabel(f"{param} = 1.0")
                lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #38BDF8; min-width: 60px;")
                row.addWidget(lbl)

                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(-100, 100)
                slider.setValue(10)
                slider.valueChanged.connect(lambda val, p=param, l=lbl: self._on_slider_changed(p, val, l))
                row.addWidget(slider, stretch=1)

                self.sliders_layout.addWidget(row_widget)
                self.parameter_sliders[param] = (slider, lbl)
                self.parameter_values[param] = 1.0

        self.sliders_container.setVisible(bool(detected_params))
        self.canvas.set_parameters(self.parameter_values)

    def _on_slider_changed(self, param: str, int_val: int, label: QLabel):
        float_val = int_val / 10.0
        self.parameter_values[param] = float_val
        label.setText(f"{param} = {float_val:.1f}")
        self.canvas.set_parameters(self.parameter_values)

    def _toggle_kgf_panel(self):
        visible = self.btn_kgf_toggle.isChecked()
        self.kgf_card.setVisible(visible)

    def _on_trace_point_changed(self, x: float, y: float, func_label: str):
        self.kgf_details.setText(f"Trace HUD: {func_label} at x = {x:.4g}, y = {y:.4g}")

    def _update_kgf_summary(self):
        active_fns = [r.graph_fn for r in self.function_rows if r.graph_fn.is_visible and r.graph_fn.compiled_code]
        if not active_fns:
            self.kgf_details.setText("Roots: none | y-intercept: none")
            return

        first_fn = active_fns[0]
        features = first_fn.find_key_features(self.canvas.x_min, self.canvas.x_max, params=self.parameter_values)
        roots = features.get("roots", [])
        y_int = features.get("y_intercept")

        roots_fmt = []
        for r in roots[:4]:
            val = r[0] if isinstance(r, (tuple, list)) else r
            roots_fmt.append(f"{val:.3g}")
        roots_str = ", ".join(roots_fmt) if roots_fmt else "none"
        if y_int is not None and isinstance(y_int, tuple):
            y_str = f"{y_int[1]:.3g}"
        else:
            y_str = "none"

        fn_name = f"f1(x)" if len(active_fns) > 1 else "f(x)"
        self.kgf_details.setText(f"{fn_name} | Roots: [{roots_str}] | y-intercept: {y_str}")

    def set_theme_tokens(self, tokens: Dict[str, str]):
        self.canvas.set_theme_tokens(tokens)
        text_color = tokens.get("text_primary", "#FFFFFF")
        self.keypad.update_theme_icons(text_color)
        for row in self.function_rows:
            row.update_theme_icons(text_color)
        self._apply_theme_styles(tokens)

    def _apply_theme_styles(self, tokens: Optional[Dict[str, str]] = None):
        t = tokens or {}
        bg_card = t.get("bg_card", "rgba(255, 255, 255, 0.05)")
        border_subtle = t.get("border_subtle", "rgba(255, 255, 255, 0.1)")
        accent = t.get("accent_primary", "#38BDF8")

        self.setStyleSheet(f"""
            QFrame#GraphingView {{
                background-color: transparent;
                border: none;
            }}
            QFrame#EquationDeck {{
                background-color: {bg_card};
                border: 1px solid {border_subtle};
                border-radius: 6px;
            }}
            QFrame#KGFCard {{
                background-color: {bg_card};
                border: 1px solid {border_subtle};
                border-radius: 6px;
            }}
            QWidget#GraphModeBar QPushButton {{
                background-color: {bg_card};
                border: 1px solid {border_subtle};
                border-radius: 4px;
                padding: 5px 14px;
                color: #CCC;
                font-size: 11px;
                font-weight: 600;
            }}
            QWidget#GraphModeBar QPushButton:checked {{
                background-color: {accent};
                color: #000000;
                font-weight: 700;
            }}
            QFrame#SciFlyoutPanel {{
                background-color: {t.get('bg_surface', '#1E1F1C')};
                border: 1px solid {border_subtle};
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton.sciFlyoutKey {{
                background-color: {t.get('bg_card', '#383830')};
                color: {t.get('text_primary', '#FFFFFF')};
                border: 1px solid {border_subtle};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 1px 2px;
                min-height: 24px;
                max-height: 28px;
                min-width: 34px;
            }}
            QPushButton.sciFlyoutKey:hover {{
                background-color: {t.get('bg_card_hover', '#444444')};
                border-color: {accent};
                color: {t.get('text_primary', '#FFFFFF')};
            }}
            QPushButton.sciFlyoutKey:pressed {{
                background-color: {t.get('bg_card_active', '#555555')};
                border-color: {accent};
            }}
            QPushButton.sciFlyoutKey:checked {{
                background-color: {accent};
                color: {t.get('text_accent', '#FFFFFF')};
                border: 1px solid {accent};
                font-weight: 600;
            }}
            QPushButton.sciDropdownBtn {{
                background-color: transparent;
                color: {t.get('text_primary', '#FFFFFF')};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                text-align: left;
            }}
            QPushButton.sciDropdownBtn:hover {{
                background-color: {t.get('bg_card_hover', '#444444')};
                border-color: {border_subtle};
            }}
            QPushButton.sciDropdownBtn:checked {{
                background-color: {t.get('bg_card_active', '#555555')};
                color: {accent};
            }}
        """)
