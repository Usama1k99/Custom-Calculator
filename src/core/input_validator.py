"""
Input validation and character filtering for Standard, Scientific, and Programmer modes.
Strictly adheres to Windows Calculator keyboard and input standards:
- Standard: Digits 0-9, Decimal '.', Basic operators (+, -, *, /, %). All letters & non-math symbols blocked.
- Scientific: Digits 0-9, '.', Operators (+, -, *, /, ^, %), Parentheses (, ),
  Constants/Exponents (e, E, pi, π), and Scientific function letters. Non-math letters & symbols blocked.
- Programmer: Radix-specific digits (HEX: 0-9, A-F; DEC: 0-9; OCT: 0-7; BIN: 0-1).
  Decimal '.' is STRICTLY FORBIDDEN. Bitwise/logic operators (&, |, ^, ~, +, -, *, /, %, (, ), <<, >>).
- Leading Zero Management: '0' displayed by default; as soon as a valid char is input,
  the leading zero on the left is replaced/removed (e.g. '05' -> '5', '-05' -> '-5', '0A' -> 'A', '12 + 05' -> '12 + 5').
"""

import re
from typing import Set

# Standard Mode: Digits 0-9, Decimal separator ('.', ','), Basic operators
STANDARD_ALLOWED_CHARS: Set[str] = set("0123456789.+-*/%−×÷, ")

# Scientific Mode: Digits, decimals, operators, parentheses, exponents, constants, math function letters
SCIENTIFIC_ALLOWED_MATH_CHARS: Set[str] = set("0123456789.+-*/^%()−×÷, eEπ ")

# Valid letters forming mathematical functions and constants:
# sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, log, ln, sqrt, cbrt, exp, abs, fact, mod, pi, deg, rad
SCIENTIFIC_ALLOWED_LETTERS: Set[str] = set(
    "abcdefghilmnopqrstxyABCDEFGHILMNOPQRSTXY"
)

# Programmer Mode: Base operators & symbols
PROGRAMMER_COMMON_OPS: Set[str] = set("+-*/%&|^~()<>−×÷ ")


def is_char_allowed(char: str, mode: str = "Standard", radix: str = "DEC") -> bool:
    """
    Checks whether an individual character is permitted in the specified mode and radix.
    """
    if not char:
        return False
    if char in ("\r", "\n", "\t"):
        return False

    if mode == "Standard":
        return char in STANDARD_ALLOWED_CHARS

    elif mode == "Scientific":
        return char in SCIENTIFIC_ALLOWED_MATH_CHARS or char in SCIENTIFIC_ALLOWED_LETTERS

    elif mode == "Programmer":
        # Decimal point is NEVER allowed in Programmer mode
        if char in (".", ","):
            return False

        if char in PROGRAMMER_COMMON_OPS:
            return True

        rad = radix.upper()
        if rad == "HEX":
            return char in "0123456789abcdefABCDEF"
        elif rad == "DEC":
            return char in "0123456789"
        elif rad == "OCT":
            return char in "01234567"
        elif rad == "BIN":
            return char in "01"
        else:
            # Default fallback for Programmer mode
            return char in "0123456789abcdefABCDEF"

    # Fallback for converter or other modes: allow basic digits and decimal
    return char in "0123456789., "


def filter_allowed_text(text: str, mode: str = "Standard", radix: str = "DEC") -> str:
    """
    Strips out all characters not permitted in the specified mode and radix.
    """
    if not text:
        return ""
    return "".join(c for c in text if is_char_allowed(c, mode, radix))


def sanitize_leading_zeros(text: str, mode: str = "Standard") -> str:
    """
    Ensures that '0' is displayed by default, and as soon as a valid char is input,
    the left-side trailing/leading zero is removed (e.g. '05' -> '5', '-05' -> '-5').
    Preserves valid zero usages like '0', '-0', '0.', '0.05', '105', '10'.
    """
    if not text:
        return "0"

    # Replace localized comma with decimal period
    text = text.replace(",", ".")

    # Fast-paths for lone zero tokens
    if text in ("0", "-0"):
        return text

    def _clean_number_token(m):
        prefix = m.group(1) or ""
        num = m.group(2)
        if "." in num:
            int_part, frac_part = num.split(".", 1)
            is_neg = int_part.startswith("-")
            digits = int_part.lstrip("-").lstrip("0")
            if not digits:
                digits = "0"
            clean_int = f"-{digits}" if is_neg else digits
            return f"{prefix}{clean_int}.{frac_part}"
        else:
            is_neg = num.startswith("-")
            digits = num.lstrip("-").lstrip("0")
            if not digits:
                digits = "0"
            clean_num = f"-{digits}" if is_neg else digits
            return f"{prefix}{clean_num}"

    # Match number tokens (with optional sign, digits, optional decimal)
    # Programmer mode allows hex digits [0-9a-fA-F]
    if mode == "Programmer":
        pattern = r"(^|[^\w\.])(-?[0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?)"
    else:
        pattern = r"(^|[^\w\.])(-?\d+(?:\.\d*)?)"

    text = re.sub(pattern, _clean_number_token, text)
    return text if text else "0"


def validate_and_sanitize_input(text: str, mode: str = "Standard", radix: str = "DEC") -> str:
    """
    Complete pipeline: filters out disallowed characters and cleans leading zeros.
    """
    filtered = filter_allowed_text(text, mode=mode, radix=radix)
    if mode == "Programmer" and radix.upper() == "HEX":
        # Auto-uppercase hex characters while preserving operators
        filtered = "".join(c.upper() if c in "abcdef" else c for c in filtered)
    return sanitize_leading_zeros(filtered, mode=mode)
