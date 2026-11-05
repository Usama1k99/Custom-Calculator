"""
Exhaustive unit tests for Input Validation and Leading Zero Sanitization.
Tests Standard, Scientific, and Programmer modes against Windows Calculator standards.
"""

import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
import sys

from src.core.input_validator import (
    is_char_allowed,
    filter_allowed_text,
    sanitize_leading_zeros,
    validate_and_sanitize_input,
)
from src.ui.main_window import MainWindow
from src.ui.display_widget import CalculatorDisplayEdit


app = QApplication.instance() or QApplication(sys.argv)


class TestInputValidatorCore(unittest.TestCase):
    """Tests the low-level validator functions."""

    def test_sanitize_leading_zeros(self):
        # Single digit replacement on 0
        self.assertEqual(sanitize_leading_zeros("05", "Standard"), "5")
        self.assertEqual(sanitize_leading_zeros("00", "Standard"), "0")
        self.assertEqual(sanitize_leading_zeros("007", "Standard"), "7")
        self.assertEqual(sanitize_leading_zeros("-05", "Standard"), "-5")
        self.assertEqual(sanitize_leading_zeros("-0", "Standard"), "-0")
        self.assertEqual(sanitize_leading_zeros("0", "Standard"), "0")
        self.assertEqual(sanitize_leading_zeros("", "Standard"), "0")

        # Decimal numbers must preserve zero before and after dot
        self.assertEqual(sanitize_leading_zeros("0.", "Standard"), "0.")
        self.assertEqual(sanitize_leading_zeros("0.5", "Standard"), "0.5")
        self.assertEqual(sanitize_leading_zeros("0.05", "Standard"), "0.05")
        self.assertEqual(sanitize_leading_zeros("0.005", "Standard"), "0.005")
        self.assertEqual(sanitize_leading_zeros("00.5", "Standard"), "0.5")
        self.assertEqual(sanitize_leading_zeros("-0.5", "Standard"), "-0.5")
        self.assertEqual(sanitize_leading_zeros("-00.5", "Standard"), "-0.5")
        self.assertEqual(sanitize_leading_zeros("105", "Standard"), "105")
        self.assertEqual(sanitize_leading_zeros("10", "Standard"), "10")

        # Programmer Mode Hex
        self.assertEqual(sanitize_leading_zeros("0A", "Programmer"), "A")
        self.assertEqual(sanitize_leading_zeros("0FF", "Programmer"), "FF")

        # Scientific Expression formulas
        self.assertEqual(sanitize_leading_zeros("5 + 05", "Scientific"), "5 + 5")
        self.assertEqual(sanitize_leading_zeros("sin(05)", "Scientific"), "sin(5)")
        self.assertEqual(sanitize_leading_zeros("(05)", "Scientific"), "(5)")
        self.assertEqual(sanitize_leading_zeros("2^05", "Scientific"), "2^5")

    def test_standard_mode_character_filtering(self):
        # Allowed in Standard
        for ch in "0123456789.+-*/%":
            self.assertTrue(is_char_allowed(ch, "Standard"), f"Char '{ch}' should be allowed in Standard")

        # Disallowed in Standard (Letters & non-math symbols)
        disallowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ()@#$^&_!~|\\;:'\"<>?[]{}"
        for ch in disallowed:
            self.assertFalse(is_char_allowed(ch, "Standard"), f"Char '{ch}' must be blocked in Standard")

        self.assertEqual(filter_allowed_text("123 + 45.6", "Standard"), "123 + 45.6")
        self.assertEqual(filter_allowed_text("abc123xyz!@#", "Standard"), "123")

    def test_scientific_mode_character_filtering(self):
        # Allowed in Scientific: Digits, operators, parentheses, exponents, constants, math function letters
        allowed = "0123456789.+-*/^%()eEπ"
        for ch in allowed:
            self.assertTrue(is_char_allowed(ch, "Scientific"), f"Char '{ch}' should be allowed in Scientific")

        # Valid function letters
        fn_letters = "sincotaghleqrbfmdpx"
        for ch in fn_letters:
            self.assertTrue(is_char_allowed(ch, "Scientific"), f"Letter '{ch}' should be allowed in Scientific")

        # Invalid symbols & random letters
        invalid = "@#$&_~\\;:'\"?[]{}"
        for ch in invalid:
            self.assertFalse(is_char_allowed(ch, "Scientific"), f"Symbol '{ch}' must be blocked in Scientific")

        self.assertEqual(filter_allowed_text("sin(30) + 5.2^2", "Scientific"), "sin(30) + 5.2^2")
        self.assertEqual(filter_allowed_text("log(100) * pi", "Scientific"), "log(100) * pi")

    def test_programmer_mode_radix_filtering(self):
        # In all radixes of Programmer mode, '.' is strictly forbidden
        self.assertFalse(is_char_allowed(".", "Programmer", "HEX"))
        self.assertFalse(is_char_allowed(".", "Programmer", "DEC"))
        self.assertFalse(is_char_allowed(".", "Programmer", "OCT"))
        self.assertFalse(is_char_allowed(".", "Programmer", "BIN"))

        # HEX: Digits 0-9 and A-F allowed
        for ch in "0123456789abcdefABCDEF":
            self.assertTrue(is_char_allowed(ch, "Programmer", "HEX"), f"'{ch}' must be allowed in HEX")
        for ch in "GHIJKLMNOPQRSTUVWXYZghijklmnopqrstuvwxyz":
            self.assertFalse(is_char_allowed(ch, "Programmer", "HEX"), f"'{ch}' must be blocked in HEX")

        # DEC: Digits 0-9 allowed, A-F blocked
        for ch in "0123456789":
            self.assertTrue(is_char_allowed(ch, "Programmer", "DEC"), f"'{ch}' must be allowed in DEC")
        for ch in "abcdefABCDEF":
            self.assertFalse(is_char_allowed(ch, "Programmer", "DEC"), f"'{ch}' must be blocked in DEC")

        # OCT: Digits 0-7 allowed, 8, 9, A-F blocked
        for ch in "01234567":
            self.assertTrue(is_char_allowed(ch, "Programmer", "OCT"), f"'{ch}' must be allowed in OCT")
        for ch in "89abcdefABCDEF":
            self.assertFalse(is_char_allowed(ch, "Programmer", "OCT"), f"'{ch}' must be blocked in OCT")

        # BIN: Digits 0 and 1 only
        self.assertTrue(is_char_allowed("0", "Programmer", "BIN"))
        self.assertTrue(is_char_allowed("1", "Programmer", "BIN"))
        for ch in "23456789abcdefABCDEF":
            self.assertFalse(is_char_allowed(ch, "Programmer", "BIN"), f"'{ch}' must be blocked in BIN")

        # Bitwise operators allowed across all radixes
        for op in "+-*/%&|^~()":
            self.assertTrue(is_char_allowed(op, "Programmer", "HEX"))
            self.assertTrue(is_char_allowed(op, "Programmer", "DEC"))
            self.assertTrue(is_char_allowed(op, "Programmer", "OCT"))
            self.assertTrue(is_char_allowed(op, "Programmer", "BIN"))

    def test_validate_and_sanitize_input(self):
        # Cleaning dirty inputs
        self.assertEqual(validate_and_sanitize_input("0054abc@#$", "Standard"), "54")
        self.assertEqual(validate_and_sanitize_input("0ff.5", "Programmer", "HEX"), "FF5")
        self.assertEqual(validate_and_sanitize_input("0789", "Programmer", "OCT"), "7")
        self.assertEqual(validate_and_sanitize_input("010129", "Programmer", "BIN"), "101")


