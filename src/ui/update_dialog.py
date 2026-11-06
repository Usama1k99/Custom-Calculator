"""
Software Update & Commit Build Selector Dialogs.
Zero emojis, clean progress bar, and instant release switching.
"""

from pathlib import Path
import tempfile
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QWidget, QFrame
)
from src.version import APP_VERSION, BUILD_COMMIT
from src.core.updater import (
    BinaryDownloadWorker, fetch_all_releases, apply_update_and_restart, is_license_entry
)


class UpdatePromptDialog(QDialog):
    def __init__(self, release_info: dict, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.setWindowTitle("Software Update Available")
        self.setFixedSize(380, 260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("A new version of Custom-Calculator is available!")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fff;")
        layout.addWidget(title)

        tag = self.release_info.get("tag_name", "Latest")
        body = self.release_info.get("body", "Bug fixes and performance improvements.")

        info_box = QFrame()
        info_box.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(4)

        cur_lbl = QLabel(f"Current Build:  v{APP_VERSION} ({BUILD_COMMIT})")
        cur_lbl.setStyleSheet("color: #888; font-size: 12px;")
        info_layout.addWidget(cur_lbl)

        new_lbl = QLabel(f"Latest Remote:  {tag}")
        new_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(new_lbl)

        notes_lbl = QLabel(f"Notes:\n{body[:120]}...")
        notes_lbl.setStyleSheet("color: #bbb; font-size: 11px; margin-top: 4px;")
        notes_lbl.setWordWrap(True)
        info_layout.addWidget(notes_lbl)

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
            }
            QProgressBar::chunk {
                background-color: #10B981;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Actions
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

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

        skip_btn = QPushButton("Skip")
        skip_btn.setStyleSheet(browse_btn.styleSheet())
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(skip_btn)

        layout.addLayout(btn_row)

    def _start_download(self):
        assets = self.release_info.get("assets", [])
        exe_asset = next((a for a in assets if a.get("name", "").endswith(".exe")), None)

        if not exe_asset:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            html_url = self.release_info.get("html_url", "https://github.com/Usama1k99/Custom-Calculator")
            QDesktopServices.openUrl(QUrl(html_url))
            self.accept()
            return

        download_url = exe_asset.get("browser_download_url")
        out_file = str(Path(tempfile.gettempdir()) / "CustomCalculator_new.exe")

        self.progress_bar.setVisible(True)
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
            self.update_btn.setText("Download Failed")
            self.update_btn.setEnabled(True)

    def _open_build_browser(self):
        self.accept()
        parent_win = self.parent()
        if parent_win and hasattr(parent_win, "_open_theme_dialog"):
            parent_win._open_theme_dialog(initial_tab=1)
        else:
            dlg = BuildBrowserDialog(parent_win)
            dlg.exec()


class BuildBrowserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Release & Build Archive")
        self.setFixedSize(420, 360)
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

        tag_lbl = QLabel(f"{tag} - {name}")
        tag_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #fff;")
        v_box.addWidget(tag_lbl)

        date_lbl = QLabel(f"Published: {date_str}")
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

