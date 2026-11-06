"""
Robust Mathematical Engine with Exhaustive Edge-Case Handling.
Prevents IEEE-754 float drift, safely evaluates complex expressions,
handles domain errors, divisions by zero, and malformed inputs gracefully.
"""

import ast
import decimal
from decimal import Decimal, InvalidOperation, Overflow
import math
import random
import re
from typing import Tuple, Optional

# 36 digits of precision
decimal.getcontext().prec = 36


class AngleMode:
    DEG = "DEG"
    RAD = "RAD"
    GRAD = "GRAD"


def is_expression_incomplete(expr: str) -> bool:
    """
    Checks if an expression ends in an operator, open parenthesis, comma, or incomplete syntax
    where evaluating a live preview would be meaningless or generate invalid repetitions.
    """
    if not expr or not expr.strip():
        return True
    s = expr.strip()
    # Check if ends with binary operator, unary operator waiting for argument, open parenthesis, or comma
    # Covers +, -, *, /, ×, ÷, −, %, ^, &, |, ~, <<, >>, <, >, <=, >=, ==, !=
    # and words AND, OR, XOR, NOT, mod, or opening parenthesis (
    op_pattern = r'([\+\-\*/%&\|\^×÷−~<>=]|<<|>>|\bAND\b|\bOR\b|\bXOR\b|\bNOT\b|\bmod\b|\(|,)\s*$'
    return bool(re.search(op_pattern, s, flags=re.IGNORECASE))


