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
        self.engine = MathEngine()
        self.db = HistoryDB(":memory:")
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
        self.db.close()

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


class TestPercentageAndExpressionFixes(unittest.TestCase):
    def setUp(self):
        self.engine = MathEngine()
        self.db = HistoryDB(":memory:")
        self.events = []
        self.state = CalculatorState(
            self.engine, self.db,
            lambda is_evaluated, expression_trail, active_token, live_preview:
                self.events.append({
                    "is_evaluated": is_evaluated,
                    "trail": expression_trail,
                    "token": active_token,
                    "preview": live_preview
                })
        )

    def test_percentage_subtraction_user_scenario(self):
        # User scenario: 20 = - 10 % =
        # 1. 20 =
        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "20")

        # 2. -
        self.state.input_operator("-")
        self.assertEqual(self.state.expression_trail, "20 - ")

        # 3. 10
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.assertEqual(self.state.active_token, "10")

        # 4. % (10% of 20 = 2)
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "2")
        self.assertEqual(self.state.expression_trail, "20 - ")
        self.assertEqual(self.events[-1]["preview"], "18")

        # 5. = (20 - 2 = 18)
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "18")
        self.assertEqual(self.state.last_result, Decimal("18"))

    def test_percentage_addition(self):
        # 100 + 10 % = 110
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "10")
        self.assertEqual(self.events[-1]["preview"], "110")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "110")

    def test_percentage_multiplication_and_division(self):
        # 20 * 10 % = 2
        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.input_operator("*")
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.events[-1]["preview"], "2")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "2")

        # 20 / 10 % = 200
        self.state.clear_all()
        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.input_operator("/")
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.events[-1]["preview"], "200")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "200")

    def test_percentage_standalone(self):
        # 50 % = 0.5
        self.state.input_digit("5")
        self.state.input_digit("0")
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "0.5")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "0.5")

    def test_percentage_chained_accumulated(self):
        # 10 + 20 - 10 % = 27 (10% of 30 = 3, 30 - 3 = 27)
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.input_operator("-")
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_percentage()
        self.assertEqual(self.state.active_token, "3")
        self.assertEqual(self.events[-1]["preview"], "27")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "27")

    def test_engine_expression_fixes(self):
        # Leading zero normalization
        self.assertEqual(self.engine.evaluate("05 + 2")[1], "7")
        self.assertEqual(self.engine.evaluate("007 * 3")[1], "21")

        # Comma formatted numbers
        self.assertEqual(self.engine.evaluate("1,000 + 200")[1], "1,200")

        # Factorial exclamation mark
        self.assertEqual(self.engine.evaluate("5!")[1], "120")
        self.assertEqual(self.engine.evaluate("(3+2)!")[1], "120")

        # Implicit multiplication with functions
        self.assertEqual(self.engine.evaluate("2sqrt(4)")[1], "4")
        self.assertEqual(self.engine.evaluate("(2)sqrt(4)")[1], "4")

        # Contextual percentages in expressions
        self.assertEqual(self.engine.evaluate("(50 + 50) - 10%")[1], "90")
        self.assertEqual(self.engine.evaluate("(20 + 30)%")[1], "0.5")

    def test_large_number_scientific_notation(self):
        # fact(90) should format in clean scientific notation, not 140 digits overflowing text field
        succ, formatted, _ = self.engine.evaluate("fact(90)", mode="Scientific")
        self.assertTrue(succ)
        self.assertTrue("e+" in formatted)
        self.assertLess(len(formatted), 30)

        # 10^16 should format in scientific notation (>= 1e16)
        succ, formatted, _ = self.engine.evaluate("10^16", mode="Scientific")
        self.assertTrue(succ)
        self.assertTrue("e+" in formatted)

        # 10^15 should be standard integer grouping (16 digits total: 1,000,000,000,000,000)
        succ, formatted, _ = self.engine.evaluate("10^15", mode="Scientific")
        self.assertTrue(succ)
        self.assertEqual(formatted, "1,000,000,000,000,000")

    def test_digit_capping_16_digits(self):
        # In Standard / Scientific mode, active token cannot exceed 16 digits
        self.state.mode = "Scientific"
        self.state.clear_all()
        for i in range(16):
            self.state.input_digit("9")
        self.assertEqual(self.state.active_token, "9999999999999999")
        self.assertEqual(len(self.state.active_token), 16)

        # 17th digit should be ignored
        self.state.input_digit("9")
        self.assertEqual(self.state.active_token, "9999999999999999")
        self.assertEqual(len(self.state.active_token), 16)

        # Starting fresh after evaluate allows new 16 digits
        self.state.evaluate()
        self.state.input_digit("1")
        self.assertEqual(self.state.active_token, "1")

    def test_parentheses_image_2_scenario(self):
        # Replicating Image 2: ( ( ( ( 0 ) ) ) followed by ( (
        self.state.mode = "Scientific"
        self.state.clear_all()

        # Press ( 4 times
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "(")
        self.assertEqual(self.state.open_parentheses_count, 1)

        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "((")
        self.assertEqual(self.state.open_parentheses_count, 2)

        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "(((")
        self.assertEqual(self.state.open_parentheses_count, 3)

        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "((((")
        self.assertEqual(self.state.open_parentheses_count, 4)

        # Press ) 3 times
        self.state.input_parenthesis(")")
        self.assertEqual(self.state.expression_trail, "((((0)")
        self.assertEqual(self.state.open_parentheses_count, 3)

        self.state.input_parenthesis(")")
        self.assertEqual(self.state.expression_trail, "((((0))")
        self.assertEqual(self.state.open_parentheses_count, 2)

        self.state.input_parenthesis(")")
        self.assertEqual(self.state.expression_trail, "((((0)))")
        self.assertEqual(self.state.open_parentheses_count, 1)

        # Press ( -> Auto inserts "× (" beside closed bracket
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "((((0))) × (")
        self.assertEqual(self.state.open_parentheses_count, 2)

        # Press ( again -> Appends "("
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "((((0))) × ((")
        self.assertEqual(self.state.open_parentheses_count, 3)
        self.assertEqual(self.state.active_token, "0")

    def test_parentheses_auto_multiplication_with_number(self):
        # 5 then ( -> "5 × ("
        self.state.mode = "Scientific"
        self.state.clear_all()

        self.state.input_digit("5")
        self.assertEqual(self.state.active_token, "5")

        self.state.input_parenthesis("(")
        self.assertEqual(self.state.expression_trail, "5 × (")
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.assertEqual(self.state.active_token, "0")

        self.state.input_digit("2")
        self.state.input_operator("+")
        self.state.input_digit("3")
        self.state.input_parenthesis(")")
        self.assertEqual(self.state.expression_trail, "5 × (2 + 3)")
        self.assertEqual(self.state.open_parentheses_count, 0)
        self.assertEqual(self.state.active_token, "5")

        self.state.evaluate()
        self.assertEqual(self.state.active_token, "25")
        self.assertEqual(self.state.pinned_expression, "5 × (2 + 3) =")

    def test_parentheses_auto_close_on_equals(self):
        # 5 × (2 + 3 without typing ) then = auto closes parentheses
        self.state.mode = "Scientific"
        self.state.clear_all()

        self.state.input_digit("5")
        self.state.input_parenthesis("(")
        self.state.input_digit("2")
        self.state.input_operator("+")
        self.state.input_digit("3")
        self.assertEqual(self.state.open_parentheses_count, 1)

        self.state.evaluate()
        self.assertEqual(self.state.active_token, "25")
        self.assertEqual(self.state.pinned_expression, "5 × (2 + 3) =")
        self.assertEqual(self.state.open_parentheses_count, 0)

    def test_factorial_unary_operation(self):
        self.state.mode = "Scientific"
        self.state.clear_all()
        self.state.input_digit("5")
        self.state.input_unary_operation("fact")
        self.assertEqual(self.state.active_token, "120")
        self.assertEqual(self.state.current_operand_repr, "fact(5)")

    def test_bracket_cap_at_50(self):
        self.state.mode = "Scientific"
        self.state.clear_all()
        for _ in range(65):
            self.state.input_parenthesis("(")
        self.assertEqual(self.state.open_parentheses_count, 50)
        # Verify 50 is preserved and further opens are blocked
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.open_parentheses_count, 50)

    def test_parentheses_backspace_sync(self):
        self.state.mode = "Scientific"
        self.state.clear_all()

        # 1. Type ( and immediately backspace -> resets trail and open count
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.assertEqual(self.state.expression_trail, "(")
        self.state.backspace()
        self.assertEqual(self.state.open_parentheses_count, 0)
        self.assertEqual(self.state.expression_trail, "")

        # 2. Type (( and backspace twice -> 2 -> 1 -> 0
        self.state.input_parenthesis("(")
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.open_parentheses_count, 2)
        self.state.backspace()
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.assertEqual(self.state.expression_trail, "(")
        self.state.backspace()
        self.assertEqual(self.state.open_parentheses_count, 0)
        self.assertEqual(self.state.expression_trail, "")

        # 3. 5 × ( and backspace -> removes paren and multiplier
        self.state.input_digit("5")
        self.state.input_parenthesis("(")
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.assertEqual(self.state.expression_trail, "5 × (")
        self.state.backspace()
        self.assertEqual(self.state.open_parentheses_count, 0)
        self.assertEqual(self.state.expression_trail, "5")

        # 4. ( 5 then backspace backspace -> backspacing 5 resets active_token to 0, next backspace removes (
        self.state.clear_all()
        self.state.input_parenthesis("(")
        self.state.input_digit("5")
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.assertEqual(self.state.active_token, "5")
        self.state.backspace()
        self.assertEqual(self.state.active_token, "0")
        self.assertEqual(self.state.open_parentheses_count, 1)
        self.state.backspace()
        self.assertEqual(self.state.open_parentheses_count, 0)
        self.assertEqual(self.state.expression_trail, "")


if __name__ == "__main__":
    unittest.main()