class TestUIDisplayFieldInteractions(unittest.TestCase):
    """Tests interactive typing and display widget behaviors."""

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
        self.display_edit = self.win.display.primary_display

    def test_leading_zero_replacement_on_digit_input(self):
        # Initial display must be "0"
        self.assertEqual(self.display_edit.text(), "0")
        self.assertEqual(self.state.active_token, "0")

        # Keying '5' must replace '0' with '5', NOT produce '05'
        self.state.input_digit("5")
        self.assertEqual(self.state.active_token, "5")
        self.assertEqual(self.display_edit.text(), "5")

        # Keying '0' after '5' appends '0' -> '50'
        self.state.input_digit("0")
        self.assertEqual(self.state.active_token, "50")
        self.assertEqual(self.display_edit.text(), "50")

    def test_leading_zero_with_decimal(self):
        # Keying '.' on '0' must produce '0.'
        self.assertEqual(self.display_edit.text(), "0")
        self.state.input_digit(".")
        self.assertEqual(self.state.active_token, "0.")
        self.assertEqual(self.display_edit.text(), "0.")

        # Keying '5' produces '0.5'
        self.state.input_digit("5")
        self.assertEqual(self.state.active_token, "0.5")
        self.assertEqual(self.display_edit.text(), "0.5")

    def test_backspace_to_empty_restores_zero(self):
        self.state.input_digit("9")
        self.assertEqual(self.state.active_token, "9")

        # Backspacing the only digit must restore "0", never leave it blank
        self.state.backspace()
        self.assertEqual(self.state.active_token, "0")
        self.assertEqual(self.display_edit.text(), "0")

        # Additional backspaces on "0" keep it at "0"
        self.state.backspace()
        self.assertEqual(self.state.active_token, "0")
        self.assertEqual(self.display_edit.text(), "0")

    def test_letters_blocked_in_standard_mode(self):
        # Letters must be blocked via state.input_digit
        self.state.input_digit("a")
        self.assertEqual(self.state.active_token, "0")
        self.state.input_digit("Z")
        self.assertEqual(self.state.active_token, "0")

    def test_programmer_mode_hex_and_no_decimals(self):
        self.win._switch_mode("Programmer", save_config=False)
        self.win.set_radix("HEX")
        self.state.clear_all()

        # Decimal point is blocked
        self.state.input_digit(".")
        self.assertEqual(self.state.active_token, "0")

        # Hex letters A-F allowed and replace leading 0
        self.state.input_digit("A")
        self.assertEqual(self.state.active_token, "A")
        self.state.input_digit("f")
        self.assertEqual(self.state.active_token, "AF")

        # Radix BIN: only 0 and 1 allowed
        self.win.set_radix("BIN")
        self.state.clear_all()
        self.state.input_digit("2")
        self.assertEqual(self.state.active_token, "0")  # '2' rejected
        self.state.input_digit("1")
        self.assertEqual(self.state.active_token, "1")  # '1' accepted


if __name__ == "__main__":
    unittest.main()
