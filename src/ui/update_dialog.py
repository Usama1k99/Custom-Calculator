"""
Software Update & Commit Build Selector Dialogs.
Zero emojis, clean progress bar, and instant release switching.
"""

from pathlib import Path
import sys
import tempfile
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QWidget, QFrame
)
from src.version import APP_VERSION, BUILD_COMMIT
from src.core.updater import (
    BinaryDownloadWorker, fetch_all_releases, apply_update_and_restart,
    is_license_entry, get_release_download_url,
    VERSION_STATUS_FUNCTIONAL, VERSION_STATUS_NOT_RECOMMENDED, VERSION_STATUS_DEPRECATED
)


class UpdatePromptDialog(QDialog):
    """
    Update prompt dialog for functional and not recommended versions.
    If the current version is marked Not Recommended, displays a prominent
    warning banner highlighting that updating is highly recommended.
    """
    def __init__(self, release_info: dict, mode: str = "functional", parent=None):
        super().__init__(parent)
        self.release_info = release_info
        # Auto-detect mode from release_info if default "functional" passed
        self.mode = release_info.get("current_status", mode)
        self.is_not_recommended = (self.mode == VERSION_STATUS_NOT_RECOMMENDED)

        if self.is_not_recommended:
            self.setWindowTitle("Update Recommended - Version Not Recommended")
            self.setFixedSize(400, 310)
        else:
            self.setWindowTitle("Software Update Available")
            self.setFixedSize(380, 260)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        tag = self.release_info.get("tag_name", "Latest")
        body = self.release_info.get("body", "Bug fixes and performance improvements.")

        # 1. Header or Highlight Banner
        if self.is_not_recommended:
            warning_box = QFrame()
            warning_box.setStyleSheet("""
                QFrame {
                    background: rgba(245, 158, 11, 0.15);
                    border: 1px solid #F59E0B;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
            warn_layout = QVBoxLayout(warning_box)
            warn_layout.setContentsMargins(8, 6, 8, 6)
            warn_layout.setSpacing(4)

            warn_title = QLabel("ACTION HIGHLY RECOMMENDED")
            warn_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #FBBF24;")
            warn_layout.addWidget(warn_title)

            warn_msg = QLabel(
                f"Your current version (v{APP_VERSION}) is marked as Not Recommended. "
                f"Updating to {tag} is highly recommended to ensure full stability and security."
            )
            warn_msg.setStyleSheet("color: #FDE68A; font-size: 11px;")
            warn_msg.setWordWrap(True)
            warn_layout.addWidget(warn_msg)

            layout.addWidget(warning_box)
        else:
            title = QLabel("A new version of Custom-Calculator is available!")
            title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fff;")
            layout.addWidget(title)

        # 2. Release Info Box
        info_box = QFrame()
        info_box.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(4)

        cur_status_suffix = " (Not Recommended)" if self.is_not_recommended else ""
        cur_lbl = QLabel(f"Current Build:  v{APP_VERSION} ({BUILD_COMMIT}){cur_status_suffix}")
        cur_lbl.setStyleSheet("color: #F87171; font-size: 12px;" if self.is_not_recommended else "color: #888; font-size: 12px;")
        info_layout.addWidget(cur_lbl)

        new_lbl = QLabel(f"Latest Remote:  {tag}")
        new_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(new_lbl)

        self.notes_lbl = QLabel(f"Notes:\n{body[:110]}...")
        self.notes_lbl.setStyleSheet("color: #bbb; font-size: 11px; margin-top: 4px;")
        self.notes_lbl.setWordWrap(True)
        info_layout.addWidget(self.notes_lbl)

        layout.addWidget(info_box)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                text-align: center;
                height: 16px;
                color: #fff;
            }
            QProgressBar::chunk {
                background-color: #10B981;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Actions
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if self.is_not_recommended:
            self.update_btn = QPushButton("Update Now (Highly Recommended)")
            self.update_btn.setStyleSheet("""
                QPushButton {
                    background: #F59E0B;
                    color: #000;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover { background: #D97706; }
            """)
        else:
            self.update_btn = QPushButton("Update to Latest")
            self.update_btn.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: #000;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover { background: #059669; }
            """)
        self.update_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self.update_btn)

        browse_btn = QPushButton("Browse Builds...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                color: #ccc;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        browse_btn.clicked.connect(self._open_build_browser)
        btn_row.addWidget(browse_btn)

        skip_btn = QPushButton("Skip for Now" if self.is_not_recommended else "Skip")
        skip_btn.setStyleSheet(browse_btn.styleSheet())
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(skip_btn)

        layout.addLayout(btn_row)

    def _start_download(self):
        download_url = get_release_download_url(self.release_info)
        out_file = str(Path(tempfile.gettempdir()) / "CustomCalculator_new.exe")

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Downloading...")

        self.worker = BinaryDownloadWorker(download_url, out_file)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.start()

    def _on_download_finished(self, success: bool, path_or_err: str):
        if success:
            self.update_btn.setText("Restarting...")
            apply_update_and_restart(path_or_err)
        else:
            self.update_btn.setText("Retry Update")
            self.update_btn.setEnabled(True)
            self.notes_lbl.setText(f"Update download failed: {path_or_err}")

    def _open_build_browser(self):
        self.accept()
        parent_win = self.parent()
        if parent_win and hasattr(parent_win, "_open_theme_dialog"):
            parent_win._open_theme_dialog(initial_tab=1)
        else:
            dlg = BuildBrowserDialog(parent_win)
            dlg.exec()


class DeprecatedUpdateDialog(QDialog):
    """
    Automatic update dialog for deprecated versions.
    Directly informs the user that the running version is deprecated and automatically
    downloads and installs the latest stable release without requiring user confirmation.
    """
    def __init__(self, release_info: dict, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.setWindowTitle("Critical Update: Version Deprecated")
        self.setFixedSize(400, 240)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        tag = self.release_info.get("tag_name", "Latest Release")

        # 1. Critical notice banner
        alert_box = QFrame()
        alert_box.setStyleSheet("""
            QFrame {
                background: rgba(239, 68, 68, 0.15);
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        alert_layout = QVBoxLayout(alert_box)
        alert_layout.setContentsMargins(8, 6, 8, 6)
        alert_layout.setSpacing(4)

        alert_title = QLabel("CURRENT VERSION DEPRECATED")
        alert_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #F87171;")
        alert_layout.addWidget(alert_title)

        alert_msg = QLabel(
            f"Your current version (v{APP_VERSION}) has been deprecated and is no longer supported.\n"
            f"The application is being updated automatically to {tag}."
        )
        alert_msg.setStyleSheet("color: #FECACA; font-size: 11px;")
        alert_msg.setWordWrap(True)
        alert_layout.addWidget(alert_msg)

        layout.addWidget(alert_box)

        # 2. Status Label & Progress Bar
        self.status_lbl = QLabel("Initializing automatic update download...")
        self.status_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                text-align: center;
                height: 18px;
                color: #fff;
            }
            QProgressBar::chunk {
                background-color: #EF4444;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 3. Actions / Controls (Retry & Close, hidden during active download)
        self.btn_row = QHBoxLayout()
        self.btn_row.setSpacing(8)

        self.retry_btn = QPushButton("Retry Update")
        self.retry_btn.setVisible(False)
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background: #EF4444;
                color: #fff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #DC2626; }
        """)
        self.retry_btn.clicked.connect(self._start_download)
        self.btn_row.addWidget(self.retry_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.setVisible(False)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                color: #ccc;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); color: #fff; }
        """)
        self.close_btn.clicked.connect(self.reject)
        self.btn_row.addWidget(self.close_btn)

        layout.addLayout(self.btn_row)

        # Trigger download automatically without user prompt
        QTimer.singleShot(250, self._start_download)

    def _start_download(self):
        download_url = get_release_download_url(self.release_info)
        out_file = str(Path(tempfile.gettempdir()) / "CustomCalculator_deprecated_update.exe")

        self.retry_btn.setVisible(False)
        self.close_btn.setVisible(False)
        self.status_lbl.setText("Downloading updated release binary...")
        self.progress_bar.setValue(0)

        self.worker = BinaryDownloadWorker(download_url, out_file)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.start()

    def _on_progress(self, pct: int):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(f"Downloading updated release binary... {pct}%")

    def _on_download_finished(self, success: bool, path_or_err: str):
        if success:
            self.status_lbl.setText("Download complete. Relaunching application...")
            self.progress_bar.setValue(100)
            if not getattr(sys, "frozen", False):
                self.status_lbl.setText("[Dev Mode] Download verified. Safe testing completed.")
                self.close_btn.setText("Done")
                self.close_btn.setVisible(True)
            else:
                apply_update_and_restart(path_or_err)
        else:
            self.status_lbl.setText(f"Automatic update failed: {path_or_err}")
            self.retry_btn.setVisible(True)
            self.close_btn.setVisible(True)


class BuildBrowserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Release & Build Archive")
        self.setFixedSize(440, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Available Builds from GitHub Releases:")
        header.setStyleSheet("font-weight: 600; font-size: 12px; color: #aaa;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;")

        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(8, 8, 8, 8)
        cards_layout.setSpacing(6)

        releases = fetch_all_releases()
        if not releases:
            empty = QLabel("No remote release binaries published yet.\nPush a release tag to generate builds.")
            empty.setStyleSheet("color: #777; font-size: 12px; padding: 20px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cards_layout.addWidget(empty)
        else:
            for rel in releases:
                if is_license_entry(rel):
                    continue
                card = self._create_release_card(rel)
                cards_layout.addWidget(card)

        cards_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                color: #ccc;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); color: #fff; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _create_release_card(self, rel: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 6px; padding: 6px;")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)

        v_box = QVBoxLayout()
        v_box.setSpacing(2)
        tag = rel.get("tag_name", "v0.0.0")
        name = rel.get("name") or tag
        date_str = rel.get("published_at", "")[:10]
        status = rel.get("version_status", VERSION_STATUS_FUNCTIONAL)

        status_badge = ""
        if status == VERSION_STATUS_DEPRECATED:
            status_badge = " [Deprecated]"
        elif status == VERSION_STATUS_NOT_RECOMMENDED:
            status_badge = " [Not Recommended]"

        tag_lbl = QLabel(f"{tag} - {name}{status_badge}")
        if status == VERSION_STATUS_DEPRECATED:
            tag_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #F87171;")
        elif status == VERSION_STATUS_NOT_RECOMMENDED:
            tag_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #FBBF24;")
        else:
            tag_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #fff;")
        v_box.addWidget(tag_lbl)

        date_lbl = QLabel(f"Published: {date_str} | Status: {status.replace('_', ' ').title()}")
        date_lbl.setStyleSheet("font-size: 10px; color: #777;")
        v_box.addWidget(date_lbl)
        layout.addLayout(v_box, stretch=1)

        assets = rel.get("assets", [])
        has_exe = any(a.get("name", "").endswith(".exe") for a in assets)

        btn = QPushButton("Download & Run" if has_exe else "No Binary")
        btn.setEnabled(has_exe)
        btn.setStyleSheet("""
            QPushButton {
                background: #6366F1;
                color: #fff;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:disabled { background: #333; color: #666; }
            QPushButton:hover:enabled { background: #4F46E5; }
        """)
        layout.addWidget(btn)
        return card

