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
        self.is_evaluated = False
        self.has_error = False

        # Repeated equals support: preserves (last_operator, last_operand)
        self.last_op_repeat = None
        self.last_operand_repeat = None

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

        if self.has_error or self.is_evaluated:
            # Overwrite after error or evaluation
            self.active_token = "0." if char == "." else char
            if self.is_evaluated:
                self.expression_trail = ""
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
                    self.active_token += char

                self.active_token = sanitize_leading_zeros(self.active_token, self.mode)

        self._notify()

    def input_operator(self, op: str):
        record_breadcrumb("Input", f"Operator '{op}'", trail=self.expression_trail, active=self.active_token)
        if self.has_error:
            return

        KNOWN_OPS = ("+", "-", "*", "/", "×", "÷", "−", "AND", "OR", "XOR", "<<", ">>", "mod", "%")

        if self.is_evaluated:
            # Ans chaining: use the previous result as the base
            res_str = self.engine.format_number(self.last_result) if self.last_result is not None else "0"
            self.expression_trail = f"{res_str} {op} "
            self._last_committed_val = res_str
            self.active_token = ""
            self.is_evaluated = False
            self.last_op_repeat = None
        else:
            if not self.active_token:
                # If active_token is empty and we already have a trailing operator, replace it!
                if any(self.expression_trail.rstrip().endswith(o) for o in KNOWN_OPS):
                    tokens = self.expression_trail.strip().split()
                    if tokens:
                        tokens[-1] = op
                        self.expression_trail = " ".join(tokens) + " "
            else:
                self.expression_trail += f"{self.active_token} {op} "
                self._last_committed_val = self.active_token
                self.active_token = ""

        self._notify()

    def input_unary_operation(self, func_type: str):
        """
        Immediate unary operations: 1/x (recip), x² (sqr), ²√x (sqrt), fact, abs, log, ln.
        Operates immediately on the active token!
        """
        record_breadcrumb("Input", f"Unary op '{func_type}'", active=self.active_token)
        if self.has_error:
            return

        operand_str = self.active_token if self.active_token else (
            self.engine.format_number(self.last_result) if self.last_result else "0"
        )

        success, val_str, dec_val = self.engine.evaluate(f"{func_type}({operand_str})", mode=self.mode)
        if success and dec_val is not None:
            self.active_token = val_str
            self.is_evaluated = False
            self._notify()
        else:
            self._trigger_error(val_str)

    def input_percentage(self):
        """
        Context-aware percentage on the active token.
        """
        record_breadcrumb("Input", "Percentage (%)", trail=self.expression_trail, active=self.active_token)
        if self.has_error or not self.active_token:
            return

        # If we have an expression trail like "100 +", B% calculates (100 * (B / 100))
        full_expr = f"{self.expression_trail} {self.active_token}%"
        success, val_str, dec_val = self.engine.evaluate(full_expr, mode=self.mode)
        if success and dec_val is not None:
            self.active_token = val_str
            self._notify()

    def negate(self):
        """
        Toggles +/- sign on the active token.
        """
        record_breadcrumb("Input", "Negate (+/-)", active=self.active_token)
        if self.has_error:
            return

        if self.is_evaluated and self.last_result is not None:
            self.last_result = -self.last_result
            self.active_token = self.engine.format_number(self.last_result)
            self.is_evaluated = False
        else:
            if self.active_token.startswith("-"):
                self.active_token = self.active_token[1:]
            else:
                if self.active_token and self.active_token != "0":
                    self.active_token = f"-{self.active_token}"
                elif not self.active_token:
                    self.active_token = "-0"

        self._notify()

    def backspace(self):
        record_breadcrumb("Input", "Backspace", active=self.active_token)
        if self.has_error or self.is_evaluated:
            self.clear_all()
            return

        if self.active_token:
            s = self.active_token[:-1]
            if not s or s == "-":
                self.active_token = "0"
            else:
                self.active_token = s
            self._notify()
        elif self.expression_trail:
            # Active token is empty, remove the trailing operator and restore previous operand
            tokens = self.expression_trail.strip().split()
            if tokens:
                tokens.pop()  # remove operator
                self.active_token = tokens.pop() if tokens else "0"
                self.expression_trail = " ".join(tokens) + (" " if tokens else "")
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
            self._notify()

    def clear_all(self):
        """
        C: Resets all active calculation buffers.
        """
        record_breadcrumb("Action", "Clear All (C)")
        self.expression_trail = ""
        self.active_token = "0"
        self.pinned_expression = ""
        self.is_evaluated = False
        self.has_error = False
        self.last_op_repeat = None
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
        if not self.expression_trail and (not self.active_token or self.active_token == "0"):
            self.pinned_expression = "0 ="
            self.is_evaluated = True
            self.on_state_changed(
                is_evaluated=True,
                expression_trail="0 =",
                active_token="0",
                live_preview=""
            )
            return

        # Build complete formula
        if self.active_token:
            expr_to_eval = f"{self.expression_trail.strip()} {self.active_token.strip()}".strip()
        else:
            # Incomplete expression like "5 + " -> repeat operand: "5 + 5"
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
            self.pinned_expression = f"{expr_to_eval} ="
            self.is_evaluated = True
            self.active_token = result_str
            self.expression_trail = ""

            self._record_history(expr_to_eval, result_str)

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
        # Calculate real-time live preview if multiple operands or expressions present
        live_ghost = ""
        full_expr = f"{self.expression_trail.strip()} {self.active_token.strip()}".strip()

        # If expression is incomplete (e.g. ends with an operator like "60 +" or open parenthesis),
        # NEVER calculate or show preview!
        if full_expr and not self.is_evaluated and not self.has_error:
            if not is_expression_incomplete(full_expr):
                has_expr_features = (
                    bool(self.expression_trail)
                    or any(ch in full_expr for ch in ("+", "-", "*", "/", "×", "÷", "^", "%", "(", ")"))
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
            expression_trail=self.pinned_expression if self.is_evaluated else self.expression_trail,
            active_token=self.active_token,
            live_preview=live_ghost
        )
