"""
Interactive Crash Report & Diagnostic Recovery Dialog for Apex Calculator.
Replicates modern Windows 11 Fluent design with:
- Custom title bar with translucent red close button
- Clear summary of the exception, mode, and input context that caused the crash
- Full scrollable monospace traceback viewer
- One-click copy of full diagnostic details to Windows clipboard
- Direct button to open the crash logs folder in Windows Explorer
- Clean restart or exit actions. Zero emojis across all UI elements.
"""

import os
from pathlib import Path
import subprocess
import sys
from PyQt6.QtCore import Qt, QTimer, QProcess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFrame, QWidget, QApplication
)
from src.ui.title_bar import DialogTitleBar
from src.ui.native_window import apply_dialog_rounded_corners
from src.ui.mode_icons import get_themed_icon


class CrashReportDialog(QDialog):
    """Modern frameless recovery modal presented when an unhandled exception occurs."""

    def __init__(
        self,
        exc_name: str,
        exc_msg: str,
        mode: str,
        active_token: str,
        report_path: str,
        full_report: str,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Apex Calculator - Unexpected Error")
        self.setFixedSize(560, 480)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("CrashReportDialog")

        self.exc_name = exc_name
        self.exc_msg = exc_msg
        self.mode = mode
        self.active_token = active_token
        self.report_path = report_path
        self.full_report = full_report

        self._init_ui()
        self._apply_styles()

    def showEvent(self, event):
        super().showEvent(event)
        apply_dialog_rounded_corners(self)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Custom Frameless Title Bar
        icon_path = Path("assets") / "icons" / "app_icon.svg"
        if not icon_path.exists():
            icon_path = Path("assets") / "icons" / "app_icon.ico"
        self.title_bar = DialogTitleBar(self, title="Apex Calculator - Error", icon_path=str(icon_path))
        root.addWidget(self.title_bar)

        # 2. Main Content Card
        content = QWidget()
        content.setObjectName("CrashContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("Apex Calculator encountered an unexpected error.")
        title_lbl.setObjectName("CrashTitle")
        layout.addWidget(title_lbl)

        # Subtitle
        desc_lbl = QLabel("A diagnostic crash report has been generated with full traceback and state context.")
        desc_lbl.setObjectName("CrashDesc")
        layout.addWidget(desc_lbl)

        # Key Context Box
        context_box = QFrame()
        context_box.setObjectName("CrashContextCard")
        ctx_layout = QVBoxLayout(context_box)
        ctx_layout.setContentsMargins(12, 10, 12, 10)
        ctx_layout.setSpacing(4)

        err_line = QLabel(f"<b>Error:</b> {self.exc_name}: {self.exc_msg or '(No message)'}")
        err_line.setObjectName("CrashErrLine")
        err_line.setWordWrap(True)
        ctx_layout.addWidget(err_line)

        mode_line = QLabel(f"<b>Triggering Mode:</b> {self.mode} &nbsp;|&nbsp; <b>Causing Input:</b> {self.active_token}")
        mode_line.setObjectName("CrashMetaLine")
        ctx_layout.addWidget(mode_line)

        path_line = QLabel(f"<b>Report Location:</b> {self.report_path}")
        path_line.setObjectName("CrashPathLine")
        path_line.setWordWrap(True)
        ctx_layout.addWidget(path_line)

        layout.addWidget(context_box)

        # Full Report Text Viewer
        self.report_viewer = QPlainTextEdit()
        self.report_viewer.setObjectName("CrashReportViewer")
        self.report_viewer.setReadOnly(True)
        self.report_viewer.setPlainText(self.full_report)
        layout.addWidget(self.report_viewer, stretch=1)

        # Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_copy = QPushButton("Copy Report Details")
        self.btn_copy.setObjectName("CrashBtnSecondary")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.btn_copy)

        self.btn_open_folder = QPushButton("Open Crash Folder")
        self.btn_open_folder.setObjectName("CrashBtnSecondary")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_crash_folder)
        btn_row.addWidget(self.btn_open_folder)

        btn_row.addStretch()

        self.btn_restart = QPushButton("Restart Application")
        self.btn_restart.setObjectName("CrashBtnPrimary")
        self.btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart.clicked.connect(self._restart_app)
        btn_row.addWidget(self.btn_restart)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("CrashBtnDanger")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_close)

        layout.addLayout(btn_row)
        root.addWidget(content, stretch=1)

    def _copy_to_clipboard(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.full_report)
            self.btn_copy.setText("Copied to Clipboard!")
            QTimer.singleShot(2500, lambda: self.btn_copy.setText("Copy Report Details"))

    def _open_crash_folder(self):
        try:
            if self.report_path and Path(self.report_path).exists():
                folder = str(Path(self.report_path).parent)
            else:
                from src.core.crash_reporter import get_crash_reporter
                dirs = get_crash_reporter().get_crash_directories()
                folder = str(dirs[0]) if dirs else "."

            if os.name == "nt":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _restart_app(self):
        try:
            exe = sys.executable
            args = [a for a in sys.argv if not a.endswith(".pyc")]
            QProcess.startDetached(exe, args)
        except Exception:
            pass
        self.accept()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog#CrashReportDialog {
                background-color: #1E1F1C;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
            }
            QWidget#CrashContent {
                background-color: #1E1F1C;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QLabel#CrashTitle {
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#CrashDesc {
                color: #AAAAAA;
                font-size: 11px;
                line-height: 1.4;
            }
            QFrame#CrashContextCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-left: 3px solid #EF4444;
                border-radius: 4px;
            }
            QLabel#CrashErrLine {
                color: #F87171;
                font-size: 12px;
            }
            QLabel#CrashMetaLine, QLabel#CrashPathLine {
                color: #CCCCCC;
                font-size: 11px;
            }
            QPlainTextEdit#CrashReportViewer {
                background-color: #141414;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                color: #A6E22E;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                padding: 6px;
            }
            QPushButton#CrashBtnSecondary {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                color: #DDDDDD;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
            }
            QPushButton#CrashBtnSecondary:hover {
                background-color: rgba(255, 255, 255, 0.16);
                color: #FFFFFF;
            }
            QPushButton#CrashBtnPrimary {
                background-color: #0284C7;
                border: none;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 14px;
            }
            QPushButton#CrashBtnPrimary:hover {
                background-color: #0369A1;
            }
            QPushButton#CrashBtnDanger {
                background-color: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 5px;
                color: #EF4444;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 14px;
            }
            QPushButton#CrashBtnDanger:hover {
                background-color: #EF4444;
                color: #FFFFFF;
            }
        """)

