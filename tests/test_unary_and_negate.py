"""
Unit tests for +/- (negate) button behavior and unary operator ribbon chaining.
Verifies proper ribbon expression generation, preview synchronization,
and negative decimal number formatting without sign truncation.
"""

import unittest
from decimal import Decimal
from src.core.engine import MathEngine
from src.core.state import CalculatorState
from src.database.history_db import HistoryDB


class TestUnaryAndNegate(unittest.TestCase):
    def setUp(self):
        self.db = HistoryDB(":memory:")
        self.engine = MathEngine()
        self.history = []

        def on_change(**kwargs):
            self.history.append(kwargs)

        self.state = CalculatorState(self.engine, self.db, on_change)

    def test_negative_decimal_format_number(self):
        """Verifies that format_number does not drop negative sign on numbers between -1 and 0."""
        cases = [
            (Decimal("-0.95"), "-0.95"),
            (Decimal("-0.005"), "-0.005"),
            (Decimal("-0.5"), "-0.5"),
            (Decimal("-1.5"), "-1.5"),
            (Decimal("-1234.56"), "-1,234.56"),
            (Decimal("0"), "0"),
            (Decimal("-0"), "0"),
        ]
        for val, expected in cases:
            self.assertEqual(self.engine.format_number(val), expected)

    def test_negate_standalone_decimal_preview(self):
        """Verifies -0.95 has no phantom preview and preserves sign on equals."""
        # Key in 0 . 9 5 +/-
        self.state.input_digit("0")
        self.state.input_digit(".")
        self.state.input_digit("9")
        self.state.input_digit("5")
        self.assertEqual(self.state.active_token, "0.95")
        self.assertEqual(self.history[-1]["live_preview"], "")

        # Negate
        self.state.negate()
        self.assertEqual(self.state.active_token, "-0.95")
        # Critical test: ghost preview MUST be empty, NOT "= 0.95"!
        self.assertEqual(self.history[-1]["live_preview"], "")

        # Press equals: sign must be preserved!
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "-0.95")
        self.assertEqual(self.history[-1]["expression_trail"], "-0.95 =")
        self.assertEqual(self.history[-1]["live_preview"], "")

        # Post-eval negate
        self.state.negate()
        self.assertEqual(self.state.active_token, "0.95")

    def test_negate_in_binary_operation(self):
        """Verifies 10 + 5 -> negate -> display -5, ribbon 10 + negate(5), preview = 5, equals gives 5."""
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("5")
        self.assertEqual(self.history[-1]["live_preview"], "15")

        self.state.negate()
        self.assertEqual(self.state.active_token, "-5")
        self.assertEqual(self.history[-1]["expression_trail"], "10 + negate(5)")
        self.assertEqual(self.history[-1]["live_preview"], "5")

        self.state.evaluate()
        self.assertEqual(self.state.active_token, "5")
        self.assertEqual(self.history[-1]["expression_trail"], "10 + negate(5) =")
        self.assertEqual(self.history[-1]["live_preview"], "")

    def test_unary_chaining_standard(self):
        """Verifies 10 -> 1/x -> sqr -> sqrt chains ribbon representations like Windows Calculator."""
        self.state.input_digit("1")
        self.state.input_digit("0")

        # 1/x (recip)
        self.state.input_unary_operation("recip")
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.history[-1]["expression_trail"], "1/(10)")
        self.assertEqual(self.history[-1]["live_preview"], "")

        # x² (sqr)
        self.state.input_unary_operation("sqr")
        self.assertEqual(self.state.active_token, "0.01")
        self.assertEqual(self.history[-1]["expression_trail"], "sqr(1/(10))")
        self.assertEqual(self.history[-1]["live_preview"], "")

        # √x (sqrt)
        self.state.input_unary_operation("sqrt")
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.history[-1]["expression_trail"], "√(sqr(1/(10)))")
        self.assertEqual(self.history[-1]["live_preview"], "")

    def test_unary_chaining_with_binary_operator(self):
        """Verifies unary chaining after binary operator: 5 + 10 -> 1/x -> sqr -> sqrt -> + 2 ="""
        self.state.input_digit("5")
        self.state.input_operator("+")
        self.state.input_digit("1")
        self.state.input_digit("0")

        self.state.input_unary_operation("recip")
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.history[-1]["expression_trail"], "5 + 1/(10)")
        self.assertEqual(self.history[-1]["live_preview"], "5.1")

        self.state.input_unary_operation("sqr")
        self.assertEqual(self.state.active_token, "0.01")
        self.assertEqual(self.history[-1]["expression_trail"], "5 + sqr(1/(10))")
        self.assertEqual(self.history[-1]["live_preview"], "5.01")

        self.state.input_unary_operation("sqrt")
        self.assertEqual(self.state.active_token, "0.1")
        self.assertEqual(self.history[-1]["expression_trail"], "5 + √(sqr(1/(10)))")
        self.assertEqual(self.history[-1]["live_preview"], "5.1")

        # Add 2
        self.state.input_operator("+")
        self.assertEqual(self.history[-1]["expression_trail"], "5 + √(sqr(1/(10))) + ")
        self.state.input_digit("2")
        self.assertEqual(self.history[-1]["live_preview"], "7.1")

        # Evaluate
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "7.1")
        self.assertEqual(self.history[-1]["expression_trail"], "5 + √(sqr(1/(10))) + 2 =")

    def test_unary_programmer_not(self):
        """Verifies NOT in Programmer mode wraps and evaluates correctly."""
        self.state.mode = "Programmer"
        self.state.input_digit("5")
        self.state.input_unary_operation("NOT")
        self.assertEqual(self.state.active_token, "-6")
        self.assertEqual(self.history[-1]["expression_trail"], "NOT(5)")

    def test_digit_after_unary_starts_fresh_number(self):
        """Verifies typing a digit after a unary operation starts a new number instead of appending."""
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_unary_operation("recip")  # 0.1
        self.assertEqual(self.state.active_token, "0.1")

        # Type digit 5
        self.state.input_digit("5")
        self.assertEqual(self.state.active_token, "5")
        self.assertIsNone(self.state.current_operand_repr)


if __name__ == "__main__":
    unittest.main()

