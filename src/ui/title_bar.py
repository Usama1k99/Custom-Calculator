"""
Custom Windows Frameless Title Bar and Dialog Title Bar.
Replicates Windows 11 Fluent architecture with:
- Fluent icon glyphs (\uE921, \uE922/\uE923, \uE8BB)
- Window control hover/click highlights:
    * Minimize: Translucent Green on hover, Intense Green on click
    * Maximize: Translucent Yellow on hover, Intense Yellow on click
    * Close: Translucent Red on hover, Intense Red on click
- Support for Win32 Snap Layouts (HTMAXBUTTON) hover tracking
- Zero emojis across all UI elements
"""

from pathlib import Path
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QWidget, QDialog
)


def get_control_font() -> QFont:
    """Returns Segoe Fluent Icons or system fallback font."""
    font = QFont("Segoe Fluent Icons", 9)
    if not font.exactMatch():
        font = QFont("Segoe MDL2 Assets", 9)
        if not font.exactMatch():
            font = QFont("Segoe UI Symbol", 10)
            if not font.exactMatch():
                font = QFont("Segoe UI", 9)
    return font


TITLE_BUTTON_STYLES = """
    QFrame#CustomTitleBar, QWidget#dialogTitleBar {
        background-color: transparent;
        border: none;
    }
    QPushButton#winBtnMinimize,
    QPushButton#winBtnMaximize,
    QPushButton#winBtnClose {
        background-color: transparent;
        border: none;
        color: #888888;
        padding: 0px;
        margin: 0px;
    }

    /* ─── MINIMIZE: Translucent Green on Hover, Intense Green on Click ─── */
    QPushButton#winBtnMinimize:hover {
        background-color: rgba(34, 197, 94, 0.25);
        color: #22C55E;
    }
    QPushButton#winBtnMinimize:pressed {
        background-color: #22C55E;
        color: #000000;
    }

    /* ─── MAXIMIZE: Translucent Yellow on Hover, Intense Yellow on Click ─── */
    QPushButton#winBtnMaximize:hover,
    QPushButton#winBtnMaximize[hover="true"] {
        background-color: rgba(234, 179, 8, 0.28);
        color: #EAB308;
    }
    QPushButton#winBtnMaximize:pressed,
    QPushButton#winBtnMaximize[pressed="true"] {
        background-color: #EAB308;
        color: #000000;
    }

    /* ─── CLOSE: Translucent Red on Hover, Intense Red on Click ─── */
    QPushButton#winBtnClose:hover {
        background-color: rgba(239, 68, 68, 0.35);
        color: #FFFFFF;
    }
    QPushButton#winBtnClose:pressed {
        background-color: #EF4444;
        color: #FFFFFF;
    }
"""


class CustomTitleBar(QFrame):
    """Main window title bar with native resizing, dragging, and Win32 controls."""

    def __init__(self, parent_window: QWidget, title: str = "Calculator"):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(34)
        self._drag_pos = QPoint()

        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(6)

        # App Icon
        icon_path = Path("assets") / "icons" / "app_icon.ico"
        icon_svg = Path("assets") / "icons" / "app_icon.svg"
        if icon_svg.exists():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon(str(icon_svg)).pixmap(16, 16))
            icon_lbl.setFixedSize(16, 16)
            layout.addWidget(icon_lbl)
        elif icon_path.exists():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon(str(icon_path)).pixmap(16, 16))
            icon_lbl.setFixedSize(16, 16)
            layout.addWidget(icon_lbl)

        # Title Label
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #888888; background: transparent;")
        self.title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_lbl)

        layout.addStretch()

        # Window Control Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(0)

        ctrl_font = get_control_font()

        # 1. Minimize: Translucent Green Hover, Intense Green Click
        self.btn_minimize = QPushButton("\uE921", self)
        self.btn_minimize.setFont(ctrl_font)
        self.btn_minimize.setObjectName("winBtnMinimize")
        self.btn_minimize.setFixedSize(46, 34)
        self.btn_minimize.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_minimize.clicked.connect(self.parent_window.showMinimized)
        btn_box.addWidget(self.btn_minimize)

        # 2. Maximize: Translucent Yellow Hover, Intense Yellow Click
        self.btn_maximize = QPushButton("\uE922", self)
        self.btn_maximize.setFont(ctrl_font)
        self.btn_maximize.setObjectName("winBtnMaximize")
        self.btn_maximize.setFixedSize(46, 34)
        self.btn_maximize.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        btn_box.addWidget(self.btn_maximize)

        # 3. Close: Translucent Red Hover, Intense Red Click
        self.btn_close = QPushButton("\uE8BB", self)
        self.btn_close.setFont(ctrl_font)
        self.btn_close.setObjectName("winBtnClose")
        self.btn_close.setFixedSize(46, 34)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.clicked.connect(self.parent_window.close)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)
        self.setStyleSheet(TITLE_BUTTON_STYLES)

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_maximize.setText("\uE922")  # Square
        else:
            self.parent_window.showMaximized()
            self.btn_maximize.setText("\uE923")  # Restore overlapping squares

    def set_btn_maximize_hover(self, hover: bool):
        curr = bool(self.btn_maximize.property("hover"))
        if curr != hover:
            self.btn_maximize.setProperty("hover", hover)
            self.btn_maximize.style().unpolish(self.btn_maximize)
            self.btn_maximize.style().polish(self.btn_maximize)

    def set_btn_maximize_pressed(self, pressed: bool):
        curr = bool(self.btn_maximize.property("pressed"))
        if curr != pressed:
            self.btn_maximize.setProperty("pressed", pressed)
            self.btn_maximize.style().unpolish(self.btn_maximize)
            self.btn_maximize.style().polish(self.btn_maximize)

    # Mouse events for dragging on non-Win32 fallback
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            wh = self.parent_window.windowHandle()
            if wh:
                wh.startSystemMove()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag_pos") and event.buttons() & Qt.MouseButton.LeftButton and not self.parent_window.isMaximized():
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()


class DialogTitleBar(QWidget):
    """Frameless custom title bar for modal dialogs matching MainWindow window controls."""

    def __init__(self, parent_dialog: QDialog, title: str = "", icon_path: str = None):
        super().__init__(parent_dialog)
        self.dialog = parent_dialog
        self.setObjectName("dialogTitleBar")
        self.setFixedHeight(36)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        # App / Dialog Icon
        if icon_path and Path(icon_path).exists():
            lbl_icon = QLabel(self)
            lbl_icon.setPixmap(QIcon(icon_path).pixmap(16, 16))
            lbl_icon.setFixedSize(16, 16)
            lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(lbl_icon)

        # Title Label
        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 500; background: transparent;")
        self.lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_title)

        layout.addStretch(1)

        # Close Button: Translucent Red on Hover, Intense Red on Click
        ctrl_font = get_control_font()
        self.btn_close = QPushButton("\uE8BB", self)
        self.btn_close.setFont(ctrl_font)
        self.btn_close.setObjectName("winBtnClose")
        self.btn_close.setFixedSize(46, 36)
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self.dialog.reject)
        layout.addWidget(self.btn_close)

        self.setStyleSheet(TITLE_BUTTON_STYLES)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            wh = self.dialog.windowHandle()
            if wh:
                wh.startSystemMove()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.dialog.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.dialog.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
