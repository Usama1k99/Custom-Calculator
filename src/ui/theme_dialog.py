"""
Theme Selector, Customizer, and Application Settings Dialog.
Includes:
- IDE-Style Color Picker integration
- Bi-directionally synced Hex inputs with edge-case validation
- Custom theme naming prompt with auto-incremented CustomTheme{num}
- Portable Theme JSON Export, Import (file picker & raw JSON paste), and Copy JSON
- Dynamic visibility for Save Custom Palette (hidden on stock presets)
- Software Updates & Commit Build Browser integration fully aligned to active theme tokens
- Frameless modal dialog with custom title bar and Windows 11 rounded corners. Zero emojis.
"""

from pathlib import Path
import json
import re
import tempfile
from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QScrollArea, QWidget, QLineEdit,
    QTabWidget, QFileDialog, QCheckBox, QPlainTextEdit,
    QApplication
)
from src.core.config import ConfigManager
from src.ui.theme_manager import ThemeManager, BUILTIN_THEMES
from src.ui.color_picker import IDEColorPicker
from src.ui.title_bar import DialogTitleBar
from src.ui.native_window import apply_dialog_rounded_corners
from src.ui.update_dialog import UpdatePromptDialog
from src.ui.toggle_switch import ThemeModeToggle
from src.ui.mode_icons import get_themed_svg_path
from src.version import APP_VERSION, BUILD_STATUS, BUILD_COMMIT, GITHUB_REPO
from src.core.updater import (
    VersionCheckWorker, BuildsFetchWorker, fetch_all_releases, BinaryDownloadWorker,
    apply_update_and_restart, is_license_entry, get_release_download_url, parse_semver,
    is_connected_to_internet
)


