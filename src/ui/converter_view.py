"""
Unit and Currency Converter View (Windows Calculator Style).
Supports instant two-way conversion across 12 domains. Zero emojis.
"""

from decimal import Decimal
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QGridLayout, QPushButton
)


CONVERSION_FACTORS = {
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
        "Bytes": 1.0,
        "Kilobytes (KB)": 1024.0,
        "Megabytes (MB)": 1048576.0,
        "Gigabytes (GB)": 1073741824.0,
        "Terabytes (TB)": 1099511627776.0
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
    },
    "Currency": {
        "USD ($)": 1.0,
        "EUR (€)": 1.08,
        "GBP (£)": 1.28,
        "JPY (¥)": 0.0066,
        "CAD ($)": 0.73,
        "AUD ($)": 0.65,
        "INR (₹)": 0.012
    }
}


class ConverterView(QFrame):
    def __init__(self, category: str = "Length", parent=None):
        super().__init__(parent)
        self.setObjectName("ConverterView")
        self.category = category
        self._init_ui()

    def set_category(self, category: str):
        self.category = category
        self._populate_units()
        self._calculate()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)

        # ─── SECTION 1: TOP UNIT INPUT ──────────────────────────────
        v1 = QVBoxLayout()
        v1.setSpacing(4)
        self.input1 = QLineEdit("1")
        self.input1.setProperty("class", "converterInput")
        self.input1.textChanged.connect(self._on_input1_changed)
        v1.addWidget(self.input1)

        self.combo1 = QComboBox()
        self.combo1.setProperty("class", "unitCombo")
        self.combo1.currentIndexChanged.connect(self._calculate)
        v1.addWidget(self.combo1)
        layout.addLayout(v1)

        # ─── SECTION 2: EQUALS DIVIDER / ARROW ──────────────────────
        equals_lbl = QLabel("=")
        equals_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #888; padding: 4px 0;")
        layout.addWidget(equals_lbl)

        # ─── SECTION 3: BOTTOM UNIT OUTPUT ──────────────────────────
        v2 = QVBoxLayout()
        v2.setSpacing(4)
        self.input2 = QLineEdit("1")
        self.input2.setProperty("class", "converterInput")
        self.input2.setReadOnly(True)
        v2.addWidget(self.input2)

        self.combo2 = QComboBox()
        self.combo2.setProperty("class", "unitCombo")
        self.combo2.currentIndexChanged.connect(self._calculate)
        v2.addWidget(self.combo2)
        layout.addLayout(v2)

        # ─── SECTION 4: MINI NUMPAD FOR TOUCH / MOUSE ───────────────
        grid = QGridLayout()
        grid.setSpacing(2)
        key_map = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["C", "0", "."]
        ]
        for r, row in enumerate(key_map):
            for c, key in enumerate(row):
                btn = QPushButton(key)
                btn.setProperty("class", "calcKey numKey" if key.isdigit() or key == "." else "calcKey fnKey")
                btn.setFixedHeight(44)
                btn.clicked.connect(lambda _, k=key: self._on_key_clicked(k))
                grid.addWidget(btn, r, c)
        layout.addLayout(grid)

        self._populate_units()
        self._calculate()

    def _populate_units(self):
        self.combo1.blockSignals(True)
        self.combo2.blockSignals(True)
        self.combo1.clear()
        self.combo2.clear()

        if self.category == "Temperature":
            units = ["Celsius", "Fahrenheit", "Kelvin"]
        else:
            factors = CONVERSION_FACTORS.get(self.category, CONVERSION_FACTORS["Length"])
            units = list(factors.keys())

        for u in units:
            self.combo1.addItem(u)
            self.combo2.addItem(u)

        if len(units) > 1:
            self.combo2.setCurrentIndex(1)

        self.combo1.blockSignals(False)
        self.combo2.blockSignals(False)

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
        else:
            factors = CONVERSION_FACTORS.get(self.category, CONVERSION_FACTORS["Length"])
            f1 = factors.get(unit1, 1.0)
            f2 = factors.get(unit2, 1.0)
            # base = val * f1; result = base / f2
            result = (val * f1) / f2

        if abs(result - round(result)) < 1e-9:
            self.input2.setText(str(int(round(result))))
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