class MathEngine:
    def __init__(self):
        self.angle_mode = AngleMode.DEG
        self.scientific_notation = False

    def set_angle_mode(self, mode: str):
        if mode in (AngleMode.DEG, AngleMode.RAD, AngleMode.GRAD):
            self.angle_mode = mode

    def toggle_angle_mode(self) -> str:
        if self.angle_mode == AngleMode.DEG:
            self.angle_mode = AngleMode.RAD
        elif self.angle_mode == AngleMode.RAD:
            self.angle_mode = AngleMode.GRAD
        else:
            self.angle_mode = AngleMode.DEG
        return self.angle_mode

    def toggle_fe_notation(self) -> bool:
        self.scientific_notation = not self.scientific_notation
        return self.scientific_notation

    def _to_radians(self, val: float) -> float:
        if self.angle_mode == AngleMode.DEG:
            return math.radians(val)
        elif self.angle_mode == AngleMode.GRAD:
            return val * math.pi / 200.0
        return val

    def _from_radians(self, rad: float) -> float:
        if self.angle_mode == AngleMode.DEG:
            return math.degrees(rad)
        elif self.angle_mode == AngleMode.GRAD:
            return rad * 200.0 / math.pi
        return rad

    def sanitize_expression(self, expr: str, mode: str = "Standard", allow_incomplete: bool = True) -> str:
        """
        Cleans and normalizes user input into a valid Python AST string.
        Gracefully repairs unclosed parentheses, removes empty brackets,
        and standardizes math operators, percentages, constants, and radix formats.
        """
        s = expr.strip()
        if not s:
            return "0"

        # Strip trailing '='
        if s.endswith("="):
            s = s[:-1].strip()

        # Replace UI Unicode glyphs with standard arithmetic tokens
        s = s.replace("×", "*")
        s = s.replace("÷", "/")
        s = s.replace("−", "-")
        s = s.replace("—", "-")
        s = s.replace("^", "**")

        # Replace programmer & scientific logical operators before AST parsing
        s = re.sub(r'\bAND\b', '&', s, flags=re.IGNORECASE)
        s = re.sub(r'\bOR\b', '|', s, flags=re.IGNORECASE)
        s = re.sub(r'\bXOR\b', '^', s, flags=re.IGNORECASE)
        s = re.sub(r'\bNOT\b', '~', s, flags=re.IGNORECASE)

        # Radix & constant normalization based on mode
        if mode == "Programmer":
            reserved_prog = {'and', 'or', 'xor', 'not', 'mod', 'lsh', 'rsh'}
            def _replace_hex(m):
                w = m.group(0)
                if w.lower() in reserved_prog:
                    return w
                if any(c in 'abcdefABCDEF' for c in w) and not w.lower().startswith('0x'):
                    return f'0x{w}'
                return w
            s = re.sub(r'\b[0-9a-fA-F]+\b', _replace_hex, s)
        else:
            # Mathematical constants pi and e (only in non-programmer modes)
            s = re.sub(r'(\b\d+(?:\.\d+)?)\s*(?:pi|π)', rf'\1*({math.pi})', s, flags=re.IGNORECASE)
            s = re.sub(r'(?<![a-zA-Z_])(?:pi|π)(?![a-zA-Z_])', f'({math.pi})', s, flags=re.IGNORECASE)
            s = re.sub(r'(\b\d+(?:\.\d+)?)\s*e(?![a-zA-Z0-9_\+\-])', rf'\1*({math.e})', s)
            s = re.sub(r'(?<![a-zA-Z0-9_])e(?![a-zA-Z0-9_\+\-])', f'({math.e})', s)

        # Handle percentages (contextual: only when attached as a percentage suffix like 10%, NOT binary modulo like 10 % 3)
        # Case 1: Additive / Subtractive: A + B% -> A + (A * (B/100))
        s = re.sub(
            r'(\b\d+(?:\.\d+)?)\s*([\+\-])\s*(\b\d+(?:\.\d+)?)\s*%(?!\s*\d)',
            r'\1 \2 (\1 * (\3 / 100))',
            s
        )
        # Case 2: Multiplicative / Divisive: A * B% -> A * (B/100)
        s = re.sub(
            r'(\b\d+(?:\.\d+)?)\s*([\*/])\s*(\b\d+(?:\.\d+)?)\s*%(?!\s*\d)',
            r'\1 \2 (\3 / 100)',
            s
        )
        # Case 3: Standalone percentage: X% -> (X / 100)
        s = re.sub(r'(\b\d+(?:\.\d+)?)\s*%(?!\s*\d)', r'(\1 / 100)', s)

        # Replace programmer & scientific mod operator after percentage handling
        s = re.sub(r'\bmod\b', '%', s, flags=re.IGNORECASE)

        # Handle incomplete expressions like "5 +" or "5 *" (Windows Calc behavior on '=': repeat operand)
        trailing_op_match = re.search(r'([\+\-\*/%&|\^]|<<|>>)\s*$', s)
        if trailing_op_match:
            if not allow_incomplete:
                return ""  # Incomplete, cannot evaluate in preview
            op = trailing_op_match.group(1)
            # Find the last valid number preceding the operator
            preceding_num = re.findall(r'\b\d+(?:\.\d+)?\b', s)
            if preceding_num:
                s = f"{s} {preceding_num[-1]}"
            else:
                s = s[:-len(op)].strip() or "0"

        # Auto-expand standalone rand to rand()
        s = re.sub(r'\brand\b(?!\s*\()', 'rand()', s, flags=re.IGNORECASE)

        # Remove standalone empty parentheses e.g. "5 + ()" (protect function calls like rand())
        s = re.sub(r'(?<![a-zA-Z0-9_])\(\s*\)', '', s)

        # Handle implicit multiplication: 2(3) -> 2*(3), (2)(3) -> (2)*(3), 2pi -> 2*pi
        # Use word boundary \b to avoid breaking function names with digits like log2(8) or pow10(3)
        s = re.sub(r'\b(\d+)\s*\(', r'\1*(', s)
        s = re.sub(r'\)\s*\(', r')*(', s)
        s = re.sub(r'\)\s*(\d)', r')*\1', s)

        # Balance unclosed parentheses: e.g. "(5 + 2 * (3 + 1" -> append "))"
        open_count = s.count("(")
        close_count = s.count(")")
        if open_count > close_count:
            s += ")" * (open_count - close_count)

        # Final check if empty
        if not s.strip():
            return "0"

        return s

    def evaluate(self, expr: str, mode: str = "Standard", allow_incomplete: bool = True) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Safely evaluates an algebraic expression with exhaustive edge case protection.
        Returns: (success: bool, formatted_result_or_error: str, raw_decimal: Optional[Decimal])
        """
        if not expr or not expr.strip():
            return True, "0", Decimal("0")

        if not allow_incomplete and is_expression_incomplete(expr):
            return False, "", None

        sanitized = self.sanitize_expression(expr, mode=mode, allow_incomplete=allow_incomplete)
        if not sanitized:
            return False, "", None

        try:
            tree = ast.parse(sanitized, mode='eval')
            result_val = self._eval_ast_node(tree.body)

            if isinstance(result_val, (int, float, Decimal)):
                # Detect special float cases like inf or nan
                if math.isinf(float(result_val)):
                    return False, "Overflow", None
                if math.isnan(float(result_val)):
                    return False, "Invalid input", None

                dec_val = Decimal(str(result_val))
                formatted = self.format_number(dec_val)
                return True, formatted, dec_val
            else:
                return False, "Invalid input", None

        except ZeroDivisionError:
            return False, "Cannot divide by zero", None
        except (ValueError, InvalidOperation):
            return False, "Invalid input", None
        except OverflowError:
            return False, "Overflow", None
        except Exception:
            return False, "Invalid input", None

    def _eval_ast_node(self, node: ast.AST):
        if isinstance(node, ast.Constant):
            return Decimal(str(node.value))

        elif isinstance(node, ast.BinOp):
            left = self._eval_ast_node(node.left)
            right = self._eval_ast_node(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError()
                return left / right
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    raise ZeroDivisionError()
                return left % right
            elif isinstance(node.op, ast.Pow):
                if left == 0 and right == 0:
                    return Decimal("1")
                # Protect against gigantic powers that hang CPU
                if abs(right) > 10000:
                    raise OverflowError()
                return left ** right
            elif isinstance(node.op, ast.LShift):
                return int(left) << int(right)
            elif isinstance(node.op, ast.RShift):
                return int(left) >> int(right)
            elif isinstance(node.op, ast.BitAnd):
                return int(left) & int(right)
            elif isinstance(node.op, ast.BitOr):
                return int(left) | int(right)
            elif isinstance(node.op, ast.BitXor):
                return int(left) ^ int(right)
            else:
                raise TypeError(f"Unsupported binary operator: {type(node.op)}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_ast_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Invert):
                return ~int(operand)
            else:
                raise TypeError(f"Unsupported unary operator: {type(node.op)}")

        elif isinstance(node, ast.Call):
            func_name = node.func.id.lower() if isinstance(node.func, ast.Name) else ""
            args = [self._eval_ast_node(arg) for arg in node.args]
            return self._call_math_func(func_name, args)

        else:
            raise TypeError(f"Unsupported AST node: {type(node)}")

    def _call_math_func(self, name: str, args: list):
        if not args:
            if name == "rand":
                return Decimal(str(round(random.random(), 9)))
            raise ValueError(f"Function {name} requires arguments")

        val = float(args[0])

        rad = self._to_radians(val)
        if name == "sin":
            res = math.sin(rad)
            return Decimal(str(0 if abs(res) < 1e-12 else round(res, 12)))
        elif name == "cos":
            res = math.cos(rad)
            return Decimal(str(0 if abs(res) < 1e-12 else round(res, 12)))
        elif name == "tan":
            cos_val = math.cos(rad)
            if abs(cos_val) < 1e-12:
                raise ValueError("Invalid input (tan is undefined)")
            res = math.tan(rad)
            return Decimal(str(0 if abs(res) < 1e-12 else round(res, 12)))
        elif name == "sec":
            cos_val = math.cos(rad)
            if abs(cos_val) < 1e-12:
                raise ValueError("Invalid input (sec is undefined)")
            return Decimal(str(round(1.0 / cos_val, 12)))
        elif name == "csc":
            sin_val = math.sin(rad)
            if abs(sin_val) < 1e-12:
                raise ValueError("Invalid input (csc is undefined)")
            return Decimal(str(round(1.0 / sin_val, 12)))
        elif name == "cot":
            tan_val = math.tan(rad)
            if abs(tan_val) < 1e-12:
                raise ValueError("Invalid input (cot is undefined)")
            return Decimal(str(round(1.0 / tan_val, 12)))

        elif name == "asin":
            if val < -1.0 or val > 1.0:
                raise ValueError("Domain error for asin")
            return Decimal(str(self._from_radians(math.asin(val))))
        elif name == "acos":
            if val < -1.0 or val > 1.0:
                raise ValueError("Domain error for acos")
            return Decimal(str(self._from_radians(math.acos(val))))
        elif name == "atan":
            return Decimal(str(self._from_radians(math.atan(val))))
        elif name == "asec":
            if abs(val) < 1.0:
                raise ValueError("Domain error for asec")
            return Decimal(str(self._from_radians(math.acos(1.0 / val))))
        elif name == "acsc":
            if abs(val) < 1.0:
                raise ValueError("Domain error for acsc")
            return Decimal(str(self._from_radians(math.asin(1.0 / val))))
        elif name == "acot":
            return Decimal(str(self._from_radians(math.atan(1.0 / val))))

        elif name == "sinh":
            return Decimal(str(math.sinh(val)))
        elif name == "cosh":
            return Decimal(str(math.cosh(val)))
        elif name == "tanh":
            return Decimal(str(math.tanh(val)))
        elif name == "sech":
            return Decimal(str(1.0 / math.cosh(val)))
        elif name == "csch":
            if val == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return Decimal(str(1.0 / math.sinh(val)))
        elif name == "coth":
            if val == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return Decimal(str(1.0 / math.tanh(val)))

        elif name == "asinh":
            return Decimal(str(math.asinh(val)))
        elif name == "acosh":
            if val < 1.0:
                raise ValueError("Domain error for acosh")
            return Decimal(str(math.acosh(val)))
        elif name == "atanh":
            if val <= -1.0 or val >= 1.0:
                raise ValueError("Domain error for atanh")
            return Decimal(str(math.atanh(val)))
        elif name == "asech":
            if val <= 0 or val > 1.0:
                raise ValueError("Domain error for asech")
            return Decimal(str(math.acosh(1.0 / val)))
        elif name == "acsch":
            if val == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return Decimal(str(math.asinh(1.0 / val)))
        elif name == "acoth":
            if abs(val) <= 1.0:
                raise ValueError("Domain error for acoth")
            return Decimal(str(math.atanh(1.0 / val)))

        elif name in ("sqrt", "²√x"):
            if val < 0:
                raise ValueError("Square root of negative number")
            return Decimal(str(math.sqrt(val)))
        elif name in ("cbrt", "³√x"):
            res = math.cbrt(val) if hasattr(math, 'cbrt') else (val ** (1.0/3.0) if val >= 0 else -((-val) ** (1.0/3.0)))
            return Decimal(str(res))
        elif name == "sqr":
            return Decimal(str(val ** 2))
        elif name == "cube":
            return Decimal(str(val ** 3))
        elif name == "pow2":
            return Decimal(str(2.0 ** val))
        elif name == "pow10":
            return Decimal(str(10.0 ** val))
        elif name == "exp_e":
            return Decimal(str(math.exp(val)))
        elif name == "ln":
            if val <= 0:
                raise ValueError("Log of non-positive number")
            return Decimal(str(math.log(val)))
        elif name == "log":
            if val <= 0:
                raise ValueError("Log of non-positive number")
            return Decimal(str(math.log10(val)))
        elif name == "log2":
            if val <= 0:
                raise ValueError("Log of non-positive number")
            return Decimal(str(math.log2(val)))
        elif name == "abs":
            return Decimal(str(abs(val)))
        elif name == "floor":
            return Decimal(str(math.floor(val)))
        elif name == "ceil":
            return Decimal(str(math.ceil(val)))
        elif name == "rand":
            return Decimal(str(round(random.random(), 9)))
        elif name == "dms":
            d = int(val)
            rem = abs(val - d) * 60.0
            m = int(rem)
            s = round((rem - m) * 60.0, 4)
            return Decimal(str(d + m / 100.0 + s / 10000.0))
        elif name == "deg":
            d = int(val)
            rem = round((abs(val) - abs(d)) * 100.0, 6)
            m = int(rem)
            s = (rem - m) * 100.0
            sign = 1 if val >= 0 else -1
            return Decimal(str(sign * (abs(d) + m / 60.0 + s / 3600.0)))
        elif name == "fact":
            int_val = int(val)
            if int_val < 0 or int_val != val:
                raise ValueError("Factorial requires non-negative integer")
            if int_val > 1000:
                raise OverflowError("Factorial too large")
            return Decimal(str(math.factorial(int_val)))
        elif name == "recip":
            if val == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return Decimal(str(1.0 / val))
        else:
            raise NameError(f"Unknown function: {name}")

    def format_number(self, val: Decimal) -> str:
        """
        Formats a Decimal into a clean, human-readable string with proper digit grouping.
        """
        if self.scientific_notation:
            return f"{float(val):.6e}".replace("+0", "+").replace("-0", "-")

        if val == val.to_integral():
            int_val = int(val)
            return f"{int_val:,}"

        f = float(val)
        if (0 < abs(f) < 1e-7) or abs(f) >= 1e16:
            return f"{f:.8e}".replace("+0", "+").replace("-0", "-")

        normalized = val.normalize()
        s = f"{normalized:f}"
        if "." in s:
            whole, frac = s.split(".")
            whole_int = int(whole)
            if len(frac) > 10:
                frac = frac[:10].rstrip("0")
            return f"{whole_int:,}.{frac}" if frac else f"{whole_int:,}"
        return f"{int(s):,}"
