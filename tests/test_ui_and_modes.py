"""
Comprehensive UI & Interaction Tests for Programmer Mode & Date Calculation.
Tests actual button interactions and UI component updates via PyQt6.
"""

import sys
import unittest
from datetime import date
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import QApplication

from src.core.engine import MathEngine
from src.core.state import CalculatorState
from src.database.history_db import HistoryDB
from src.ui.keypad_widget import KeypadWidget
from src.ui.date_calc_view import DateCalcView

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestProgrammerKeypadAndState(unittest.TestCase):
    def setUp(self):
        self.db = HistoryDB(":memory:")
        self.engine = MathEngine()
        self.recorded_states = []

        def on_change(**kwargs):
            self.recorded_states.append(kwargs)

        self.state = CalculatorState(self.engine, self.db, on_change)
        self.keypad = KeypadWidget(mode="Programmer")

        # Wire keypad signals to state just like MainWindow does
        self.keypad.digitClicked.connect(self.state.input_digit)
        self.keypad.operatorClicked.connect(self.state.input_operator)
        self.keypad.unaryFunctionClicked.connect(self.state.input_unary_operation)
        self.keypad.equalsClicked.connect(self.state.evaluate)
        self.keypad.clearClicked.connect(self.state.clear_all)
        self.keypad.clearEntryClicked.connect(self.state.clear_entry)
        self.keypad.backspaceClicked.connect(self.state.backspace)

    def tearDown(self):
        self.db.close()

    def _click_button(self, label: str):
        btn = self.keypad.button_map.get(label)
        self.assertIsNotNone(btn, f"Button '{label}' not found in Programmer keypad")
        btn.click()

    def test_modulo_ui_flow(self):
        # 1 0 mod 3 = -> 1
        self._click_button("1")
        self._click_button("0")
        self.state.input_operator("mod")  # mod op
        self._click_button("3")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "1")
        self.assertEqual(self.state.pinned_expression, "10 mod 3 =")

    def test_bitwise_and_ui_flow(self):
        # 12 AND 5 = -> 4
        self._click_button("1")
        self._click_button("2")
        self._click_button("AND")
        self._click_button("5")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "4")
        self.assertEqual(self.state.pinned_expression, "12 AND 5 =")

    def test_bitwise_or_ui_flow(self):
        # 12 OR 3 = -> 15
        self._click_button("1")
        self._click_button("2")
        self._click_button("OR")
        self._click_button("3")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "15")

    def test_bitwise_xor_ui_flow(self):
        # 12 XOR 5 = -> 9
        self._click_button("1")
        self._click_button("2")
        self._click_button("XOR")
        self._click_button("5")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "9")

    def test_shift_left_ui_flow(self):
        # 4 Lsh 2 = -> 16
        self._click_button("4")
        self._click_button("Lsh")
        self._click_button("2")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "16")

    def test_shift_right_ui_flow(self):
        # 16 Rsh 2 = -> 4
        self._click_button("1")
        self._click_button("6")
        self._click_button("Rsh")
        self._click_button("2")
        self._click_button("=")
        self.assertEqual(self.state.active_token, "4")


class TestDateCalcViewUI(unittest.TestCase):
    def setUp(self):
        self.view = DateCalcView()

    def test_date_diff_ui_interaction(self):
        self.view.mode_combo.setCurrentIndex(0)
        self.view.from_date_edit.setDate(QDate(2026, 11, 1))
        self.view.to_date_edit.setDate(QDate(2026, 11, 20))

        self.assertEqual(self.view.diff_headline.text(), "2 weeks, 5 days")
        self.assertEqual(self.view.diff_total_days.text(), "19 days")

        # Test same date
        self.view.to_date_edit.setDate(QDate(2026, 11, 1))
        self.assertEqual(self.view.diff_headline.text(), "Same date")
        self.assertEqual(self.view.diff_total_days.text(), "0 days")

    def test_add_subtract_ui_interaction(self):
        self.view.mode_combo.setCurrentIndex(1)
        self.view.addsub_from_edit.setDate(QDate(2026, 11, 5))
        self.view.radio_add.setChecked(True)
        self.view.spin_years.setValue(1)
        self.view.spin_months.setValue(2)
        self.view.spin_days.setValue(10)

        # 2026-11-05 + 1y 2m 10d = 2028-01-15 (Saturday)
        self.assertEqual(self.view.addsub_headline.text(), "Saturday, January 15, 2028")

        # Toggle to Subtract
        self.view.radio_sub.setChecked(True)
        # 2026-11-05 - 1y 2m 10d = 2025-08-26 (Tuesday)
        self.assertEqual(self.view.addsub_headline.text(), "Tuesday, August 26, 2025")


if __name__ == "__main__":
    unittest.main()

