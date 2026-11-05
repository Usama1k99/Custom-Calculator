"""
Exhaustive Stress Test Suite for All Expression-Based Modes:
- Standard Mode: Arithmetic, Precedence, Associativity, Percentages, Precision, Chaining
- Scientific Mode: Trigonometry, Hyperbolics, Powers, Roots, Logarithms, Factorials, DMS, Constants
- Programmer Mode: Bitwise Logic (AND/OR/XOR/NOT), Bit Shifts, Hexadecimal Literals, Modulo
- Graphing Mode: Expression Compilation, Implicit Multiplication, Asymptotes, Parameters, KGF
- UI Level Stress: Keypad Button Simulation, Live Ghost Previews, Pinned Expressions, Error Recovery
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import math
from decimal import Decimal
from PyQt6.QtWidgets import QApplication

from src.core.engine import MathEngine, AngleMode
from src.core.state import CalculatorState
from src.core.graph_engine import GraphFunction
from src.ui.main_window import MainWindow
from src.ui.graph_canvas import GraphCanvas
from src.ui.graphing_view import GraphingView

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestStandardModeExpressions(unittest.TestCase):
    """Exhaustive tests for Standard Mode calculations and edge cases."""

    def setUp(self):
        self.engine = MathEngine()

    def test_basic_arithmetic(self):
        cases = [
            ("1 + 1", "2"),
            ("10 - 4", "6"),
            ("6 * 7", "42"),
            ("8 / 4", "2"),
            ("0 + 0", "0"),
            ("123456789 + 987654321", "1,111,111,110"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_order_of_operations_and_precedence(self):
        cases = [
            ("2 + 3 * 4", "14"),
            ("3 * 4 + 2", "14"),
            ("10 - 2 * 3", "4"),
            ("20 / 4 + 2 * 3", "11"),
            ("2 + 3 * 4 - 5 / 5", "13"),
            ("2 ^ 3 * 2", "16"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_associativity_left_and_right(self):
        # Left-associative division and subtraction
        success, res1, _ = self.engine.evaluate("8 / 2 / 2")
        self.assertEqual(res1, "2")  # (8/2)/2 = 2, not 8/(2/2) = 8

        success, res2, _ = self.engine.evaluate("10 - 5 - 2")
        self.assertEqual(res2, "3")  # (10-5)-2 = 3

        # Right-associative exponentiation: 2 ^ 3 ^ 2 = 2 ^ 9 = 512
        success, res3, _ = self.engine.evaluate("2 ^ 3 ^ 2")
        self.assertEqual(res3, "512")

    def test_parentheses_nesting_and_repair(self):
        cases = [
            ("(2 + 3) * 4", "20"),
            ("((1 + 2) * (3 + 4)) / ((5 - 1) * 2)", "2.625"),
            ("((((1 + 2) * 3) + 4) * 5)", "65"),
            # Unclosed parentheses auto-repair
            ("(5 + 2 * (3 + 1", "13"),
            ("((10 + 20", "30"),
            # Empty parentheses cleanup
            ("5 + () + 2", "7"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_implicit_multiplication(self):
        cases = [
            ("2(3)", "6"),
            ("(2)(3)", "6"),
            ("4(5 + 2)", "28"),
            ("(3 + 1)(2 + 2)", "16"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_percentages(self):
        cases = [
            # Additive / Subtractive percentages
            ("100 + 10%", "110"),
            ("100 - 25%", "75"),
            ("50 + 20%", "60"),
            ("200 - 15%", "170"),
            # Multiplicative / Divisive
            ("200 * 15%", "30"),
            ("50 / 50%", "100"),
            # Standalone percentages
            ("25%", "0.25"),
            ("100%", "1"),
            ("0.5%", "0.005"),
            # Modulo vs percentage
            ("10 % 3", "1"),
            ("17 mod 5", "2"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_floating_point_precision_and_no_drift(self):
        # Classic IEEE-754 drift pitfalls that Decimal eliminates
        success, res1, _ = self.engine.evaluate("0.1 + 0.2")
        self.assertEqual(res1, "0.3")

        success, res2, _ = self.engine.evaluate("1.0 - 0.9")
        self.assertEqual(res2, "0.1")

        success, res3, _ = self.engine.evaluate("0.7 + 0.1")
        self.assertEqual(res3, "0.8")

        success, res4, _ = self.engine.evaluate("0.3 - 0.2 - 0.1")
        self.assertEqual(res4, "0")

    def test_division_by_zero_and_domain_errors(self):
        err_cases = [
            "5 / 0",
            "0 / 0",
            "-10 / 0",
            "10 / (5 - 5)",
            "10 % 0",
            "10 mod 0",
        ]
        for expr in err_cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertFalse(success, f"Expected division by zero error for {expr}")
            self.assertIn("divide by zero", res.lower())

    def test_extreme_inputs_and_overflow(self):
        # Gigantic power overflow protection
        success, res, _ = self.engine.evaluate("2 ^ 50000")
        self.assertFalse(success)
        self.assertEqual(res, "Overflow")

        # Incomplete expression trailing operator repetition
        success, res, _ = self.engine.evaluate("5 +")
        self.assertTrue(success)
        self.assertEqual(res, "10")

        success, res, _ = self.engine.evaluate("8 *")
        self.assertTrue(success)
        self.assertEqual(res, "64")


class TestScientificModeExpressions(unittest.TestCase):
    """Exhaustive tests for Scientific Mode mathematical functions and domain limits."""

    def setUp(self):
        self.engine = MathEngine()

    def test_trigonometry_degree_mode(self):
        self.engine.set_angle_mode(AngleMode.DEG)
        cases = [
            ("sin(0)", "0"),
            ("sin(30)", "0.5"),
            ("sin(90)", "1"),
            ("sin(180)", "0"),  # Epsilon rounding to exact 0
            ("cos(0)", "1"),
            ("cos(60)", "0.5"),
            ("cos(90)", "0"),   # Epsilon rounding to exact 0
            ("cos(180)", "-1"),
            ("tan(0)", "0"),
            ("tan(45)", "1"),
            ("sec(0)", "1"),
            ("csc(90)", "1"),
            ("cot(45)", "1"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}: {res}")
            self.assertEqual(res, expected)

    def test_trigonometry_radian_and_gradian_modes(self):
        # Radians
        self.engine.set_angle_mode(AngleMode.RAD)
        success, res1, _ = self.engine.evaluate(f"sin({math.pi / 2})")
        self.assertTrue(success)
        self.assertEqual(res1, "1")

        success, res2, _ = self.engine.evaluate(f"cos({math.pi})")
        self.assertTrue(success)
        self.assertEqual(res2, "-1")

        # Gradians (100 grad = 90 deg = pi/2 rad)
        self.engine.set_angle_mode(AngleMode.GRAD)
        success, res3, _ = self.engine.evaluate("sin(100)")
        self.assertTrue(success)
        self.assertEqual(res3, "1")

        success, res4, _ = self.engine.evaluate("cos(200)")
        self.assertTrue(success)
        self.assertEqual(res4, "-1")

    def test_trigonometric_asymptotes_and_poles(self):
        self.engine.set_angle_mode(AngleMode.DEG)
        pole_cases = [
            "tan(90)",
            "tan(270)",
            "sec(90)",
            "csc(0)",
            "cot(0)",
            "cot(180)",
        ]
        for expr in pole_cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertFalse(success, f"Expected pole undefined error for {expr}")
            self.assertIn("invalid input", res.lower())

    def test_inverse_trigonometry_and_domains(self):
        self.engine.set_angle_mode(AngleMode.DEG)
        cases = [
            ("asin(0)", "0"),
            ("asin(0.5)", "30"),
            ("asin(1)", "90"),
            ("asin(-1)", "-90"),
            ("acos(1)", "0"),
            ("acos(0.5)", "60"),
            ("acos(0)", "90"),
            ("acos(-1)", "180"),
            ("atan(0)", "0"),
            ("atan(1)", "45"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

        # Domain boundary violations
        for bad_expr in ["asin(1.01)", "asin(-1.5)", "acos(2.0)", "acos(-1.1)", "asec(0.5)", "acsc(0.5)"]:
            success, res, _ = self.engine.evaluate(bad_expr)
            self.assertFalse(success, f"Expected domain error for {bad_expr}")

    def test_hyperbolic_functions(self):
        cases = [
            ("sinh(0)", "0"),
            ("cosh(0)", "1"),
            ("tanh(0)", "0"),
            ("sech(0)", "1"),
            ("asinh(0)", "0"),
            ("acosh(1)", "0"),
            ("atanh(0)", "0"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

        # Hyperbolic zero divisions and domain limits
        self.assertFalse(self.engine.evaluate("csch(0)")[0])
        self.assertFalse(self.engine.evaluate("coth(0)")[0])
        self.assertFalse(self.engine.evaluate("acosh(0.5)")[0])  # acosh domain x >= 1
        self.assertFalse(self.engine.evaluate("atanh(1.0)")[0])  # atanh domain |x| < 1

    def test_powers_roots_and_exponents(self):
        cases = [
            ("sqr(5)", "25"),
            ("cube(3)", "27"),
            ("pow2(4)", "16"),
            ("pow10(3)", "1,000"),
            ("sqrt(144)", "12"),
            ("cbrt(27)", "3"),
            ("cbrt(-8)", "-2"),
            ("2 ^ 0", "1"),
            ("0 ^ 0", "1"),
            ("(-2) ^ 3", "-8"),
            ("(-2) ^ 4", "16"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

        # Negative square root domain error
        success, res, _ = self.engine.evaluate("sqrt(-4)")
        self.assertFalse(success)

    def test_logarithms_and_domains(self):
        cases = [
            ("ln(e)", "1"),
            ("ln(1)", "0"),
            ("log(100)", "2"),
            ("log(1)", "0"),
            ("log2(8)", "3"),
            ("log2(1024)", "10"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

        # Non-positive log domain errors
        for bad_expr in ["ln(0)", "ln(-1)", "log(0)", "log(-10)", "log2(0)", "log2(-8)"]:
            success, res, _ = self.engine.evaluate(bad_expr)
            self.assertFalse(success, f"Expected domain error for {bad_expr}")

    def test_factorials(self):
        cases = [
            ("fact(0)", "1"),
            ("fact(1)", "1"),
            ("fact(5)", "120"),
            ("fact(10)", "3,628,800"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr)
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

        # Factorial invalid inputs and limits
        self.assertFalse(self.engine.evaluate("fact(-1)")[0])
        self.assertFalse(self.engine.evaluate("fact(3.5)")[0])
        self.assertFalse(self.engine.evaluate("fact(1001)")[0])

    def test_dms_and_deg_roundtrip(self):
        # 45.5 degrees = 45 degrees 30 minutes
        success, res_dms, _ = self.engine.evaluate("dms(45.5)")
        self.assertTrue(success)
        self.assertEqual(res_dms, "45.3")

        # 45.3 dms = 45.5 degrees
        success, res_deg, _ = self.engine.evaluate("deg(45.3)")
        self.assertTrue(success)
        self.assertEqual(res_deg, "45.5")

    def test_constants_and_implicit_multiplication(self):
        # 2pi and 2π
        success, res1, _ = self.engine.evaluate("2pi")
        self.assertTrue(success)
        self.assertAlmostEqual(float(res1), 2 * math.pi, places=4)

        success, res2, _ = self.engine.evaluate("2π")
        self.assertTrue(success)
        self.assertAlmostEqual(float(res2), 2 * math.pi, places=4)

        # 2e
        success, res3, _ = self.engine.evaluate("2e")
        self.assertTrue(success)
        self.assertAlmostEqual(float(res3), 2 * math.e, places=4)


class TestProgrammerModeExpressions(unittest.TestCase):
    """Exhaustive tests for Programmer Mode bitwise logic and hex expressions."""

    def setUp(self):
        self.engine = MathEngine()

    def test_bitwise_operations(self):
        cases = [
            ("5 AND 3", "1"),
            ("5 OR 3", "7"),
            ("5 XOR 3", "6"),
            ("NOT(0)", "-1"),
            ("NOT(5)", "-6"),
            ("1 << 4", "16"),
            ("16 >> 2", "4"),
            ("100 mod 7", "2"),
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr, mode="Programmer")
            self.assertTrue(success, f"Failed on {expr}")
            self.assertEqual(res, expected)

    def test_hexadecimal_expressions_in_programmer_mode(self):
        cases = [
            ("A + B", "21"),         # 10 + 11 = 21
            ("FF AND 0F", "15"),     # 255 & 15 = 15
            ("1A + 2B", "69"),       # 26 + 43 = 69
            ("0xFF + 1", "256"),
            ("F0 OR 0F", "255"),
            ("E * 2", "28"),         # 14 * 2 = 28
        ]
        for expr, expected in cases:
            success, res, _ = self.engine.evaluate(expr, mode="Programmer")
            self.assertTrue(success, f"Failed on {expr}: {res}")
            self.assertEqual(res, expected)

    def test_bitwise_and_arithmetic_precedence(self):
        # In Python AST, + has higher precedence than <<
        success, res1, _ = self.engine.evaluate("1 + 2 << 2", mode="Programmer")
        self.assertEqual(res1, "12")  # (1 + 2) << 2 = 3 << 2 = 12

        # 5 + 3 AND 7 -> (5 + 3) & 7 = 8 & 7 = 0
        success, res2, _ = self.engine.evaluate("5 + 3 AND 7", mode="Programmer")
        self.assertEqual(res2, "0")


class TestGraphingModeExpressions(unittest.TestCase):
    """Exhaustive tests for Graphing Mode functions, parameters, and KGF."""

    def test_natural_expression_parsing_and_implicit_multiplication(self):
        cases = [
            ("x^2 - 4", 3.0, 5.0),
            ("2x + 1", 4.0, 9.0),
            ("3(x + 2)", 2.0, 12.0),
            ("(x - 1)(x + 1)", 3.0, 8.0),
            ("4sin(x)", 0.0, 0.0),
            ("|x - 5|", 2.0, 3.0),
        ]
        for expr, x_val, expected in cases:
            fn = GraphFunction(expr)
            self.assertTrue(fn.is_valid, f"Compilation failed on {expr}")
            val = fn.eval_single(x_val)
            self.assertIsNotNone(val)
            self.assertAlmostEqual(val, expected, places=3)

    def test_asymptote_and_pole_splitting(self):
        fn_tan = GraphFunction("tan(x)")
        # Range crossing pi/2 (~1.57)
        segs_tan = fn_tan.eval_range(0.0, 3.14, num_points=300)
        self.assertGreater(len(segs_tan), 1, "tan(x) must be split into discontinuous segments across pi/2")

        fn_recip = GraphFunction("1/x")
        # Range crossing 0.0
        segs_recip = fn_recip.eval_range(-5.0, 5.0, num_points=300)
        self.assertGreater(len(segs_recip), 1, "1/x must be split across pole at x=0")

    def test_dynamic_parameters_and_evaluation(self):
        fn = GraphFunction("m*x + b")
        self.assertTrue(fn.is_valid)
        self.assertEqual(sorted(fn.parameters), ["b", "m"])

        # Change parameters dynamically
        val1 = fn.eval_single(5.0, params={"m": 2.0, "b": 3.0})
        self.assertAlmostEqual(val1, 13.0)

        val2 = fn.eval_single(5.0, params={"m": -1.0, "b": 10.0})
        self.assertAlmostEqual(val2, 5.0)

    def test_key_graph_features(self):
        fn = GraphFunction("x^2 - 4")
        kgf = fn.compute_key_features(x_min=-5.0, x_max=5.0)

        # Roots at x = -2.0 and x = 2.0
        roots = sorted([r[0] for r in kgf["roots"]])
        self.assertEqual(len(roots), 2)
        self.assertAlmostEqual(roots[0], -2.0, places=1)
        self.assertAlmostEqual(roots[1], 2.0, places=1)

        # y-intercept at (0, -4)
        self.assertIsNotNone(kgf["y_intercept"])
        self.assertAlmostEqual(kgf["y_intercept"][1], -4.0)

        # Minimum at (0, -4)
        minima = [e for e in kgf["extrema"] if e[0] == "Minimum"]
        self.assertGreaterEqual(len(minima), 1)
        self.assertAlmostEqual(minima[0][1], 0.0, places=1)
        self.assertAlmostEqual(minima[0][2], -4.0, places=1)

    def test_malicious_code_injection_blocked(self):
        malicious_inputs = [
            "__import__('os').system('dir')",
            "eval('1+1')",
            "exec('pass')",
            "open('test.txt')",
            "subprocess.call(['dir'])",
        ]
        for bad in malicious_inputs:
            fn = GraphFunction(bad)
            self.assertFalse(fn.is_valid, f"Malicious input was not blocked: {bad}")
            self.assertIsNone(fn.eval_single(1.0))


class TestUIExpressionStressAndState(unittest.TestCase):
    """Exhaustive tests for UI state machine, button interactions, live preview, and pinned expressions."""

    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win._disable_win32_filter_for_testing = True
        cls.win.resize(380, 600)
        cls.win.show()

    def setUp(self):
        self.win._switch_mode("Standard", save_config=False)
        self.state = self.win.state
        self.state.clear_all()

    def test_ui_keystroke_simulation_and_pinned_expression(self):
        # Simulate: 10 + 20 =
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.evaluate()

        self.assertEqual(self.state.active_token, "30")
        self.assertEqual(self.state.pinned_expression, "10 + 20 =")
        self.assertTrue(self.state.is_evaluated)
        # Verify UI display text matches
        self.assertEqual(self.win.display.primary_display.text(), "30")
        self.assertEqual(self.win.display.expression_label.text(), "10 + 20 =")

    def test_ui_ans_chaining(self):
        # 10 + 5 = 15
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("5")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "15")

        # * 2 = 30
        self.state.input_operator("*")
        self.state.input_digit("2")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "30")
        self.assertEqual(self.state.pinned_expression, "15 * 2 =")

    def test_ui_repeated_equals_chaining(self):
        # 5 + 3 = 8
        self.state.input_digit("5")
        self.state.input_operator("+")
        self.state.input_digit("3")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "8")

        # Second '=' -> 8 + 3 = 11
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "11")

        # Third '=' -> 11 + 3 = 14
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "14")

    def test_ui_clear_entry_vs_clear_all(self):
        # 10 + 50 -> CE -> 20 = 30
        self.state.input_digit("1")
        self.state.input_digit("0")
        self.state.input_operator("+")
        self.state.input_digit("5")
        self.state.input_digit("0")
        self.assertEqual(self.state.active_token, "50")

        self.state.clear_entry()
        self.assertEqual(self.state.active_token, "0")
        self.assertEqual(self.state.expression_trail, "10 + ")

        self.state.input_digit("2")
        self.state.input_digit("0")
        self.state.evaluate()
        self.assertEqual(self.state.active_token, "30")

    def test_ui_negate_button(self):
        self.state.input_digit("4")
        self.state.input_digit("2")
        self.state.negate()
        self.assertEqual(self.state.active_token, "-42")
        self.state.negate()
        self.assertEqual(self.state.active_token, "42")

    def test_ui_backspace(self):
        self.state.input_digit("1")
        self.state.input_digit("2")
        self.state.input_digit("3")
        self.state.backspace()
        self.assertEqual(self.state.active_token, "12")
        self.state.backspace()
        self.assertEqual(self.state.active_token, "1")
        self.state.backspace()
        self.assertEqual(self.state.active_token, "0")

    def test_ui_error_display_and_recovery(self):
        # 5 / 0 =
        self.state.input_digit("5")
        self.state.input_operator("/")
        self.state.input_digit("0")
        self.state.evaluate()

        self.assertTrue(self.state.has_error)
        self.assertIn("cannot divide by zero", self.win.display.primary_display.text().lower())

        # Typing a new digit must clear the error gracefully
        self.state.input_digit("7")
        self.assertFalse(self.state.has_error)
        self.assertEqual(self.state.active_token, "7")


if __name__ == "__main__":
    unittest.main()