class ThemeNameDialog(QDialog):
    """Modal prompt to name a custom theme before saving. Zero emojis."""

    def __init__(self, default_name: str, tokens: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Custom Theme")
        self.setFixedSize(320, 160)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setObjectName("ThemeNameDialog")
        self.chosen_name = default_name
        self.tokens = tokens
        self._init_ui(default_name)
        self._apply_styles()

    def showEvent(self, event):
        super().showEvent(event)
        apply_dialog_rounded_corners(self)

    def _init_ui(self, default_name: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title_bar = DialogTitleBar(self, title="Save Custom Theme")
        root.addWidget(title_bar)

        content = QWidget()
        content.setObjectName("ThemeNameContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        prompt_lbl = QLabel("Enter a name for this custom theme:")
        prompt_lbl.setObjectName("ThemePromptLbl")
        layout.addWidget(prompt_lbl)

        self.name_input = QLineEdit(default_name)
        self.name_input.setObjectName("ThemeNameInput")
        self.name_input.selectAll()
        layout.addWidget(self.name_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ThemeNameCancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("ThemeNameSaveBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        root.addWidget(content, stretch=1)

    def _apply_styles(self):
        t = self.tokens
        self.setStyleSheet(f"""
            QDialog#ThemeNameDialog {{
                background-color: {t.get('bg_base', '#1E1F1C')};
                border: 1px solid {t.get('border_subtle', 'rgba(255, 255, 255, 0.12)')};
                border-radius: 8px;
            }}
            QWidget#ThemeNameContent {{
                background-color: {t.get('bg_base', '#1E1F1C')};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QLabel#ThemePromptLbl {{
                font-size: 12px;
                color: {t.get('text_secondary', '#CCCCCC')};
            }}
            QLineEdit#ThemeNameInput {{
                background: {t.get('bg_surface', 'rgba(255, 255, 255, 0.08)')};
                border: 1px solid {t.get('border_subtle', 'rgba(255, 255, 255, 0.18)')};
                border-radius: 5px;
                padding: 6px 10px;
                color: {t.get('text_primary', '#FFFFFF')};
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit#ThemeNameInput:focus {{
                border-color: {t.get('accent_primary', '#3B82F6')};
            }}
            QPushButton#ThemeNameCancelBtn {{
                background: {t.get('bg_card', 'rgba(255, 255, 255, 0.08)')};
                border: 1px solid {t.get('border_subtle', 'rgba(255, 255, 255, 0.15)')};
                border-radius: 5px;
                padding: 6px 14px;
                color: {t.get('text_primary', '#DDD')};
                font-size: 12px;
            }}
            QPushButton#ThemeNameCancelBtn:hover {{
                background: {t.get('bg_card_hover', 'rgba(255, 255, 255, 0.15)')};
            }}
            QPushButton#ThemeNameSaveBtn {{
                background: {t.get('accent_primary', '#10B981')};
                border: none;
                border-radius: 5px;
                padding: 6px 16px;
                color: {t.get('text_accent', '#FFFFFF')};
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#ThemeNameSaveBtn:hover {{
                opacity: 0.9;
            }}
        """)

    def _on_save(self):
        txt = self.name_input.text().strip()
        if txt:
            self.chosen_name = txt
        self.accept()


class ThemeImportDialog(QDialog):
    """Dialog allowing user to import a theme by picking a JSON file or pasting raw JSON. Zero emojis."""

    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.imported_theme_id: Optional[str] = None
        self.setWindowTitle("Import Theme")
        self.setFixedSize(420, 380)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setObjectName("ThemeImportDialog")
        self._init_ui()
        self._apply_styles()

    def showEvent(self, event):
        super().showEvent(event)
        apply_dialog_rounded_corners(self)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title_bar = DialogTitleBar(self, title="Import Theme")
        root.addWidget(title_bar)

        content = QWidget()
        content.setObjectName("ImportContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        # File picker row
        file_row = QHBoxLayout()
        self.pick_file_btn = QPushButton("Choose JSON File...")
        self.pick_file_btn.setObjectName("ImportPickFileBtn")
        self.pick_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_file_btn.clicked.connect(self._on_pick_file)
        file_row.addWidget(self.pick_file_btn)

        self.file_path_lbl = QLabel("No file selected")
        self.file_path_lbl.setObjectName("ImportFilePathLbl")
        self.file_path_lbl.setStyleSheet("font-size: 11px;")
        file_row.addWidget(self.file_path_lbl, stretch=1)
        layout.addLayout(file_row)

        paste_lbl = QLabel("Or paste theme JSON below:")
        paste_lbl.setObjectName("ImportPasteLbl")
        layout.addWidget(paste_lbl)

        self.json_editor = QPlainTextEdit()
        self.json_editor.setObjectName("ImportJsonEditor")
        self.json_editor.setPlaceholderText('{\n  "name": "My Custom Theme",\n  "bg_base": "#1E1E1E",\n  "accent_primary": "#007ACC",\n  ...\n}')
        layout.addWidget(self.json_editor, stretch=1)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("ImportErrorLbl")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setVisible(False)
        layout.addWidget(self.error_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("ImportCancelBtn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("Import")
        self.confirm_btn.setObjectName("ImportConfirmBtn")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.clicked.connect(self._on_import_clicked)
        btn_row.addWidget(self.confirm_btn)

        layout.addLayout(btn_row)
        root.addWidget(content, stretch=1)

    def _on_pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Theme JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.json_editor.setPlainText(content)
                self.file_path_lbl.setText(Path(path).name)
                self.error_lbl.setVisible(False)
            except Exception as e:
                self.error_lbl.setText(f"Failed to read file: {e}")
                self.error_lbl.setVisible(True)

    def _on_import_clicked(self):
        raw = self.json_editor.toPlainText().strip()
        if not raw:
            self.error_lbl.setText("Please paste JSON or choose a JSON file.")
            self.error_lbl.setVisible(True)
            return

        try:
            data = json.loads(raw)
        except Exception as e:
            self.error_lbl.setText(f"Invalid JSON syntax: {e}")
            self.error_lbl.setVisible(True)
            return

        success, t_id, msg = self.theme_manager.import_theme_data(data)
        if success:
            self.imported_theme_id = t_id
            self.accept()
        else:
            self.error_lbl.setText(msg)
            self.error_lbl.setVisible(True)

    def _apply_styles(self):
        t = self.theme_manager.current_tokens
        self.setStyleSheet(f"""
            QDialog#ThemeImportDialog {{
                background-color: {t['bg_base']};
                border: 1px solid {t['border_subtle']};
                border-radius: 8px;
            }}
            QWidget#ImportContent {{
                background-color: {t['bg_base']};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QPushButton#ImportPickFileBtn {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton#ImportPickFileBtn:hover {{
                background-color: {t['bg_card_hover']};
            }}
            QLabel#ImportFilePathLbl {{
                color: {t['text_secondary']};
                font-size: 11px;
            }}
            QLabel#ImportPasteLbl {{
                color: {t['text_secondary']};
                font-size: 12px;
            }}
            QPlainTextEdit#ImportJsonEditor {{
                background-color: {t['bg_surface']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 8px;
            }}
            QPlainTextEdit#ImportJsonEditor:focus {{
                border-color: {t['accent_primary']};
            }}
            QLabel#ImportErrorLbl {{
                color: #EF4444;
                font-size: 11px;
            }}
            QPushButton#ImportCancelBtn {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton#ImportCancelBtn:hover {{
                background-color: {t['bg_card_hover']};
            }}
            QPushButton#ImportConfirmBtn {{
                background-color: {t['accent_primary']};
                color: {t['text_accent']};
                border: none;
                border-radius: 5px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#ImportConfirmBtn:hover {{
                opacity: 0.9;
            }}
        """)


class ThemeDialog(QDialog):
    themeApplied = pyqtSignal()

    def __init__(self, theme_manager: ThemeManager, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setObjectName("ThemeDialog")
        self.setFixedSize(430, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.temp_tokens = dict(self.theme_manager.current_tokens)

        self._check_worker: Optional[VersionCheckWorker] = None
        self._builds_worker: Optional[BuildsFetchWorker] = None

        self._init_ui()
        if initial_tab > 0 and hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(initial_tab)
        self._apply_theme_styles()
        self._update_save_btn_visibility()
        self._load_live_builds()

    def showEvent(self, event):
        super().showEvent(event)
        apply_dialog_rounded_corners(self)

    def closeEvent(self, event):
        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.terminate()
            self._check_worker.wait(500)
        if self._builds_worker and self._builds_worker.isRunning():
            self._builds_worker.terminate()
            self._builds_worker.wait(500)
        super().closeEvent(event)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ─── 1. CUSTOM TITLE BAR (WITH RED CLOSE BUTTON & DRAGGING) ───
        icon_path = Path("assets") / "icons" / "app_icon.svg"
        if not icon_path.exists():
            icon_path = Path("assets") / "icons" / "app_icon.ico"
        self.title_bar = DialogTitleBar(self, title="Settings", icon_path=str(icon_path))
        root_layout.addWidget(self.title_bar)

        # Content container
        content_widget = QWidget(self)
        content_widget.setObjectName("ThemeDialogContent")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(10)

        # ─── 2. TABBED SETTINGS VIEW ─────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabWidget")

        # Tab 1: Themes & Colors
        tab_themes = self._create_themes_tab()
        self.tabs.addTab(tab_themes, "Themes & Colors")

        # Tab 2: Updates & Versions
        tab_updates = self._create_updates_tab()
        self.tabs.addTab(tab_updates, "Updates & Versions")

        layout.addWidget(self.tabs, stretch=1)

        # ─── 3. BOTTOM FOOTER WITH CURRENT VERSION & CLOSE BUTTON ───────
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(4, 0, 4, 0)

        status_suffix = f" ({BUILD_STATUS})" if BUILD_STATUS else ""
        self.version_footer_lbl = QLabel(f"v{APP_VERSION}{status_suffix}")
        self.version_footer_lbl.setObjectName("SettingsFooterVersionLbl")
        bottom_row.addWidget(self.version_footer_lbl)

        bottom_row.addStretch()

        self.done_btn = QPushButton("Done")
        self.done_btn.setObjectName("ThemeDoneBtn")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self.done_btn)

        layout.addLayout(bottom_row)
        root_layout.addWidget(content_widget, stretch=1)

    def _create_themes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 4)
        layout.setSpacing(8)

        # 1. Dark / Light Appearance Mode Row (Slidable Capsule Toggle with Sun & Moon Vector Logos)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        mode_row.addWidget(mode_lbl)

        is_dark = self.theme_manager.current_tokens.get("category", "dark") == "dark"
        self.mode_desc_lbl = QLabel("Dark" if is_dark else "Light")
        self.mode_desc_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        mode_row.addWidget(self.mode_desc_lbl)

        mode_row.addStretch()

        self.mode_toggle = ThemeModeToggle(is_dark=is_dark)
        self.mode_toggle.set_accent_color(self.theme_manager.current_tokens.get("accent_primary", "#F92672"))
        self.mode_toggle.modeToggled.connect(self._on_theme_mode_toggled)
        mode_row.addWidget(self.mode_toggle)
        layout.addLayout(mode_row)

        # 2. Preset Dropdown Row (Filtered to Selected Mode Only)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self.preset_lbl = QLabel("Preset:")
        self.preset_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        preset_row.addWidget(self.preset_lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("ThemePresetCombo")
        self._populate_presets(is_dark=is_dark)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.preset_combo, stretch=1)
        layout.addLayout(preset_row)

        # 3. Custom Themes Dropdown Row
        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self.custom_lbl = QLabel("Custom:")
        self.custom_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        custom_row.addWidget(self.custom_lbl)

        self.custom_combo = QComboBox()
        self.custom_combo.setObjectName("ThemeCustomCombo")
        self._populate_custom_themes()
        self.custom_combo.currentIndexChanged.connect(self._on_custom_theme_changed)
        custom_row.addWidget(self.custom_combo, stretch=1)
        layout.addLayout(custom_row)

        # Import / Export / Copy JSON Buttons Row
        io_row = QHBoxLayout()
        io_row.setSpacing(6)

        self.import_btn = QPushButton("Import Theme...")
        self.import_btn.setObjectName("ThemeIOBtn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_theme_modal)
        io_row.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export Theme...")
        self.export_btn.setObjectName("ThemeIOBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_theme_file)
        io_row.addWidget(self.export_btn)

        self.copy_json_btn = QPushButton("Copy JSON")
        self.copy_json_btn.setObjectName("ThemeIOBtn")
        self.copy_json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_json_btn.clicked.connect(self._copy_theme_json)
        io_row.addWidget(self.copy_json_btn)

        layout.addLayout(io_row)

        # Glass Blur Effect Toggle Row
        blur_row = QHBoxLayout()
        blur_lbl = QLabel("Window Blur:")
        blur_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        blur_row.addWidget(blur_lbl)

        self.blur_check = QCheckBox("Enable Windows Acrylic / Mica frosted blur")
        self.blur_check.setObjectName("BlurEffectCheck")
        self.blur_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.blur_check.setStyleSheet("font-size: 12px;")
        self.blur_check.setChecked(ConfigManager().get("blur_enabled", True))
        self.blur_check.toggled.connect(self._on_blur_toggled)
        blur_row.addWidget(self.blur_check, stretch=1)
        layout.addLayout(blur_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("ThemeDivider")
        layout.addWidget(divider)

        self.custom_title = QLabel("Customize Palette Colors (Live Preview):")
        self.custom_title.setStyleSheet("font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        layout.addWidget(self.custom_title)

        # Scroll area for color tokens
        self.scroll = QScrollArea()
        self.scroll.setObjectName("ThemeScrollArea")
        self.scroll.setWidgetResizable(True)

        self.tokens_container = QWidget()
        self.tokens_container.setObjectName("ThemeTokensContainer")
        self.tokens_layout = QVBoxLayout(self.tokens_container)
        self.tokens_layout.setContentsMargins(0, 0, 0, 0)
        self.tokens_layout.setSpacing(6)

        # Customizable tokens list
        self.editable_tokens = [
            ("bg_base", "Background Base"),
            ("bg_surface", "Display Surface"),
            ("bg_card", "Number Buttons"),
            ("bg_op", "Operator Buttons"),
            ("accent_primary", "Equals & Primary Accent"),
            ("text_primary", "Primary Result Text"),
            ("text_secondary", "Expression Ribbon Text"),
        ]

        self.token_labels = []
        self.swatch_buttons = {}
        self.hex_inputs = {}

        for token_key, label_name in self.editable_tokens:
            row = self._create_token_row(token_key, label_name)
            self.tokens_layout.addWidget(row)

        self.tokens_layout.addStretch()
        self.scroll.setWidget(self.tokens_container)
        layout.addWidget(self.scroll, stretch=1)

        # Save Custom Theme Button (reduced width, centered, no trailing dots)
        self.save_btn = QPushButton("Save Custom Palette")
        self.save_btn.setObjectName("ThemeSaveBtn")
        self.save_btn.setFixedWidth(200)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_custom)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_row.addWidget(self.save_btn)
        save_row.addStretch()
        layout.addLayout(save_row)

        return tab

    def _create_updates_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 10)
        layout.setSpacing(12)

        # App Info Box
        info_frame = QFrame()
        info_frame.setObjectName("UpdateInfoBox")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)

        title_lbl = QLabel("Custom-Calculator (ApexCalc)")
        title_lbl.setObjectName("UpdateAppTitle")
        info_layout.addWidget(title_lbl)

        ver_lbl = QLabel(f"Installed Version:  v{APP_VERSION}")
        ver_lbl.setObjectName("UpdateVerLbl")
        info_layout.addWidget(ver_lbl)

        commit_lbl = QLabel(f"Build Commit:      {BUILD_COMMIT}")
        commit_lbl.setObjectName("UpdateCommitLbl")
        info_layout.addWidget(commit_lbl)

        repo_lbl = QLabel(f"GitHub Repository: {GITHUB_REPO}")
        repo_lbl.setObjectName("UpdateRepoLbl")
        info_layout.addWidget(repo_lbl)

        layout.addWidget(info_frame)

        # Update Status Message
        self.update_status_lbl = QLabel("Check GitHub Releases for latest compiled standalone builds.")
        self.update_status_lbl.setObjectName("UpdateStatusLbl")
        self.update_status_lbl.setWordWrap(True)
        layout.addWidget(self.update_status_lbl)

        # Actions Row
        actions_v = QVBoxLayout()
        actions_v.setSpacing(8)

        self.btn_check_updates = QPushButton("Check for Updates")
        self.btn_check_updates.setObjectName("CheckUpdatesBtn")
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_updates.clicked.connect(self._run_manual_update_check)
        actions_v.addWidget(self.btn_check_updates)

        # Previous Builds & Release Versions Dropdown
        builds_lbl = QLabel("Release Versions & Past Builds:")
        builds_lbl.setObjectName("BuildsHeaderLbl")
        builds_lbl.setStyleSheet("font-size: 12px; font-weight: 600; margin-top: 4px;")
        actions_v.addWidget(builds_lbl)

        self.builds_combo = QComboBox()
        self.builds_combo.setObjectName("BuildsCombo")
        self.builds_combo.addItem(f"v{APP_VERSION} (Installed Current)", {"tag_name": f"v{APP_VERSION}", "body": "Active installation build."})
        self.builds_combo.currentIndexChanged.connect(self._on_build_selected)
        actions_v.addWidget(self.builds_combo)

        self.build_details_lbl = QLabel(f"Currently running build v{APP_VERSION} ({BUILD_COMMIT}).")
        self.build_details_lbl.setObjectName("BuildDetailsLbl")
        self.build_details_lbl.setStyleSheet("font-size: 11px; color: #888888;")
        self.build_details_lbl.setWordWrap(True)
        actions_v.addWidget(self.build_details_lbl)

        self.btn_install_selected = QPushButton("Switch to Selected Version")
        self.btn_install_selected.setObjectName("InstallSelectedBuildBtn")
        self.btn_install_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install_selected.setVisible(False)
        self.btn_install_selected.clicked.connect(self._install_selected_build)
        actions_v.addWidget(self.btn_install_selected)

        layout.addLayout(actions_v)
        layout.addStretch()

        if not is_connected_to_internet(timeout=1.5):
            self.btn_check_updates.setEnabled(False)
            self.builds_combo.setEnabled(False)
            self.btn_install_selected.setEnabled(False)
            self.update_status_lbl.setText("Not connected to internet.")

        return tab

    def _load_live_builds(self):
        """Fetches releases and commits live in the background and populates the build selector."""
        if not is_connected_to_internet(timeout=1.5):
            self.btn_check_updates.setEnabled(False)
            self.builds_combo.setEnabled(False)
            self.btn_install_selected.setEnabled(False)
            self.update_status_lbl.setText("Not connected to internet.")
            return

        self.btn_check_updates.setEnabled(True)
        self.builds_combo.setEnabled(True)
        self._builds_worker = BuildsFetchWorker()
        self._builds_worker.buildsFetched.connect(self._populate_builds_list)
        self._builds_worker.start()

    def _populate_builds_list(self, releases: list):
        self.builds_combo.blockSignals(True)
        self.builds_combo.clear()
        found_current = False
        installed_idx = 0

        for rel in releases:
            if is_license_entry(rel):
                continue
            tag = rel.get("tag_name", "Release")
            sha = rel.get("target_commitish", "")[:7]
            is_curr = (tag.lstrip("v") == APP_VERSION)
            if is_curr:
                found_current = True
                installed_idx = self.builds_combo.count()
            suffix = " (Installed Current)" if is_curr else ""
            self.builds_combo.addItem(f"{tag}{suffix}", rel)

        if not found_current:
            self.builds_combo.insertItem(
                0,
                f"v{APP_VERSION} (Installed Current)",
                {"tag_name": f"v{APP_VERSION}", "body": "Active installation build.", "target_commitish": BUILD_COMMIT}
            )
            installed_idx = 0

        self.builds_combo.setCurrentIndex(installed_idx)
        self.builds_combo.blockSignals(False)
        self._on_build_selected(self.builds_combo.currentIndex())

    def _on_build_selected(self, idx: int):
        data = self.builds_combo.itemData(idx)
        if not data or not isinstance(data, dict):
            return
        tag = data.get("tag_name", "Release")
        body = data.get("body", "No release notes available.")
        date = data.get("published_at", "")[:10]
        sha = data.get("target_commitish", "")[:7]

        desc_parts = [f"Version: {tag}"]
        if sha:
            desc_parts.append(f"({sha})")
        if date:
            desc_parts.append(f"[{date}]")
        header_line = " ".join(desc_parts)
        first_line = body.splitlines()[0] if body else ""
        desc = f"{header_line}\n{first_line[:140]}"
        self.build_details_lbl.setText(desc)

        tag_ver = tag.lstrip("v")
        is_different = (tag_ver != APP_VERSION)
        self.btn_install_selected.setVisible(is_different)
        if is_different:
            if parse_semver(tag_ver) > parse_semver(APP_VERSION):
                self.btn_install_selected.setText(f"Update to {tag}")
            else:
                self.btn_install_selected.setText(f"Switch to {tag}")

    def _install_selected_build(self):
        data = self.builds_combo.currentData()
        if not data:
            return

        tag = data.get("tag_name", f"v{APP_VERSION}")
        download_url = get_release_download_url(data)
        out_path = str(Path(tempfile.gettempdir()) / f"Calculator_{tag}.exe")
        self.btn_install_selected.setEnabled(False)
        self.btn_check_updates.setEnabled(False)
        self.build_details_lbl.setText(f"Downloading {tag} standalone binary (0%)...")

        worker = BinaryDownloadWorker(download_url, out_path)

        def on_progress(pct: int):
            self.build_details_lbl.setText(f"Downloading {tag} standalone binary ({pct}%)...")

        def on_done(success: bool, path_or_err: str):
            self.btn_install_selected.setEnabled(True)
            self.btn_check_updates.setEnabled(True)
            if success:
                self.build_details_lbl.setText("Download complete! Applying update and restarting...")
                apply_update_and_restart(path_or_err)
            else:
                self.build_details_lbl.setText(f"Download failed: {path_or_err}. Please retry later.")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_done)
        worker.start()
        self._download_worker = worker

    def _populate_presets(self, is_dark: Optional[bool] = None):
        if is_dark is None:
            is_dark = self.theme_manager.current_tokens.get("category", "dark") == "dark"
        target_cat = "dark" if is_dark else "light"

        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()

        # Built-in themes filtered to active dark/light mode only
        for t_id, data in BUILTIN_THEMES.items():
            if data.get("category") == target_cat:
                self.preset_combo.addItem(data["name"], t_id)

        # Select current if it matches
        idx = self.preset_combo.findData(self.theme_manager.current_theme_id)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        else:
            self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def _populate_custom_themes(self):
        self.custom_combo.blockSignals(True)
        self.custom_combo.clear()
        custom_map = self.theme_manager.get_custom_themes_map()

        if not custom_map:
            self.custom_combo.addItem("(No custom themes saved)", None)
            self.custom_combo.setEnabled(False)
        else:
            self.custom_combo.setEnabled(True)
            self.custom_combo.addItem("(Select a custom theme...)", None)
            for t_id, data in custom_map.items():
                self.custom_combo.addItem(data.get("name", "Custom"), t_id)

            if self.theme_manager.current_theme_id in custom_map:
                idx = self.custom_combo.findData(self.theme_manager.current_theme_id)
                if idx >= 0:
                    self.custom_combo.setCurrentIndex(idx)
            else:
                self.custom_combo.setCurrentIndex(0)
        self.custom_combo.blockSignals(False)

    def _create_token_row(self, token_key: str, label_name: str) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(6)

        lbl = QLabel(label_name)
        lbl.setStyleSheet("font-size: 12px;")
        self.token_labels.append(lbl)
        row.addWidget(lbl, stretch=1)

        val = self.temp_tokens.get(token_key, "#6366F1")
        if not val.startswith("#"):
            val = f"#{val}"
        val_upper = val.upper()

        # Hex text field synced with color box
        hex_input = QLineEdit(val_upper)
        hex_input.setFixedWidth(74)
        hex_input.setMaxLength(7)
        hex_input.setObjectName("TokenHexInput")
        hex_input.setStyleSheet("""
            QLineEdit#TokenHexInput {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #FFFFFF;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 2px 4px;
                text-align: center;
            }
            QLineEdit#TokenHexInput:focus {
                border-color: #3B82F6;
            }
        """)
        hex_input.textChanged.connect(lambda txt, k=token_key: self._on_hex_text_changed(k, txt))
        self.hex_inputs[token_key] = hex_input
        row.addWidget(hex_input)

        # Color swatch button
        swatch = QPushButton()
        swatch.setFixedSize(26, 22)
        swatch.setStyleSheet(f"background-color: {val}; border-radius: 4px; border: 1px solid #777;")
        swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        swatch.setToolTip("Click to open IDE color picker")
        swatch.clicked.connect(lambda _, k=token_key, b=swatch: self._open_color_picker(k, b))

        self.swatch_buttons[token_key] = swatch
        row.addWidget(swatch)

        return widget

    def _is_palette_custom(self) -> bool:
        """Determines whether current palette tokens differ from all built-in presets."""
        for _, t_data in BUILTIN_THEMES.items():
            matches = True
            for key, _ in self.editable_tokens:
                curr_val = self.temp_tokens.get(key, "").upper().lstrip("#")
                ref_val = t_data.get(key, "").upper().lstrip("#")
                if curr_val != ref_val:
                    matches = False
                    break
            if matches:
                return False
        return True

    def _update_save_btn_visibility(self):
        """Shows Save Custom Palette only when the tokens do not match any built-in preset."""
        self.save_btn.setVisible(self._is_palette_custom())

    def _on_hex_text_changed(self, token_key: str, raw_text: str):
        clean = raw_text.strip().lstrip("#")
        if re.fullmatch(r"[0-9A-Fa-f]{6}", clean):
            norm_hex = f"#{clean.upper()}"
            self.temp_tokens[token_key] = norm_hex

            swatch = self.swatch_buttons.get(token_key)
            if swatch:
                swatch.setStyleSheet(f"background-color: {norm_hex}; border-radius: 4px; border: 1px solid #777;")

            # Live real-time UI preview
            self.theme_manager.themes["custom_preview"] = dict(self.temp_tokens)
            self.theme_manager.set_theme("custom_preview")
            self._apply_theme_styles()
            self._update_save_btn_visibility()
            self.themeApplied.emit()

    def _open_color_picker(self, token_key: str, swatch_btn: QPushButton):
        curr_hex = self.temp_tokens.get(token_key, "#6366F1")
        picker = IDEColorPicker(curr_hex, self)

        def on_color_picked(new_hex: str):
            norm_hex = new_hex.upper()
            self.temp_tokens[token_key] = norm_hex
            swatch_btn.setStyleSheet(f"background-color: {norm_hex}; border-radius: 4px; border: 1px solid #777;")

            # Sync Hex text input
            hex_in = self.hex_inputs.get(token_key)
            if hex_in and hex_in.text() != norm_hex:
                hex_in.blockSignals(True)
                hex_in.setText(norm_hex)
                hex_in.blockSignals(False)

            # Live real-time UI preview
            self.theme_manager.themes["custom_preview"] = dict(self.temp_tokens)
            self.theme_manager.set_theme("custom_preview")
            self._apply_theme_styles()
            self._update_save_btn_visibility()
            self.themeApplied.emit()

        picker.colorSelected.connect(on_color_picked)
        picker.exec()

    def _on_theme_mode_toggled(self, is_dark: bool):
        self.mode_desc_lbl.setText("Dark" if is_dark else "Light")
        self._populate_presets(is_dark=is_dark)

        curr_cat = self.theme_manager.current_tokens.get("category", "dark")
        target_cat = "dark" if is_dark else "light"

        if curr_cat != target_cat:
            first_theme_id = self.preset_combo.itemData(0)
            if first_theme_id:
                if hasattr(self, "custom_combo"):
                    self.custom_combo.blockSignals(True)
                    self.custom_combo.setCurrentIndex(0)
                    self.custom_combo.blockSignals(False)

                self.theme_manager.set_theme(first_theme_id)
                self.temp_tokens = dict(self.theme_manager.current_tokens)
                self._update_swatches_and_fields()
                self._apply_theme_styles()
                self._update_save_btn_visibility()
                self.themeApplied.emit()

    def _on_custom_theme_changed(self, idx: int):
        theme_id = self.custom_combo.itemData(idx)
        if theme_id:
            self.theme_manager.set_theme(theme_id)
            self.temp_tokens = dict(self.theme_manager.current_tokens)
            is_dark = self.temp_tokens.get("category", "dark") == "dark"

            self.mode_toggle.blockSignals(True)
            self.mode_toggle.set_dark_mode(is_dark, animate=False)
            self.mode_toggle.blockSignals(False)
            self.mode_desc_lbl.setText("Dark" if is_dark else "Light")

            self._populate_presets(is_dark=is_dark)
            self._update_swatches_and_fields()
            self._apply_theme_styles()
            self._update_save_btn_visibility()
            self.themeApplied.emit()

    def _on_preset_changed(self, idx: int):
        theme_id = self.preset_combo.itemData(idx)
        if theme_id:
            if hasattr(self, "custom_combo") and self.custom_combo.currentIndex() != 0:
                self.custom_combo.blockSignals(True)
                self.custom_combo.setCurrentIndex(0)
                self.custom_combo.blockSignals(False)

            self.theme_manager.set_theme(theme_id)
            self.temp_tokens = dict(self.theme_manager.current_tokens)
            self._update_swatches_and_fields()
            self._apply_theme_styles()
            self._update_save_btn_visibility()
            self.themeApplied.emit()

    def _update_swatches_and_fields(self):
        for k, btn in self.swatch_buttons.items():
            val = self.temp_tokens.get(k, "#6366F1")
            if not val.startswith("#"):
                val = f"#{val}"
            btn.setStyleSheet(f"background-color: {val}; border-radius: 4px; border: 1px solid #777;")

        for k, line_edit in self.hex_inputs.items():
            val = self.temp_tokens.get(k, "#6366F1")
            if not val.startswith("#"):
                val = f"#{val}"
            line_edit.blockSignals(True)
            line_edit.setText(val.upper())
            line_edit.blockSignals(False)

    def _save_custom(self):
        default_name = self.theme_manager.get_next_custom_theme_name()
        dlg = ThemeNameDialog(default_name, self.temp_tokens, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            theme_name = dlg.chosen_name
            t_id = self.theme_manager.save_new_custom_theme(theme_name, dict(self.temp_tokens))
            self._populate_custom_themes()
            idx = self.custom_combo.findData(t_id)
            if idx >= 0:
                self.custom_combo.setCurrentIndex(idx)
            self._apply_theme_styles()
            self._update_save_btn_visibility()
            self.themeApplied.emit()

    def _export_theme_file(self):
        default_name = f"{self.theme_manager.get_next_custom_theme_name().lower()}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export Theme as JSON", default_name, "JSON Files (*.json)")
        if path:
            self.theme_manager.export_theme(self.theme_manager.current_theme_id, path)

    def _copy_theme_json(self):
        """Copies formatted JSON representation of active palette tokens to system clipboard."""
        payload = {
            "name": self.preset_combo.currentText(),
            **self.temp_tokens
        }
        app = QApplication.instance()
        if app:
            app.clipboard().setText(json.dumps(payload, indent=2))
            self.copy_json_btn.setText("Copied!")
            QTimer.singleShot(1500, lambda: self.copy_json_btn.setText("Copy JSON"))

    def _import_theme_modal(self):
        """Opens import dialog supporting both picking a file and pasting raw JSON."""
        dlg = ThemeImportDialog(self.theme_manager, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.imported_theme_id:
            self._populate_custom_themes()
            idx = self.custom_combo.findData(dlg.imported_theme_id)
            if idx >= 0:
                self.custom_combo.setCurrentIndex(idx)
            self.themeApplied.emit()

    def _on_blur_toggled(self, checked: bool):
        ConfigManager().set("blur_enabled", checked)
        self.themeApplied.emit()

    def _run_manual_update_check(self):
        if not is_connected_to_internet(timeout=1.5):
            self.btn_check_updates.setEnabled(False)
            self.builds_combo.setEnabled(False)
            self.btn_install_selected.setEnabled(False)
            self.update_status_lbl.setText("Not connected to internet.")
            return

        self.btn_check_updates.setEnabled(False)
        self.update_status_lbl.setText("Checking GitHub API for latest release...")
        self._check_worker = VersionCheckWorker()

        def on_finished(update_available: bool, release_info: dict):
            if release_info.get("is_offline"):
                self.btn_check_updates.setEnabled(False)
                self.builds_combo.setEnabled(False)
                self.btn_install_selected.setEnabled(False)
                self.update_status_lbl.setText("Not connected to internet.")
                return

            self.btn_check_updates.setEnabled(True)
            self._load_live_builds()

            if update_available:
                tag = release_info.get("tag_name", "Latest")
                self.update_status_lbl.setText(f"Update available: {tag}! You can select and switch versions from the dropdown below.")
            else:
                self.update_status_lbl.setText("You are currently running the latest compiled release build.")

        self._check_worker.checkCompleted.connect(on_finished)
        self._check_worker.start()

    def _apply_theme_styles(self):
        """Applies active theme colors and tokens to the entire dialog window."""
        t = self.theme_manager.current_tokens
        chevron_down_path = get_themed_svg_path("ChevronDown", t.get("text_secondary", "#CCCCCC"))
        self.setStyleSheet(f"""
            QDialog#ThemeDialog {{
                background-color: {t['bg_base']};
                border: 1px solid {t['border_subtle']};
                border-radius: 8px;
            }}
            QWidget#dialogTitleBar {{
                background-color: {t['bg_surface']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid {t['border_subtle']};
            }}
            QLabel#dialogTitleLabel {{
                color: {t['text_primary']};
                font-weight: 600;
            }}
            QWidget#ThemeDialogContent {{
                background-color: transparent;
            }}
            QLabel {{
                color: {t['text_primary']};
            }}
            QLabel#custom_title {{
                color: {t['text_secondary']};
            }}
            QFrame#ThemeDivider {{
                background-color: {t['border_subtle']};
                max-height: 1px;
            }}
            QTabWidget#SettingsTabWidget::pane {{
                border: 1px solid {t['border_subtle']};
                border-radius: 6px;
                background-color: {t['bg_surface']};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {t['bg_card']};
                color: {t['text_secondary']};
                padding: 6px 14px;
                margin-right: 4px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {t['bg_surface']};
                color: {t['accent_primary']};
                border-bottom: 2px solid {t['accent_primary']};
            }}
            QComboBox#ThemePresetCombo, QComboBox#ThemeCustomCombo {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 5px;
                padding: 6px 28px 6px 10px;
                font-size: 12px;
            }}
            QComboBox#ThemePresetCombo:hover, QComboBox#ThemeCustomCombo:hover {{
                border-color: {t['accent_primary']};
            }}
            QComboBox#ThemePresetCombo::drop-down, QComboBox#ThemeCustomCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
            }}
            QComboBox#ThemePresetCombo::down-arrow, QComboBox#ThemeCustomCombo::down-arrow {{
                image: url({chevron_down_path});
                width: 12px;
                height: 12px;
            }}
            QComboBox#ThemePresetCombo QAbstractItemView, QComboBox#ThemeCustomCombo QAbstractItemView {{
                background-color: {t['bg_surface']};
                color: {t['text_primary']};
                selection-background-color: {t['bg_card_active']};
                selection-color: {t['accent_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 4px;
                outline: none;
                padding: 4px;
            }}
            QPushButton#ThemeIOBtn {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 5px;
                padding: 5px 12px;
                font-size: 11px;
            }}
            QPushButton#ThemeIOBtn:hover {{
                background-color: {t['bg_card_hover']};
            }}
            QScrollArea#ThemeScrollArea,
            QWidget#ThemeTokensContainer {{
                background: transparent;
                border: none;
            }}
            QPushButton#ThemeSaveBtn {{
                background-color: {t['accent_primary']};
                color: {t['text_accent']};
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                border: none;
            }}
            QPushButton#ThemeSaveBtn:hover {{
                opacity: 0.9;
            }}
            QCheckBox#BlurEffectCheck {{
                color: {t['text_primary']};
                spacing: 8px;
            }}
            QCheckBox#BlurEffectCheck::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {t['border_subtle']};
                border-radius: 4px;
                background-color: {t['bg_card']};
            }}
            QCheckBox#BlurEffectCheck::indicator:checked {{
                background-color: {t['accent_primary']};
                border-color: {t['accent_primary']};
            }}
            QLabel#SettingsFooterVersionLbl {{
                font-size: 11px;
                color: {t['text_secondary']};
                background: transparent;
                padding-left: 2px;
            }}
            QPushButton#ThemeDoneBtn {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 6px;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#ThemeDoneBtn:hover {{
                background-color: {t['bg_card_hover']};
            }}
            /* ── Updates & Versions Tab Elements Aligned to Active Theme ── */
            QFrame#UpdateInfoBox {{
                background: {t['bg_card']};
                border: 1px solid {t['border_subtle']};
                border-radius: 6px;
                padding: 12px;
            }}
            QLabel#UpdateAppTitle {{
                font-size: 14px;
                font-weight: 700;
                color: {t['text_primary']};
            }}
            QLabel#UpdateVerLbl {{
                font-size: 12px;
                color: {t['accent_primary']};
                font-weight: 600;
            }}
            QLabel#UpdateCommitLbl {{
                font-size: 11px;
                color: {t['text_secondary']};
                font-family: 'Consolas', monospace;
            }}
            QLabel#UpdateRepoLbl {{
                font-size: 11px;
                color: {t['text_secondary']};
            }}
            QLabel#UpdateStatusLbl {{
                font-size: 12px;
                color: {t['text_secondary']};
            }}
            QPushButton#CheckUpdatesBtn {{
                background-color: {t['accent_primary']};
                color: {t['text_accent']};
                font-weight: 700;
                font-size: 12px;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
            }}
            QPushButton#CheckUpdatesBtn:hover {{
                opacity: 0.9;
            }}
            QComboBox#BuildsCombo {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 5px;
                padding: 6px 28px 6px 10px;
                font-size: 12px;
            }}
            QComboBox#BuildsCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
            }}
            QComboBox#BuildsCombo::down-arrow {{
                image: url({chevron_down_path});
                width: 12px;
                height: 12px;
            }}
            QComboBox#BuildsCombo QAbstractItemView {{
                background-color: {t['bg_surface']};
                color: {t['text_primary']};
                selection-background-color: {t['bg_card_active']};
                selection-color: {t['accent_primary']};
                border: 1px solid {t['border_subtle']};
                border-radius: 4px;
                outline: none;
                padding: 4px;
            }}
            QPushButton#InstallSelectedBuildBtn {{
                background-color: {t['accent_primary']};
                color: {t['text_accent']};
                font-weight: 700;
                font-size: 12px;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
            }}
            QPushButton#InstallSelectedBuildBtn:hover {{
                opacity: 0.9;
            }}
        """)

        if hasattr(self, "mode_toggle"):
            self.mode_toggle.set_accent_color(t.get("accent_primary", "#F92672"))
