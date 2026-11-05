"""
Date Calculation View for Custom-Calculator (ApexCalc).
Replicates Windows Calculator Date Calculation experience:
- "Difference between dates": calculates years, months, weeks, days, and working business days.
- "Add or subtract days": adds/subtracts years, months, and days with month-end and leap-year clamping.
- Zero emojis anywhere in the UI. Responsive, modern, styled for all themes.
"""

from datetime import date
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QSpinBox, QRadioButton, QButtonGroup,
    QStackedWidget, QWidget, QScrollArea
)
from src.core.date_engine import (
    calculate_date_difference, add_subtract_duration
)


class DateCalcView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DateCalcView")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(14)

        # ─── TOP: SUB-MODE SELECTOR ──────────────────────────────────
        mode_box = QVBoxLayout()
        mode_box.setSpacing(4)
        
        mode_lbl = QLabel("Calculation Mode")
        mode_lbl.setProperty("class", "dateSectionLabel")
        mode_box.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.setProperty("class", "unitCombo")
        self.mode_combo.addItem("Difference between dates")
        self.mode_combo.addItem("Add or subtract days")
        self.mode_combo.currentIndexChanged.connect(self._on_submode_changed)
        mode_box.addWidget(self.mode_combo)
        main_layout.addLayout(mode_box)

        # ─── STACK FOR THE TWO MODES ────────────────────────────────
        self.mode_stack = QStackedWidget()

        # Page 0: Difference between dates
        self.page_diff = self._create_diff_page()
        self.mode_stack.addWidget(self.page_diff)

        # Page 1: Add or subtract days
        self.page_addsub = self._create_addsub_page()
        self.mode_stack.addWidget(self.page_addsub)

        main_layout.addWidget(self.mode_stack, stretch=1)

        # Initial trigger
        self._recompute_diff()
        self._recompute_addsub()

    def _create_diff_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)

        today = QDate.currentDate()

        # "From" Section
        from_box = QVBoxLayout()
        from_box.setSpacing(4)
        from_lbl = QLabel("From")
        from_lbl.setProperty("class", "dateSectionLabel")
        from_box.addWidget(from_lbl)

        self.from_date_edit = QDateEdit()
        self.from_date_edit.setCalendarPopup(True)
        self.from_date_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.from_date_edit.setDate(today)
        self.from_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.from_date_edit.setProperty("class", "dateEdit")
        self.from_date_edit.dateChanged.connect(self._recompute_diff)
        from_box.addWidget(self.from_date_edit)
        layout.addLayout(from_box)

        # "To" Section
        to_box = QVBoxLayout()
        to_box.setSpacing(4)
        to_lbl = QLabel("To")
        to_lbl.setProperty("class", "dateSectionLabel")
        to_box.addWidget(to_lbl)

        self.to_date_edit = QDateEdit()
        self.to_date_edit.setCalendarPopup(True)
        self.to_date_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.to_date_edit.setDate(today)
        self.to_date_edit.setDisplayFormat("dd-MM-yyyy")
        self.to_date_edit.setProperty("class", "dateEdit")
        self.to_date_edit.dateChanged.connect(self._recompute_diff)
        to_box.addWidget(self.to_date_edit)
        layout.addLayout(to_box)

        # Difference Result Section
        res_frame = QFrame()
        res_frame.setObjectName("DateResultFrame")
        res_layout = QVBoxLayout(res_frame)
        res_layout.setContentsMargins(12, 14, 12, 14)
        res_layout.setSpacing(6)

        diff_title = QLabel("Difference")
        diff_title.setProperty("class", "dateSectionLabel")
        res_layout.addWidget(diff_title)

        self.diff_headline = QLabel("Same date")
        self.diff_headline.setProperty("class", "dateHeadline")
        self.diff_headline.setWordWrap(True)
        res_layout.addWidget(self.diff_headline)

        self.diff_total_days = QLabel("0 days")
        self.diff_total_days.setProperty("class", "dateSubheadline")
        res_layout.addWidget(self.diff_total_days)

        self.diff_business = QLabel("0 working days")
        self.diff_business.setProperty("class", "dateDetailLabel")
        res_layout.addWidget(self.diff_business)

        layout.addWidget(res_frame)
        layout.addStretch()
        return page

    def _create_addsub_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)

        today = QDate.currentDate()

        # "From" Section
        from_box = QVBoxLayout()
        from_box.setSpacing(4)
        from_lbl = QLabel("From")
        from_lbl.setProperty("class", "dateSectionLabel")
        from_box.addWidget(from_lbl)

        self.addsub_from_edit = QDateEdit()
        self.addsub_from_edit.setCalendarPopup(True)
        self.addsub_from_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.addsub_from_edit.setDate(today)
        self.addsub_from_edit.setDisplayFormat("dd-MM-yyyy")
        self.addsub_from_edit.setProperty("class", "dateEdit")
        self.addsub_from_edit.dateChanged.connect(self._recompute_addsub)
        from_box.addWidget(self.addsub_from_edit)
        layout.addLayout(from_box)

        # Radio Options: Add vs Subtract
        radio_box = QHBoxLayout()
        radio_box.setSpacing(16)
        self.radio_add = QRadioButton("Add")
        self.radio_add.setChecked(True)
        self.radio_add.toggled.connect(self._recompute_addsub)
        radio_box.addWidget(self.radio_add)

        self.radio_sub = QRadioButton("Subtract")
        self.radio_sub.toggled.connect(self._recompute_addsub)
        radio_box.addWidget(self.radio_sub)
        radio_box.addStretch()

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_add)
        self.btn_group.addButton(self.radio_sub)
        layout.addLayout(radio_box)

        # Spinboxes for Years, Months, Days
        dur_layout = QHBoxLayout()
        dur_layout.setSpacing(8)

        # Years
        y_box = QVBoxLayout()
        y_box.setSpacing(4)
        y_lbl = QLabel("Years")
        y_lbl.setProperty("class", "dateFieldLabel")
        y_box.addWidget(y_lbl)
        self.spin_years = QSpinBox()
        self.spin_years.setRange(0, 9999)
        self.spin_years.setValue(0)
        self.spin_years.setProperty("class", "dateSpinBox")
        self.spin_years.valueChanged.connect(self._recompute_addsub)
        y_box.addWidget(self.spin_years)
        dur_layout.addLayout(y_box)

        # Months
        m_box = QVBoxLayout()
        m_box.setSpacing(4)
        m_lbl = QLabel("Months")
        m_lbl.setProperty("class", "dateFieldLabel")
        m_box.addWidget(m_lbl)
        self.spin_months = QSpinBox()
        self.spin_months.setRange(0, 99999)
        self.spin_months.setValue(0)
        self.spin_months.setProperty("class", "dateSpinBox")
        self.spin_months.valueChanged.connect(self._recompute_addsub)
        m_box.addWidget(self.spin_months)
        dur_layout.addLayout(m_box)

        # Days
        d_box = QVBoxLayout()
        d_box.setSpacing(4)
        d_lbl = QLabel("Days")
        d_lbl.setProperty("class", "dateFieldLabel")
        d_box.addWidget(d_lbl)
        self.spin_days = QSpinBox()
        self.spin_days.setRange(0, 999999)
        self.spin_days.setValue(0)
        self.spin_days.setProperty("class", "dateSpinBox")
        self.spin_days.valueChanged.connect(self._recompute_addsub)
        d_box.addWidget(self.spin_days)
        dur_layout.addLayout(d_box)

        layout.addLayout(dur_layout)

        # Result Section
        res_frame = QFrame()
        res_frame.setObjectName("DateResultFrame")
        res_layout = QVBoxLayout(res_frame)
        res_layout.setContentsMargins(12, 14, 12, 14)
        res_layout.setSpacing(6)

        date_res_title = QLabel("Date")
        date_res_title.setProperty("class", "dateSectionLabel")
        res_layout.addWidget(date_res_title)

        self.addsub_headline = QLabel()
        self.addsub_headline.setProperty("class", "dateHeadline")
        self.addsub_headline.setWordWrap(True)
        res_layout.addWidget(self.addsub_headline)

        self.addsub_sub = QLabel()
        self.addsub_sub.setProperty("class", "dateSubheadline")
        res_layout.addWidget(self.addsub_sub)

        layout.addWidget(res_frame)
        layout.addStretch()
        return page

    def _on_submode_changed(self, idx: int):
        self.mode_stack.setCurrentIndex(idx)
        if idx == 0:
            self._recompute_diff()
        else:
            self._recompute_addsub()

    def _recompute_diff(self):
        q1 = self.from_date_edit.date()
        q2 = self.to_date_edit.date()
        d1 = date(q1.year(), q1.month(), q1.day())
        d2 = date(q2.year(), q2.month(), q2.day())

        res = calculate_date_difference(d1, d2)
        self.diff_headline.setText(res.formatted_summary)
        self.diff_total_days.setText(res.total_days_summary)
        self.diff_business.setText(res.business_summary)

    def _recompute_addsub(self):
        q1 = self.addsub_from_edit.date()
        start = date(q1.year(), q1.month(), q1.day())
        is_add = self.radio_add.isChecked()
        y = self.spin_years.value()
        m = self.spin_months.value()
        d = self.spin_days.value()

        target = add_subtract_duration(start, y, m, d, add=is_add)
        q_target = QDate(target.year, target.month, target.day)
        
        self.addsub_headline.setText(q_target.toString("dddd, MMMM d, yyyy"))
        
        # Subtitle: e.g. "Today" or "In 45 days" / "45 days ago"
        diff_res = calculate_date_difference(start, target)
        if diff_res.is_same_date:
            sub = "Same as start date"
        elif is_add:
            sub = f"In {diff_res.total_days} days"
        else:
            sub = f"{diff_res.total_days} days earlier"
        self.addsub_sub.setText(sub)

