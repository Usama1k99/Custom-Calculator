"""
Windows Calculator-Style Navigation Sidebar Drawer.
Slides out from the left upon clicking the hamburger menu button (☰).
Provides one-click navigation between Calculator modes and Unit Converters. Zero emojis.
"""

from pathlib import Path
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget
)
from src.ui.mode_icons import get_themed_icon


class NavButton(QPushButton):
    """Sidebar navigation item with Windows 11 Fluent middle-height left indicator when active."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setProperty("class", "navItem")
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._accent_color = "#3B82F6"

    def set_accent_color(self, color: str):
        self._accent_color = color
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        # Windows 11 Fluent indicator: pill in the middle portion of the left edge
        if self.property("class") == "navItemActive":
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            indicator_h = 16  # Middle portion only (not full top-to-bottom)
            indicator_w = 3
            y = (self.height() - indicator_h) // 2
            x = 3
            painter.setBrush(QColor(self._accent_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, indicator_w, indicator_h, 1.5, 1.5)


class NavigationSidebar(QFrame):
    modeSelected = pyqtSignal(str)
    themeSettingsRequested = pyqtSignal()
    closeRequested = pyqtSignal()

    def __init__(self, current_mode: str = "Standard", parent=None):
        super().__init__(parent)
        self.setObjectName("NavSidebar")
        self.setFixedWidth(260)
        self.current_mode = current_mode
        self._current_text_color = "#FFFFFF"
        self._current_accent_color = "#F92672"
        self._init_ui()

    def set_current_mode(self, mode: str):
        self.current_mode = mode
        self._update_active_buttons()

    def update_theme_icons(self, text_color: str, accent_color: str):
        self._current_text_color = text_color
        self._current_accent_color = accent_color
        if hasattr(self, "hamburger_btn"):
            self.hamburger_btn.setIcon(get_themed_icon("Hamburger", text_color, size=20))
            self.hamburger_btn.setIconSize(QSize(20, 20))
        self._update_active_buttons()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Header with close / hamburger button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(6, 4, 6, 4)
        top_row.setSpacing(4)

        self.hamburger_btn = QPushButton()
        self.hamburger_btn.setObjectName("HamburgerBtn")
        self.hamburger_btn.setFixedSize(36, 32)
        self.hamburger_btn.setIcon(get_themed_icon("Hamburger", self._current_text_color, size=20))
        self.hamburger_btn.setIconSize(QSize(20, 20))
        self.hamburger_btn.clicked.connect(self.closeRequested.emit)
        top_row.addWidget(self.hamburger_btn)

        app_title = QLabel("Calculator")
        app_title.setStyleSheet("font-size: 16px; font-weight: 600; padding-left: 4px;")
        top_row.addWidget(app_title, stretch=1)

        layout.addLayout(top_row)

        # Scrollable categories list with Windows 11 Fluent scrollbar
        scroll = QScrollArea()
        scroll.setObjectName("NavScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("NavScrollContainer")
        self.items_layout = QVBoxLayout(container)
        self.items_layout.setContentsMargins(4, 4, 4, 4)
        self.items_layout.setSpacing(2)

        self.buttons = {}

        # ─── SECTION 1: CALCULATOR MODES ─────────────────────────────
        calc_header = QLabel("Calculator")
        calc_header.setProperty("class", "sidebarCategory")
        self.items_layout.addWidget(calc_header)

        calc_modes = ["Standard", "Scientific", "Graphing", "Programmer", "Date Calculation"]
        for mode in calc_modes:
            btn = self._create_nav_button(mode)
            self.items_layout.addWidget(btn)

        # ─── SECTION 2: CONVERTERS (WINDOWS CALC SUITE) ──────────────
        conv_header = QLabel("Converter")
        conv_header.setProperty("class", "sidebarCategory")
        self.items_layout.addWidget(conv_header)

        converter_modes = [
            "Currency", "Volume", "Length", "Weight and Mass", "Temperature",
            "Energy", "Area", "Speed", "Time", "Power", "Data", "Pressure", "Angle"
        ]
        for mode in converter_modes:
            btn = self._create_nav_button(mode)
            self.items_layout.addWidget(btn)

        self.items_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # ─── SECTION 3: FOOTER SETTINGS WITH SUBTLE DIVIDER ─────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("SidebarSettingsDivider")
        layout.addWidget(sep)

        self.footer_btn = NavButton("  Settings")
        self.footer_btn.clicked.connect(self.themeSettingsRequested.emit)
        layout.addWidget(self.footer_btn)

        self._update_active_buttons()

    def _create_nav_button(self, mode: str) -> NavButton:
        btn = NavButton(f"  {mode}")
        btn.clicked.connect(lambda _, m=mode: self._on_item_clicked(m))
        self.buttons[mode] = btn
        return btn

    def _on_item_clicked(self, mode: str):
        self.current_mode = mode
        self._update_active_buttons()
        self.modeSelected.emit(mode)

    def _update_active_buttons(self):
        text_color = self._current_text_color
        accent_color = self._current_accent_color
        for mode, btn in self.buttons.items():
            is_active = (mode == self.current_mode)
            btn.set_accent_color(accent_color)
            btn.setProperty("class", "navItemActive" if is_active else "navItem")
            btn.setIcon(get_themed_icon(mode, accent_color if is_active else text_color, size=18))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if hasattr(self, "footer_btn"):
            self.footer_btn.setIcon(get_themed_icon("Settings", text_color, size=18))
            self.footer_btn.style().unpolish(self.footer_btn)
            self.footer_btn.style().polish(self.footer_btn)

