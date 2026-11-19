"""
Robust Calculator State Machine with Windows Calculator Behaviors.
Manages distinct Expression Trail vs. Active Token, CE vs C,
unary operations, repeated equals chaining, and edge-case sanitization.
"""

from decimal import Decimal
from typing import Optional, Callable
from src.core.engine import MathEngine, is_expression_incomplete
from src.database.history_db import HistoryDB
from src.core.crash_reporter import record_breadcrumb
from src.core.input_validator import is_char_allowed, sanitize_leading_zeros


UNARY_DISPLAY_TEMPLATES = {
    "recip": "1/({x})",
    "sqr": "sqr({x})",
    "sqrt": "√({x})",
    "cube": "cube({x})",
    "cbrt": "³√({x})",
    "pow10": "10^({x})",
    "pow2": "2^({x})",
    "exp_e": "e^({x})",
    "fact": "fact({x})",
    "abs": "abs({x})",
    "log": "log({x})",
    "log2": "log2({x})",
    "ln": "ln({x})",
    "floor": "floor({x})",
    "ceil": "ceil({x})",
    "dms": "dms({x})",
    "deg": "degrees({x})",
    "NOT": "NOT({x})",
    "negate": "negate({x})",
    # Trigonometric functions
    "sin": "sin({x})",
    "cos": "cos({x})",
    "tan": "tan({x})",
    "asin": "asin({x})",
    "acos": "acos({x})",
    "atan": "atan({x})",
    "sinh": "sinh({x})",
    "cosh": "cosh({x})",
    "tanh": "tanh({x})",
    "asinh": "asinh({x})",
    "acosh": "acosh({x})",
    "atanh": "atanh({x})",
    "sec": "sec({x})",
    "csc": "csc({x})",
    "cot": "cot({x})",
    "asec": "asec({x})",
    "acsc": "acsc({x})",
    "acot": "acot({x})",
    "sech": "sech({x})",
    "csch": "csch({x})",
    "coth": "coth({x})",
    "asech": "asech({x})",
    "acsch": "acsch({x})",
    "acoth": "acoth({x})",
}


