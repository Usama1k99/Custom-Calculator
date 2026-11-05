"""
Unit and Interaction Tests for Windows Calculator-Style Scientific Mode.
Validates all trigonometric, hyperbolic, exponential, rounding, and conversion functions,
plus popover and 2nd mode toggling in KeypadWidget.
"""

import sys
import unittest
from PyQt6.QtWidgets import QApplication

from src.core.engine import MathEngine, AngleMode
from src.core.state import CalculatorState
from src.database.history_db import HistoryDB
from src.ui.keypad_widget import KeypadWidget

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestScientificMathEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MathEngine()

    def test_trig_deg_mode(self):
        self.engine.set_angle_mode(AngleMode.DEG)
        ok, res, _ = self.engine.evaluate("sin(30)")
        self.assertTrue(ok)
        self.assertEqual(res, "0.5")

        ok, res, _ = self.engine.evaluate("cos(60)")
        self.assertTrue(ok)
        self.assertEqual(res, "0.5")

        ok, res, _ = self.engine.evaluate("tan(45)")
        self.assertTrue(ok)
        self.assertEqual(res, "1")

        ok, res, _ = self.engine.evaluate("sec(60)")
        self.assertTrue(ok)
        self.assertEqual(res, "2")

        ok, res, _ = self.engine.evaluate("csc(30)")
        self.assertTrue(ok)
        self.assertEqual(res, "2")

        ok, res, _ = self.engine.evaluate("cot(45)")
        self.assertTrue(ok)
        self.assertEqual(res, "1")

    def test_trig_rad_and_grad_mode(self):
        self.engine.set_angle_mode(AngleMode.RAD)
        import math
        ok, res, _ = self.engine.evaluate(f"sin({math.pi / 2})")
        self.assertTrue(ok)
        self.assertEqual(res, "1")

        self.engine.set_angle_mode(AngleMode.GRAD)
        ok, res, _ = self.engine.evaluate("sin(100)")  # 100 grad = 90 deg
        self.assertTrue(ok)
        self.assertEqual(res, "1")

    def test_hyperbolic_functions(self):
        ok, res, _ = self.engine.evaluate("sinh(0)")
        self.assertTrue(ok)
        self.assertEqual(res, "0")

        ok, res, _ = self.engine.evaluate("cosh(0)")
        self.assertTrue(ok)
        self.assertEqual(res, "1")

        ok, res, _ = self.engine.evaluate("tanh(0)")
        self.assertTrue(ok)
        self.assertEqual(res, "0")

    def test_rounding_and_dms_functions(self):
        ok, res, _ = self.engine.evaluate("floor(4.9)")
        self.assertTrue(ok)
        self.assertEqual(res, "4")

        ok, res, _ = self.engine.evaluate("ceil(4.1)")
        self.assertTrue(ok)
        self.assertEqual(res, "5")

        ok, res, _ = self.engine.evaluate("dms(45.5)")
        self.assertTrue(ok)
        self.assertEqual(res, "45.3")

        ok, res, _ = self.engine.evaluate("deg(45.3)")
        self.assertTrue(ok)
        self.assertEqual(res, "45.5")

    def test_random_function(self):
        ok, res, val = self.engine.evaluate("rand()")
        self.assertTrue(ok)
        self.assertGreaterEqual(float(val), 0.0)
        self.assertLess(float(val), 1.0)


class TestScientificKeypadInteractions(unittest.TestCase):
    def setUp(self):
        self.db = HistoryDB(":memory:")
        self.engine = MathEngine()
        self.state = CalculatorState(self.engine, self.db, lambda **kw: None)
        self.keypad = KeypadWidget(mode="Scientific")

        # Wire signals
        self.keypad.digitClicked.connect(self.state.input_digit)
        self.keypad.operatorClicked.connect(self.state.input_operator)
        self.keypad.unaryFunctionClicked.connect(self.state.input_unary_operation)
        self.keypad.equalsClicked.connect(self.state.evaluate)

    def tearDown(self):
        self.db.close()

    def test_angle_mode_cycle(self):
        self.assertEqual(self.keypad._angle_mode, "DEG")
        self.keypad.btn_angle_mode.click()
        self.assertEqual(self.keypad._angle_mode, "RAD")
        self.keypad.btn_angle_mode.click()
        self.assertEqual(self.keypad._angle_mode, "GRAD")
        self.keypad.btn_angle_mode.click()
        self.assertEqual(self.keypad._angle_mode, "DEG")

    def test_trig_popover_execution(self):
        # Open trig popover
        self.keypad.btn_trig.click()
        self.assertFalse(self.keypad.trig_popover.isHidden())

        # Click sin(30)
        self.state.input_digit("3")
        self.state.input_digit("0")
        self.keypad.trig_buttons["sin"].click()

        # Popover auto-closes and calculates
        self.assertTrue(self.keypad.trig_popover.isHidden())
        self.assertEqual(self.state.active_token, "0.5")

    def test_function_popover_execution(self):
        # Open function popover
        self.keypad.btn_func.click()
        self.assertFalse(self.keypad.func_popover.isHidden())

        # Test floor(4.9)
        self.state.input_digit("4")
        self.state.input_digit(".")
        self.state.input_digit("9")
        self.keypad._on_func_key_clicked("floor")

        self.assertTrue(self.keypad.func_popover.isHidden())
        self.assertEqual(self.state.active_token, "4")

    def test_2nd_scientific_key_toggle(self):
        self.assertFalse(self.keypad._is_2nd_active)
        btn_sqr = self.keypad.button_map["x²"]
        self.assertEqual(btn_sqr.text(), "x²")

        # Toggle 2nd
        self.keypad.button_map["2ⁿᵈ"].click()
        self.assertTrue(self.keypad._is_2nd_active)
        self.assertEqual(btn_sqr.text(), "x³")

        # Toggle 2nd back
        self.keypad.button_map["2ⁿᵈ"].click()
        self.assertFalse(self.keypad._is_2nd_active)
        self.assertEqual(btn_sqr.text(), "x²")


if __name__ == "__main__":
    unittest.main()
