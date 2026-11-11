"""
Unit and Currency Converter View (Windows Calculator Style).
Supports instant two-way conversion across 12 domains. Zero emojis.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QGridLayout, QPushButton, QWidget
)

from src.core.currency_engine import CurrencyEngine, code_from_label


CONVERSION_FACTORS: Dict[str, Dict[str, float]] = {
    "Length": {
        "Meters": 1.0,
        "Kilometers": 1000.0,
        "Centimeters": 0.01,
        "Millimeters": 0.001,
        "Miles": 1609.344,
        "Yards": 0.9144,
        "Feet": 0.3048,
        "Inches": 0.0254
    },
    "Weight and Mass": {
        "Kilograms": 1.0,
        "Grams": 0.001,
        "Milligrams": 0.000001,
        "Metric Tons": 1000.0,
        "Pounds": 0.45359237,
        "Ounces": 0.028349523,
        "Stone": 6.350293
    },
    "Volume": {
        "Cubic Meters (m³)": 1000.0,
        "Cubic Centimeters (cm³)": 0.001,
        "Cubic Millimeters (mm³)": 0.000001,
        "Cubic Inches (in³)": 0.016387064,
        "Cubic Feet (ft³)": 28.316846592,
        "Cubic Yards (yd³)": 764.554857984,
        "Liters (L)": 1.0,
        "Milliliters (mL)": 0.001,
        "US Gallons (gal)": 3.785411784,
        "US Quarts (qt)": 0.946352946,
        "US Pints (pt)": 0.473176473,
        "US Cups": 0.2365882365,
        "US Fluid Ounces (fl oz)": 0.0295735295625,
        "Imperial Gallons (UK gal)": 4.54609,
        "US Tablespoons (tbsp)": 0.01478676478125,
        "US Teaspoons (tsp)": 0.00492892159375
    },
    "Speed": {
        "Meters per second": 1.0,
        "Kilometers per hour": 0.27777778,
        "Miles per hour": 0.44704,
        "Knots": 0.51444444
    },
    "Time": {
        "Seconds": 1.0,
        "Minutes": 60.0,
        "Hours": 3600.0,
        "Days": 86400.0,
        "Weeks": 604800.0,
        "Years": 31536000.0
    },
    "Data": {
        "Bits (b)": 0.125,
        "Bytes (B)": 1.0,
        "Kilobits (Kb)": 128.0,
        "Kilobytes (KB)": 1024.0,
        "Megabits (Mb)": 131072.0,
        "Megabytes (MB)": 1048576.0,
        "Gigabits (Gb)": 134217728.0,
        "Gigabytes (GB)": 1073741824.0,
        "Terabits (Tb)": 137438953472.0,
        "Terabytes (TB)": 1099511627776.0,
        "Petabits (Pb)": 140737488355328.0,
        "Petabytes (PB)": 1125899906842624.0,
        "Exabits (Eb)": 144115188075855872.0,
        "Exabytes (EB)": 1152921504606846976.0,
        "Zettabytes (ZB)": 1180591620717411303424.0,
        "Yottabytes (YB)": 1208925819614629174706176.0
    },
    "Area": {
        "Square meters": 1.0,
        "Square kilometers": 1000000.0,
        "Square feet": 0.09290304,
        "Acres": 4046.8564,
        "Hectares": 10000.0
    },
    "Energy": {
        "Joules": 1.0,
        "Kilojoules": 1000.0,
        "Calories": 4.184,
        "Kilocalories": 4184.0,
        "Watt-hours": 3600.0,
        "Kilowatt-hours": 3600000.0
    },
    "Power": {
        "Watts": 1.0,
        "Kilowatts": 1000.0,
        "Horsepower": 745.69987
    },
    "Pressure": {
        "Pascals": 1.0,
        "Bar": 100000.0,
        "PSI": 6894.757,
        "Atmospheres": 101325.0
    },
    "Angle": {
        "Degrees": 1.0,
        "Radians": 57.2957795,
        "Gradians": 0.9
    }
}


class ConverterView(QFrame):
    def __init__(self, category: str = "Length", parent=None):
        super().__init__(parent)
        self.setObjectName("ConverterView")
        self.category = category
        self.currency_engine = CurrencyEngine()
        self._init_ui()

    def set_category(self, category: str):
        self.category = category
        self._populate_units()
        if self.category == "Currency":
            # Auto refresh currency rates if offline or older than 1 hour
            self.currency_engine.fetch_live_rates_async(self._on_currency_synced)
        self._calculate()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        # ─── SECTION 1 & 2 & 3: COMPACT TOP CONVERTER INPUTS ────────
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        # Input 1
        v1 = QVBoxLayout()
        v1.setSpacing(2)
        self.input1 = QLineEdit("1")
        self.input1.setProperty("class", "converterInput")
        self.input1.textChanged.connect(self._on_input1_changed)
        v1.addWidget(self.input1)

        self.combo1 = QComboBox()
        self.combo1.setProperty("class", "unitCombo")
        self.combo1.currentIndexChanged.connect(self._calculate)
        v1.addWidget(self.combo1)
        top_layout.addLayout(v1)

        # Equals Divider
        equals_lbl = QLabel("=")
        equals_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #888; padding: 1px 0;")
        top_layout.addWidget(equals_lbl)

        # Input 2
        v2 = QVBoxLayout()
        v2.setSpacing(2)
        self.input2 = QLineEdit("1")
        self.input2.setProperty("class", "converterInput")
        self.input2.setReadOnly(True)
        v2.addWidget(self.input2)

        self.combo2 = QComboBox()
        self.combo2.setProperty("class", "unitCombo")
        self.combo2.currentIndexChanged.connect(self._calculate)
        v2.addWidget(self.combo2)
        top_layout.addLayout(v2)

        # Currency Live Sync Row
        self.currency_status_row = QWidget()
        c_layout = QHBoxLayout(self.currency_status_row)
        c_layout.setContentsMargins(2, 2, 2, 2)
        c_layout.setSpacing(6)

        self.currency_status_lbl = QLabel(self.currency_engine.last_updated_str)
        self.currency_status_lbl.setStyleSheet("font-size: 11px; color: #888888;")
        c_layout.addWidget(self.currency_status_lbl, stretch=1)

        self.btn_refresh_rates = QPushButton("Sync Rates")
        self.btn_refresh_rates.setFixedHeight(22)
        self.btn_refresh_rates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_rates.setStyleSheet(
            "QPushButton { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 4px; }"
        )
        self.btn_refresh_rates.clicked.connect(self._sync_live_currency_rates)
        c_layout.addWidget(self.btn_refresh_rates)

        self.currency_status_row.setVisible(self.category == "Currency")
        top_layout.addWidget(self.currency_status_row)

        layout.addWidget(top_container, stretch=0)
        layout.addSpacing(6)

        # ─── SECTION 4: MINI NUMPAD EXPANDING TO FILL BOTTOM ────────
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        key_map = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["C", "0", "."]
        ]
        from PyQt6.QtWidgets import QSizePolicy
        for r, row in enumerate(key_map):
            for c, key in enumerate(row):
                btn = QPushButton(key)
                btn.setProperty("class", "calcKey numKey" if key.isdigit() or key == "." else "calcKey fnKey")
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                btn.setMinimumHeight(38)
                btn.clicked.connect(lambda _, k=key: self._on_key_clicked(k))
                grid.addWidget(btn, r, c)
        layout.addWidget(grid_container, stretch=1)

        self._populate_units()
        self._calculate()

    def _populate_units(self):
        self.combo1.blockSignals(True)
        self.combo2.blockSignals(True)
        self.combo1.clear()
        self.combo2.clear()

        if self.category == "Temperature":
            units = ["Celsius", "Fahrenheit", "Kelvin"]
            self.currency_status_row.setVisible(False)
        elif self.category == "Currency":
            units = self.currency_engine.get_currency_list()
            self.currency_status_row.setVisible(True)
            self.currency_status_lbl.setText(self.currency_engine.last_updated_str)
        else:
            factors = CONVERSION_FACTORS.get(self.category, CONVERSION_FACTORS["Length"])
            units = list(factors.keys())
            self.currency_status_row.setVisible(False)

        for u in units:
            self.combo1.addItem(u)
            self.combo2.addItem(u)

        if len(units) > 1:
            self.combo2.setCurrentIndex(1)

        self.combo1.blockSignals(False)
        self.combo2.blockSignals(False)

    def _sync_live_currency_rates(self):
        self.btn_refresh_rates.setEnabled(False)
        self.currency_status_lbl.setText("Syncing live rates...")
        self.currency_engine.fetch_live_rates_async(self._on_currency_synced)

    def _on_currency_synced(self, success: bool, msg: str):
        # Schedule GUI update on Qt main thread safely
        QTimer.singleShot(0, lambda: self._apply_currency_sync_result(msg))

    def _apply_currency_sync_result(self, msg: str):
        self.btn_refresh_rates.setEnabled(True)
        self.currency_status_lbl.setText(msg)
        self._calculate()

    def _on_key_clicked(self, key: str):
        cur = self.input1.text()
        if key == "C":
            self.input1.setText("0")
        elif key == ".":
            if "." not in cur:
                self.input1.setText(cur + ".")
        else:
            if cur == "0":
                self.input1.setText(key)
            else:
                self.input1.setText(cur + key)

    def _on_input1_changed(self, text: str):
        self._calculate()

    def _calculate(self):
        text = self.input1.text().strip()
        if not text:
            self.input2.setText("0")
            return

        try:
            val = float(text)
        except ValueError:
            self.input2.setText("Invalid input")
            return

        unit1 = self.combo1.currentText()
        unit2 = self.combo2.currentText()

        if self.category == "Temperature":
            result = self._convert_temperature(val, unit1, unit2)
        elif self.category == "Currency":
            code1 = code_from_label(unit1)
            code2 = code_from_label(unit2)
            result = self.currency_engine.convert(val, code1, code2)
        else:
            factors = CONVERSION_FACTORS.get(self.category, CONVERSION_FACTORS["Length"])
            f1 = factors.get(unit1, 1.0)
            f2 = factors.get(unit2, 1.0)
            # base = val * f1; result = base / f2
            result = (val * f1) / f2

        if abs(result - round(result)) < 1e-9:
            self.input2.setText(str(int(round(result))))
        else:
            if abs(result) >= 1e9 or (0 < abs(result) < 1e-4):
                self.input2.setText(f"{result:.6e}")
            else:
                self.input2.setText(f"{result:.6g}")

    def _convert_temperature(self, val: float, u1: str, u2: str) -> float:
        # Convert u1 to Celsius
        if u1 == "Fahrenheit":
            c = (val - 32) * 5 / 9
        elif u1 == "Kelvin":
            c = val - 273.15
        else:
            c = val

        # Convert Celsius to u2
        if u2 == "Fahrenheit":
            return (c * 9 / 5) + 32
        elif u2 == "Kelvin":
            return c + 273.15
        else:
            return c