class CalculatorState:
    def __init__(self, engine: MathEngine, db: HistoryDB, on_state_changed: Callable):
        self.engine = engine
        self.db = db
        self.on_state_changed = on_state_changed

        self.mode = "Standard"
        self.radix = "DEC"
        self.expression_trail = ""   # Preceding tokens, e.g. "10 + 20 +"
        self.active_token = "0"      # Currently active number being keyed in
        self.pinned_expression = ""  # Post-evaluation formula, e.g. "10 + 20 + 30 ="
        self.current_operand_repr: Optional[str] = None  # Operand expression representation, e.g. "√(sqr(1/(10)))"
        self.is_unary_active = False # True when active_token was created by a unary operation
        self.is_evaluated = False
        self.has_error = False

        # Repeated equals support: preserves (last_operator, last_operand)
        self.last_op_repeat = None
        self.last_operand_repeat = None

        self.open_parentheses_count: int = 0

        self.last_result: Optional[Decimal] = None
        self.memory_value: Decimal = Decimal("0")

    def input_digit(self, char: str):
        record_breadcrumb("Input", f"Keyed digit '{char}'", mode=self.mode)
        # Decimal point is strictly forbidden in Programmer mode
        if char in (".", ",") and self.mode == "Programmer":
            return

        rad = getattr(self, "radix", "HEX").upper()
        if not is_char_allowed(char, self.mode, rad):
            return

        if char in (",", "."):
            char = "."

        if self.mode == "Programmer" and rad == "HEX":
            char = char.upper()

        if self.is_unary_active:
            # Typing fresh digits after unary operation starts a brand new number
            self.active_token = "0." if char == "." else char
            self.current_operand_repr = None
            self.is_unary_active = False
            self.is_evaluated = False
            self.has_error = False
            self.last_op_repeat = None
            self._notify()
            return

        if self.has_error or self.is_evaluated:
            # Overwrite after error or evaluation
            self.active_token = "0." if char == "." else char
            if self.is_evaluated:
                self.expression_trail = ""
            self.current_operand_repr = None
            self.is_unary_active = False
            self.is_evaluated = False
            self.has_error = False
            self.last_op_repeat = None
        else:
            if char == ".":
                if "." in self.active_token:
                    return  # Disallow multiple decimals in a single number
                if not self.active_token or self.active_token == "0":
                    self.active_token = "0."
                elif self.active_token == "-0":
                    self.active_token = "-0."
                else:
                    self.active_token += "."
            else:
                if not self.active_token or self.active_token == "0":
                    self.active_token = char
                elif self.active_token == "-0":
                    self.active_token = f"-{char}"
                else:
                    if self.mode != "Programmer":
                        if char.isdigit():
                            digit_count = sum(1 for c in self.active_token if c.isdigit())
                            if digit_count >= 16:
                                return
                    else:
                        rad = getattr(self, "radix", "HEX").upper()
                        clean = self.active_token.lstrip("-")
                        if rad == "HEX" and len(clean) >= 16:
                            return
                        elif rad == "BIN" and len(clean) >= 64:
                            return
                        elif rad == "OCT" and len(clean) >= 22:
                            return
                        elif rad == "DEC" and len(clean) >= 20:
                            return
                    self.active_token += char

                self.active_token = sanitize_leading_zeros(self.active_token, self.mode)

        self._notify()

    def input_operator(self, op: str):
        record_breadcrumb("Input", f"Operator '{op}'", trail=self.expression_trail, active=self.active_token)
        if self.has_error:
            return

        KNOWN_OPS = ("+", "-", "*", "/", "×", "÷", "−", "AND", "OR", "XOR", "<<", ">>", "mod", "%")
        committed_repr = self.current_operand_repr if self.current_operand_repr else self.active_token

        if self.is_evaluated:
            # Ans chaining: use the previous result as the base
            res_str = self.engine.format_number(self.last_result) if self.last_result is not None else "0"
            self.expression_trail = f"{res_str} {op} "
            self._last_committed_val = res_str
            self.active_token = ""
            self.current_operand_repr = None
            self.is_unary_active = False
            self.is_evaluated = False
            self.last_op_repeat = None
        elif self.expression_trail.rstrip().endswith(")") and not self.current_operand_repr:
            # Trailing closed parenthesis: apply operator directly to parenthesized expression
            self.expression_trail = f"{self.expression_trail.rstrip()} {op} "
            self.active_token = ""
            self.current_operand_repr = None
            self.is_unary_active = False
        else:
            if not self.active_token and not self.current_operand_repr:
                # If active_token is empty and we already have a trailing operator, replace it!
                if any(self.expression_trail.rstrip().endswith(o) for o in KNOWN_OPS):
                    tokens = self.expression_trail.strip().split()
                    if tokens:
                        tokens[-1] = op
                        self.expression_trail = " ".join(tokens) + " "
            else:
                self.expression_trail += f"{committed_repr} {op} "
                self._last_committed_val = self.active_token
                self.active_token = ""
                self.current_operand_repr = None
                self.is_unary_active = False

        self._notify()

    def input_unary_operation(self, func_type: str):
        """
        Immediate unary operations: 1/x (recip), x² (sqr), ²√x (sqrt), fact, abs, log, ln.
        Operates immediately on the active token and chains ribbon representation like Windows Calculator.
        """
        record_breadcrumb("Input", f"Unary op '{func_type}'", active=self.active_token)
        if self.has_error:
            return

        if self.active_token:
            operand_str = self.active_token
        elif self.is_evaluated and self.last_result is not None:
            operand_str = self.engine.format_number(self.last_result)
        else:
            operand_str = "0"

        success, val_str, dec_val = self.engine.evaluate(f"{func_type}({operand_str})", mode=self.mode)
        if success and dec_val is not None:
            # Build Windows Calculator style operand representation
            if self.current_operand_repr:
                inner = self.current_operand_repr
            else:
                inner = operand_str

            template = UNARY_DISPLAY_TEMPLATES.get(func_type, f"{func_type}({{x}})")
            self.current_operand_repr = template.format(x=inner)
            self.active_token = val_str
            self.is_unary_active = True
            self.is_evaluated = False
            self._notify()
        else:
            self._trigger_error(val_str)

    def input_percentage(self):
        """
        Context-aware percentage on the active token (Windows Calculator standard behavior).
        - In addition/subtraction ('A + B%', 'A - B%'): calculates B% of A -> (A * (B / 100)),
          replacing active_token with this percentage delta so '=' evaluates A ± (A * B / 100).
        - In multiplication/division ('A * B%', 'A / B%'): calculates B / 100 -> (B / 100).
        - Standalone ('B%'): calculates B / 100.
        """
        record_breadcrumb("Input", "Percentage (%)", trail=self.expression_trail, active=self.active_token)
        if self.has_error:
            return

        # If active_token is empty, check if we have a base or evaluated value
        if not self.active_token:
            if self.is_evaluated and self.last_result is not None:
                self.active_token = self.engine.format_number(self.last_result)
                self.is_evaluated = False
            elif not self.expression_trail:
                return

        trail_clean = self.expression_trail.strip()
        matched_op = None
        for op in ("mod", "+", "-", "*", "/", "×", "÷", "−"):
            if trail_clean.endswith(op):
                matched_op = op
                break

        if matched_op:
            preceding_expr = trail_clean[:-len(matched_op)].strip()
            succ, _, base_dec = self.engine.evaluate(preceding_expr, mode=self.mode) if preceding_expr else (True, "0", Decimal("0"))
            base_val = base_dec if (succ and base_dec is not None) else Decimal("0")

            try:
                act_str = self.active_token.replace(",", "") if self.active_token else str(base_val)
                act_val = Decimal(act_str)
            except Exception:
                act_val = base_val

            if matched_op in ("+", "-", "−"):
                pct_val = base_val * (act_val / Decimal("100"))
            else:  # *, /, ×, ÷, mod
                pct_val = act_val / Decimal("100")

            self.active_token = self.engine.format_number(pct_val)
            self.current_operand_repr = None
            self._notify()
        else:
            try:
                act_str = self.active_token.replace(",", "") if self.active_token else "0"
                act_val = Decimal(act_str)
            except Exception:
                act_val = Decimal("0")
            pct_val = act_val / Decimal("100")
            self.active_token = self.engine.format_number(pct_val)
            self.current_operand_repr = None
            self._notify()

    def negate(self):
        """
        Toggles +/- sign on the active token and syncs preview ribbon representation.
        """
        record_breadcrumb("Input", "Negate (+/-)", active=self.active_token)
        if self.has_error:
            return

        if self.is_evaluated and self.last_result is not None:
            prev_token = self.engine.format_number(self.last_result)
            self.last_result = -self.last_result
            self.active_token = self.engine.format_number(self.last_result)
            self.current_operand_repr = f"negate({prev_token})"
            self.is_evaluated = False
        elif self.current_operand_repr:
            # If current representation already has negate(...) wrap, unwrap it; otherwise wrap
            if self.current_operand_repr.startswith("negate(") and self.current_operand_repr.endswith(")"):
                self.current_operand_repr = self.current_operand_repr[7:-1]
            else:
                self.current_operand_repr = f"negate({self.current_operand_repr})"

            if self.active_token.startswith("-"):
                self.active_token = self.active_token[1:]
            elif self.active_token and self.active_token != "0":
                self.active_token = f"-{self.active_token}"
        else:
            if self.active_token.startswith("-"):
                self.active_token = self.active_token[1:]
                if self.expression_trail:
                    self.current_operand_repr = None
            else:
                if self.active_token and self.active_token != "0":
                    self.active_token = f"-{self.active_token}"
                    if self.expression_trail:
                        self.current_operand_repr = f"negate({self.active_token[1:]})"
                else:
                    self.active_token = "-0"

        self._notify()

    def backspace(self):
        record_breadcrumb("Input", "Backspace", active=self.active_token)
        if self.has_error or self.is_evaluated:
            self.clear_all()
            return

        if self.current_operand_repr or self.is_unary_active:
            self.current_operand_repr = None
            self.is_unary_active = False
            self.active_token = "0"
            self.open_parentheses_count = max(0, self.expression_trail.count("(") - self.expression_trail.count(")"))
            self._notify()
            return

        if self.active_token and self.active_token != "0":
            s = self.active_token[:-1]
            if not s or s == "-":
                self.active_token = "0"
            else:
                self.active_token = s
            self.open_parentheses_count = max(0, self.expression_trail.count("(") - self.expression_trail.count(")"))
            self._notify()
        elif self.expression_trail:
            trail = self.expression_trail.rstrip()
            if trail.endswith(")"):
                self.expression_trail = trail[:-1]
            elif trail.endswith("("):
                if trail.endswith(" × ("):
                    self.expression_trail = trail[:-4]
                else:
                    self.expression_trail = trail[:-1]
            else:
                # Active token is empty or "0", remove the trailing operator and restore previous operand
                tokens = trail.split()
                if tokens:
                    tokens.pop()  # remove operator
                    self.active_token = tokens.pop() if tokens else "0"
                    self.expression_trail = " ".join(tokens) + (" " if tokens else "")

            self.open_parentheses_count = max(0, self.expression_trail.count("(") - self.expression_trail.count(")"))
            self._notify()

    def clear_entry(self):
        """
        CE: Clears only the active token, keeping the expression trail intact!
        """
        record_breadcrumb("Action", "Clear Entry (CE)", active=self.active_token)
        if self.has_error:
            self.clear_all()
        else:
            self.active_token = "0"
            self.current_operand_repr = None
            self.is_unary_active = False
            self._notify()

    def clear_all(self):
        """
        C: Resets all active calculation buffers.
        """
        record_breadcrumb("Action", "Clear All (C)")
        self.expression_trail = ""
        self.active_token = "0"
        self.open_parentheses_count = 0
        self.current_operand_repr = None
        self.is_unary_active = False
        self.pinned_expression = ""
        self.is_evaluated = False
        self.has_error = False
        self.last_op_repeat = None
        self._notify()

    def input_parenthesis(self, paren: str):
        record_breadcrumb("Input", f"Parenthesis '{paren}'", trail=self.expression_trail, active=self.active_token)
        if self.has_error:
            return

        if paren == "(":
            if self.open_parentheses_count >= 50:
                return

            if self.is_evaluated:
                self.expression_trail = "("
                self.active_token = "0"
                self.current_operand_repr = None
                self.is_evaluated = False
                self.open_parentheses_count = 1
                self._notify()
                return

            trail = self.expression_trail.rstrip()
            if trail.endswith(")"):
                self.expression_trail = f"{trail} × ("
                self.active_token = "0"
                self.current_operand_repr = None
                self.open_parentheses_count += 1
            elif self.current_operand_repr:
                self.expression_trail = f"{trail} {self.current_operand_repr} × (".strip()
                self.current_operand_repr = None
                self.active_token = "0"
                self.open_parentheses_count += 1
            elif self.active_token and self.active_token != "0":
                if trail:
                    self.expression_trail = f"{trail} {self.active_token} × ("
                else:
                    self.expression_trail = f"{self.active_token} × ("
                self.active_token = "0"
                self.open_parentheses_count += 1
            else:
                if trail:
                    self.expression_trail = f"{self.expression_trail}("
                else:
                    self.expression_trail = "("
                self.active_token = "0"
                self.open_parentheses_count += 1

            self._notify()

        elif paren == ")":
            if self.open_parentheses_count <= 0:
                return

            trail = self.expression_trail.rstrip()
            if trail.endswith("("):
                tok = self.current_operand_repr if self.current_operand_repr else self.active_token
                self.expression_trail = f"{trail}{tok})"
            elif trail.endswith(")"):
                self.expression_trail = f"{trail})"
            else:
                tok = self.current_operand_repr if self.current_operand_repr else self.active_token
                if tok:
                    self.expression_trail = f"{trail} {tok})".strip()
                else:
                    self.expression_trail = f"{trail})"

            self.open_parentheses_count = max(0, self.open_parentheses_count - 1)
            self.current_operand_repr = None

            # Show evaluated inner value of the closed bracket group in active token display
            last_open = self.expression_trail.rfind("(")
            if last_open != -1:
                sub_expr = self.expression_trail[last_open:]
                succ, val_str, _ = self.engine.evaluate(sub_expr, mode=self.mode)
                if succ and val_str:
                    self.active_token = val_str
                else:
                    self.active_token = "0"
            else:
                self.active_token = "0"

            self._notify()

    def evaluate(self):
        """
        Executes calculation upon pressing '=' or Numpad Enter.
        Supports repeated '=' chaining like Windows Calculator!
        """
        record_breadcrumb("Evaluation", "Evaluate '='", trail=self.expression_trail, active=self.active_token)
        if self.has_error:
            self.clear_all()
            return

        # ─── CASE A: REPEATED EQUALS CHAINING ────────────────────────
        if self.is_evaluated and self.last_op_repeat and self.last_operand_repeat:
            op, operand = self.last_op_repeat, self.last_operand_repeat
            base = self.engine.format_number(self.last_result) if self.last_result else "0"
            expr_to_eval = f"{base} {op} {operand}"
            success, result_str, dec_val = self.engine.evaluate(expr_to_eval, mode=self.mode)
            if success and dec_val is not None:
                self.last_result = dec_val
                self.pinned_expression = f"{expr_to_eval} ="
                self.active_token = result_str
                self._record_history(expr_to_eval, result_str)
                self.on_state_changed(
                    is_evaluated=True,
                    expression_trail=self.pinned_expression,
                    active_token=result_str,
                    live_preview=""
                )
            return

        # ─── CASE B: STANDARD EVALUATION ─────────────────────────────
        # If user pressed '=' with empty expression and active_token is 0
        if not self.expression_trail and (not self.active_token or self.active_token == "0") and not self.current_operand_repr:
            self.pinned_expression = "0 ="
            self.is_evaluated = True
            self.on_state_changed(
                is_evaluated=True,
                expression_trail="0 =",
                active_token="0",
                live_preview=""
            )
            return

        # Build complete display formula for pinned ribbon & expression to evaluate
        if self.open_parentheses_count > 0:
            trail = self.expression_trail.rstrip()
            if trail.endswith("(") or any(trail.endswith(op) for op in ("+", "-", "*", "/", "×", "÷", "−")):
                if self.active_token:
                    trail = f"{trail} {self.active_token}"
            elif not trail.endswith(")"):
                if self.active_token and self.active_token != "0":
                    trail = f"{trail} {self.active_token}"
            trail += ")" * self.open_parentheses_count
            self.open_parentheses_count = 0
            display_formula = trail
            expr_to_eval = trail
        elif self.expression_trail.rstrip().endswith(")") and not self.current_operand_repr:
            display_formula = self.expression_trail.strip()
            expr_to_eval = self.expression_trail.strip()
        else:
            final_repr = self.current_operand_repr if self.current_operand_repr else self.active_token
            if final_repr:
                display_formula = f"{self.expression_trail.strip()} {final_repr.strip()}".strip()
            else:
                display_formula = self.expression_trail.strip()

            if self.active_token:
                expr_to_eval = f"{self.expression_trail.strip()} {self.active_token.strip()}".strip()
            else:
                expr_to_eval = self.expression_trail.strip()

        # Capture repeat operation components
        tokens = expr_to_eval.split()
        KNOWN_OPS = ("+", "-", "*", "/", "×", "÷", "−", "AND", "OR", "XOR", "<<", ">>", "mod", "%")
        if len(tokens) >= 3 and tokens[-2] in KNOWN_OPS:
            self.last_op_repeat = tokens[-2]
            self.last_operand_repeat = tokens[-1]

        success, result_str, dec_val = self.engine.evaluate(expr_to_eval, mode=self.mode)

        if success and dec_val is not None:
            self.last_result = dec_val
            self.pinned_expression = f"{display_formula} ="
            self.is_evaluated = True
            self.active_token = result_str
            self.expression_trail = ""
            self.current_operand_repr = None
            self.is_unary_active = False

            self._record_history(display_formula, result_str)

            self.on_state_changed(
                is_evaluated=True,
                expression_trail=self.pinned_expression,
                active_token=result_str,
                live_preview=""
            )
        else:
            self._trigger_error(result_str)

    def restore_expression(self, expr: str):
        self.clear_all()
        tokens = expr.strip().split()
        if tokens:
            self.active_token = sanitize_leading_zeros(tokens[-1], self.mode)
            self.expression_trail = " ".join(tokens[:-1]) + (" " if len(tokens) > 1 else "")
        else:
            self.active_token = "0"
        self.open_parentheses_count = max(0, self.expression_trail.count("(") - self.expression_trail.count(")"))
        self._notify()

    def _trigger_error(self, message: str):
        self.has_error = True
        self.active_token = message
        self.on_state_changed(
            is_evaluated=False,
            expression_trail=self.expression_trail,
            active_token=message,
            live_preview=""
        )

    def _record_history(self, expression: str, result: str):
        try:
            self.db.add_calculation(expression=expression, result=result, mode=self.mode)
        except Exception:
            pass

    def _notify(self):
        # Determine the display trail
        if self.is_evaluated:
            displayed_trail = self.pinned_expression
        elif self.current_operand_repr:
            displayed_trail = f"{self.expression_trail}{self.current_operand_repr}"
        else:
            displayed_trail = self.expression_trail

        # Calculate real-time live preview if expression features are present
        live_ghost = ""
        full_expr = f"{self.expression_trail.strip()} {self.active_token.strip()}".strip()

        if full_expr and not self.is_evaluated and not self.has_error:
            if not is_expression_incomplete(full_expr):
                has_expr_features = (
                    bool(self.expression_trail)
                    or any(ch in full_expr for ch in ("+", "*", "/", "×", "÷", "^", "%", "(", ")"))
                    or ("-" in full_expr and not (full_expr.startswith("-") and "-" not in full_expr[1:]))
                    or any(fn in full_expr.lower() for fn in ("sin", "cos", "tan", "log", "ln", "sqrt", "mod", "fact", "abs", "pi", "e"))
                )
                if has_expr_features:
                    try:
                        success, val, _ = self.engine.evaluate(full_expr, mode=self.mode, allow_incomplete=False)
                        if success and val and val != self.active_token:
                            live_ghost = val
                    except Exception:
                        pass

        self.on_state_changed(
            is_evaluated=self.is_evaluated,
            expression_trail=displayed_trail,
            active_token=self.active_token,
            live_preview=live_ghost
        )
