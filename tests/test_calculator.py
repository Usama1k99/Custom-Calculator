"""
Exhaustive Unit & Edge Case Test Suite for Custom-Calculator.
Run via: python tests/test_calculator.py
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from decimal import Decimal
from src.core.engine import MathEngine, AngleMode
from src.database.history_db import HistoryDB
from src.core.state import CalculatorState
from src.core.config import ConfigManager


class TestMathEngineEdgeCases(unittest.TestCase):
    def setUp(self):
        self.engine = MathEngine()

    def test_basic_arithmetic(self):
        ok, res, _ = self.engine.evaluate("2 + 3 * 4")
        self.assertTrue(ok)
        self.assertEqual(res, "14")

    def test_division_by_zero(self):
        ok, res, _ = self.engine.evaluate("10 / 0")
        self.assertFalse(ok)
        self.assertEqual(res, "Cannot divide by zero")

    def test_negative_square_root(self):
        ok, res, _ = self.engine.evaluate("sqrt(-9)")
        self.assertFalse(ok)
        self.assertEqual(res, "Invalid input")

    def test_log_of_zero(self):
        ok, res, _ = self.engine.evaluate("log(0)")
        self.assertFalse(ok)
        self.assertEqual(res, "Invalid input")

    def test_tan_90_degrees(self):
        self.engine.set_angle_mode(AngleMode.DEG)
        ok, res, _ = self.engine.evaluate("tan(90)")
        self.assertFalse(ok)
        self.assertEqual(res, "Invalid input")

    def test_overflow_protection(self):
        ok, res, _ = self.engine.evaluate("10 ** 100000")
        self.assertFalse(ok)
        self.assertEqual(res, "Overflow")

    def test_unclosed_parentheses_auto_balance(self):
        # "(5 + 3 * (2 + 1" -> auto-balances to "(5 + 3 * (2 + 1))" = 14
        ok, res, _ = self.engine.evaluate("(5 + 3 * (2 + 1")
        self.assertTrue(ok)
        self.assertEqual(res, "14")

    def test_incomplete_expression_trailing_operator(self):
        # "5 +" -> repeats operand "5 + 5" = 10 (Windows Calc behavior)
        ok, res, _ = self.engine.evaluate("5 +")
        self.assertTrue(ok)
        self.assertEqual(res, "10")

    def test_floating_point_exactness(self):
        # 0.1 + 0.2 must equal 0.3 exactly
        ok, res, _ = self.engine.evaluate("0.1 + 0.2")
        self.assertTrue(ok)
        self.assertEqual(res, "0.3")

    def test_percentage_math(self):
        ok, res, _ = self.engine.evaluate("100 + 10%")
        self.assertTrue(ok)
        self.assertEqual(res, "110")

        ok, res, _ = self.engine.evaluate("500 - 15%")
        self.assertTrue(ok)
        self.assertEqual(res, "425")


class TestCalculatorStateEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "data/unit_test_state.db"
        p = Path(self.test_db_path)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

        self.engine = MathEngine()
        self.db = HistoryDB(self.test_db_path)
        self.events = []

        def callback(is_evaluated, expression_trail, active_token, live_preview):
            self.events.append({
                "is_evaluated": is_evaluated,
                "trail": expression_trail,
                "token": active_token,
                "preview": live_preview
            })

        self.state = CalculatorState(self.engine, self.db, callback)

    def tearDown(self):
        try:
            p = Path(self.test_db_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    def test_multiple_decimals_blocked(self):
        self.state.input_digit("5")
        self.state.input_digit(".")
        self.state.input_digit("2")
        self.state.input_digit(".")  # Blocked!
        self.state.input_digit("4")
        self.assertEqual(self.state.active_token, "5.24")

    def test_consecutive_operator_replacement(self):
        self.state.input_digit("5")
        self.state.input_operator("+")
        self.state.input_operator("×")  # Replaces +
        self.state.input_digit("3")
        self.state.evaluate()
        last = self.events[-1]
        self.assertEqual(last["token"], "15")

    def test_repeated_equals_chaining(self):
        # 5 + 3 = 8
        self.state.input_digit("5")
        self.state.input_operator("+")
        self.state.input_digit("3")
        self.state.evaluate()
        self.assertEqual(self.events[-1]["token"], "8")

        # Press '=' again -> 8 + 3 = 11
        self.state.evaluate()
        self.assertEqual(self.events[-1]["token"], "11")

        # Press '=' again -> 11 + 3 = 14
        self.state.evaluate()
        self.assertEqual(self.events[-1]["token"], "14")

    def test_clear_entry_vs_clear_all(self):
        # 10 + 20
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("2")
        self.state.input_digit("0")

        # Press CE -> clears only "20", leaves "10 +"
        self.state.clear_entry()
        self.assertEqual(self.state.active_token, "0")
        self.assertTrue("10 +" in self.state.expression_trail)

        # Type "5" and evaluate -> 10 + 5 = 15
        self.state.input_digit("5")
        self.state.evaluate()
        self.assertEqual(self.events[-1]["token"], "15")

    def test_unary_operations(self):
        # 16 -> ²√x -> 4
        self.state.input_digit("1")
        self.state.input_digit("6")
        self.state.input_unary_operation("sqrt")
        self.assertEqual(self.state.active_token, "4")

        # 4 -> x² -> 16
        self.state.input_unary_operation("sqr")
        self.assertEqual(self.state.active_token, "16")

        # 0 -> 1/x -> Cannot divide by zero
        self.state.clear_all()
        self.state.input_digit("0")
        self.state.input_unary_operation("recip")
        self.assertTrue("Cannot divide by zero" in self.state.active_token)


class TestConfigPersistence(unittest.TestCase):
    def test_config_save_and_load(self):
        test_cfg_path = "data/test_config.json"
        cfg = ConfigManager(test_cfg_path)
        cfg.set("theme_id", "dark_monokai")
        cfg.set("mode", "Scientific")
        cfg.save()

        cfg2 = ConfigManager(test_cfg_path)
        self.assertEqual(cfg2.get("theme_id"), "dark_monokai")
        self.assertEqual(cfg2.get("mode"), "Scientific")

        # Cleanup
        try:
            Path(test_cfg_path).unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
