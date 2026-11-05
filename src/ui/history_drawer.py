"""
Slide-out Session-Wise History Drawer.
Displays chronologically grouped calculation sessions stored in SQLite.
Allows instant search, formula restoration, and result copying. Zero emojis.
"""

import csv
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QFileDialog, QApplication, QDialog
)
from src.database.history_db import HistoryDB
from src.ui.title_bar import DialogTitleBar
from src.ui.native_window import apply_dialog_rounded_corners
from src.ui.mode_icons import get_themed_icon


class HistoryConfirmDialog(QDialog):
    """Frameless confirmation modal prompt for destructive history deletion. Zero emojis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clear Calculation History")
        self.setFixedSize(340, 160)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setObjectName("HistoryConfirmDialog")
        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        apply_dialog_rounded_corners(self)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = DialogTitleBar(self, title="Clear History")
        root.addWidget(self.title_bar)

        content = QWidget()
        content.setObjectName("ConfirmContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        msg = QLabel("Are you sure you want to clear all calculation history?\nThis action cannot be undone.")
        msg.setStyleSheet("color: #DDD; font-size: 12px; line-height: 1.4;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 6px 14px;
                color: #DDD;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.15); }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #EF4444;
                border: none;
                border-radius: 5px;
                padding: 6px 14px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #DC2626; }
        """)
        clear_btn.clicked.connect(self.accept)
        btn_row.addWidget(clear_btn)

        layout.addLayout(btn_row)
        root.addWidget(content, stretch=1)

        self.setStyleSheet("""
            QDialog#HistoryConfirmDialog {
                background-color: #202020;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
            QWidget#ConfirmContent {
                background-color: #202020;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)


class HistoryDrawer(QFrame):
    expressionSelected = pyqtSignal(str)
    closeRequested = pyqtSignal()

    def __init__(self, db: HistoryDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("HistoryDrawer")
        self.setFixedWidth(290)
        self._current_text_color = "#AAAAAA"
        self._init_ui()

    def update_theme_icons(self, text_color: str):
        self._current_text_color = text_color
        if hasattr(self, "close_btn"):
            self.close_btn.setIcon(get_themed_icon("Close", text_color, size=14))

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Drawer Header
        header = QHBoxLayout()
        title = QLabel("CALCULATION HISTORY")
        title.setProperty("class", "historyTitle")
        header.addWidget(title, stretch=1)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("HistoryCloseBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setIcon(get_themed_icon("Close", self._current_text_color, size=14))
        self.close_btn.clicked.connect(self.closeRequested.emit)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setObjectName("HistorySearch")
        self.search_box.setPlaceholderText("Search formulas or results...")
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        # Scroll Area for Session Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("HistoryScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("HistoryScrollContainer")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # Bottom Action Bar (Export and Clear; deactivated when history is empty)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        self.export_btn = QPushButton("Export")
        self.export_btn.setProperty("class", "historyActionBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_to_csv)
        bottom_row.addWidget(self.export_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "historyClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_history)
        bottom_row.addWidget(self.clear_btn)

        layout.addLayout(bottom_row)

        self.refresh_history()

    def refresh_history(self):
        """
        Reloads history from SQLite database and populates UI cards.
        Deactivates action buttons in edge case when history is empty.
        """
        # Clear existing cards except stretch
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        grouped = self.db.get_grouped_history()
        total_items = 0

        for session in grouped:
            calcs = session["calculations"]
            if not calcs:
                continue

            total_items += len(calcs)
            # Session Header Label
            s_header = QLabel(f"{session['session_name']} ({len(calcs)})")
            s_header.setProperty("class", "historySessionHeader")
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, s_header)

            for c in calcs:
                card = self._create_calc_card(c)
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        has_items = (total_items > 0)
        self.export_btn.setEnabled(has_items)
        self.clear_btn.setEnabled(has_items)
        self.search_box.setEnabled(has_items)

        if not has_items:
            empty_lbl = QLabel("There is no history yet")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setProperty("class", "historyEmpty")
            self.cards_layout.insertWidget(0, empty_lbl)

    def _create_calc_card(self, calc_item: dict) -> QFrame:
        card = QFrame()
        card.setProperty("class", "historyCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Upper row: Mode pill + Timestamp
        top = QHBoxLayout()
        mode_pill = QLabel(calc_item["mode"][:3].upper())
        mode_pill.setProperty("class", "historyModePill")
        top.addWidget(mode_pill)

        time_str = calc_item["timestamp"].split("T")[-1][:5] if "T" in calc_item["timestamp"] else ""
        time_lbl = QLabel(time_str)
        time_lbl.setProperty("class", "historyTime")
        top.addWidget(time_lbl, stretch=1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top)

        # Formula
        expr_lbl = QLabel(calc_item["expression"])
        expr_lbl.setProperty("class", "historyExpr")
        layout.addWidget(expr_lbl)

        # Result
        res_lbl = QLabel(f"= {calc_item['result']}")
        res_lbl.setProperty("class", "historyRes")
        layout.addWidget(res_lbl)

        # Click card to restore formula
        card.mousePressEvent = lambda e, expr=calc_item["expression"]: self.expressionSelected.emit(expr)

        return card

    def _on_search(self, text: str):
        if not text.strip():
            self.refresh_history()
            return

        # Clear existing
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        matches = self.db.search_calculations(text.strip())
        for m in matches:
            card = self._create_calc_card(m)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _clear_history(self):
        dlg = HistoryConfirmDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.clear_all()
            self.refresh_history()

    def _export_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export History to CSV", "calculator_history.csv", "CSV Files (*.csv)")
        if path:
            grouped = self.db.get_grouped_history()
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Session", "Mode", "Expression", "Result", "Timestamp"])
                for s in grouped:
                    for c in s["calculations"]:
                        writer.writerow([s["session_name"], c["mode"], c["expression"], c["result"], c["timestamp"]])

