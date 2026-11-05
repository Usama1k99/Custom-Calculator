"""
Mathematical Graphing Engine for Custom-Calculator.
Provides:
- Robust mathematical expression parsing and conversion from natural notation to evaluable functions
- Handles implicit multiplication (e.g. 2x, 3sin(x), (x+1)(x-1), 5pi)
- Fast vector evaluation of f(x) over [x_min, x_max] with asymptote / discontinuity splitting
- Support for secondary parameters (sliders) like m, a, b, k
- Key Graph Features (KGF) extraction:
    * y-intercept: (0, f(0))
    * x-intercepts (Roots): real roots via sign-change bisection
    * Local Extrema: Minima and Maxima detection
- Zero external heavy dependencies (uses standard math and builtins).
"""

import math
import re
from typing import List, Tuple, Dict, Any, Optional, Callable


# Standard mathematical function environment
MATH_ENV = {
    # Trigonometric (input in radians)
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sec": lambda x: 1.0 / math.cos(x) if math.cos(x) != 0 else float("nan"),
    "csc": lambda x: 1.0 / math.sin(x) if math.sin(x) != 0 else float("nan"),
    "cot": lambda x: 1.0 / math.tan(x) if math.tan(x) != 0 else float("nan"),
    # Inverse Trigonometric
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    # Hyperbolic
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    # Exponential & Logarithmic
    "exp": math.exp,
    "ln": math.log,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    # Power & Roots
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1.0 / 3.0), x),
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    # Constants
    "pi": math.pi,
    "e": math.e,
}


class GraphFunction:
    """Represents a compiled, evaluable single-variable mathematical function."""

    def __init__(self, expression_str: str, color: str = "#38BDF8"):
        self.raw_expression = expression_str.strip()
        self.color = color
        self.is_visible = True
        self.compiled_code = None
        self.parameters = []  # Detected parameter names like ['m', 'b']
        self.error_message = ""

        self._compile()

    @property
    def is_valid(self) -> bool:
        """Returns True if the expression was parsed and compiled successfully."""
        return self.compiled_code is not None

    def eval_single(self, x_val: float, params: Optional[Dict[str, float]] = None) -> Optional[float]:
        """Convenience alias for evaluate()."""
        return self.evaluate(x_val, params)

    def eval_range(
        self,
        x_min: float,
        x_max: float,
        num_points: int = 800,
        params: Optional[Dict[str, float]] = None
    ) -> List[List[Tuple[float, float]]]:
        """Convenience alias for evaluate_range()."""
        return self.evaluate_range(x_min, x_max, num_points, params)

    def compute_key_features(
        self,
        x_min: float = -10.0,
        x_max: float = 10.0,
        params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Convenience alias for find_key_features()."""
        return self.find_key_features(x_min, x_max, params)

    def _clean_and_preprocess(self, expr: str) -> str:
        s = expr.strip()
        # Remove 'y =' or 'f(x) =' prefix if entered
        s = re.sub(r"^(?:y|f\s*\(\s*x\s*\))\s*=\s*", "", s, flags=re.IGNORECASE)

        # Replace '^' with '**'
        s = s.replace("^", "**")

        # Replace '|x|' with 'abs(x)'
        s = re.sub(r"\|([^|]+)\|", r"abs(\1)", s)

        # Common aliases
        s = re.sub(r"\btg\(", "tan(", s)
        s = re.sub(r"\bctg\(", "cot(", s)

        # Implicit multiplication transformations:
        # 1. Number followed by variable or function: e.g. 2x -> 2*x, 3sin(x) -> 3*sin(x), 5pi -> 5*pi
        s = re.sub(r"(\d+)([a-zA-Z\(])", r"\1*\2", s)

        # 2. Closing paren followed by opening paren or variable: e.g. (x+1)(x-1) -> (x+1)*(x-1)
        s = re.sub(r"\)\s*\(", ")*(", s)
        s = re.sub(r"\)\s*([a-zA-Z\d])", r")*\1", s)

        # 3. Variable 'x' followed by function: e.g. x sin(x) -> x*sin(x)
        s = re.sub(r"\bx\s+([a-zA-Z])", r"x*\1", s)

        # 4. Standalone 'e' exponent like e^x -> exp(x)
        s = re.sub(r"\be\s*\*\*\s*([a-zA-Z\d]+)", r"exp(\1)", s)
        s = re.sub(r"\be\s*\*\*\s*\(([^)]+)\)", r"exp(\1)", s)

        return s

    def _compile(self):
        self.error_message = ""
        self.compiled_code = None
        self.parameters = []

        if not self.raw_expression:
            return

        # Security: block dangerous tokens, dunder attributes, and system calls
        if re.search(r"__|\b(?:import|exec|eval|compile|builtins|open|getattr|setattr|delattr|os|sys|subprocess)\b", self.raw_expression, re.IGNORECASE):
            self.error_message = "Forbidden syntax"
            return

        try:
            processed = self._clean_and_preprocess(self.raw_expression)

            # Detect secondary parameter variables: any single letter a-z except x, e
            known_words = set(MATH_ENV.keys()) | {"x"}
            identifiers = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", processed)
            for ident in identifiers:
                if ident not in known_words:
                    if ident not in self.parameters:
                        self.parameters.append(ident)

            # Compile into bytecode for fast repetitive evaluation across coordinate points
            self.compiled_code = compile(processed, "<graph_expr>", "eval")
        except Exception as e:
            self.error_message = str(e)
            self.compiled_code = None

    def evaluate(self, x_val: float, params: Optional[Dict[str, float]] = None) -> Optional[float]:
        """Evaluates f(x) safely for a single point x."""
        if not self.compiled_code:
            return None

        scope = dict(MATH_ENV)
        scope["x"] = x_val
        if params:
            scope.update(params)

        try:
            val = eval(self.compiled_code, {"__builtins__": {}}, scope)
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    return None
                return float(val)
        except Exception:
            return None

        return None

    def evaluate_range(
        self,
        x_min: float,
        x_max: float,
        num_points: int = 800,
        params: Optional[Dict[str, float]] = None
    ) -> List[List[Tuple[float, float]]]:
        """
        Evaluates f(x) across [x_min, x_max] and splits into continuous sub-segments
        whenever a discontinuity or asymptote (e.g. tan(x), 1/x) is encountered.
        """
        if not self.compiled_code or x_max <= x_min or num_points < 2:
            return []

        dx = (x_max - x_min) / float(num_points - 1)
        segments: List[List[Tuple[float, float]]] = []
        current_segment: List[Tuple[float, float]] = []

        prev_y = None

        for i in range(num_points):
            x = x_min + i * dx
            y = self.evaluate(x, params)

            if y is None:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
                prev_y = None
                continue

            # Asymptote / Discontinuity check:
            # If y jumps sharply between positive and negative extremes across a single step, break segment!
            if prev_y is not None:
                dy = abs(y - prev_y)
                # If sign changes and magnitude is very large compared to dx
                if (prev_y * y < 0 and dy > 50.0) or (dy > 1000.0):
                    if current_segment:
                        segments.append(current_segment)
                        current_segment = []

            current_segment.append((x, y))
            prev_y = y

        if current_segment:
            segments.append(current_segment)

        return segments

    def find_key_features(
        self,
        x_min: float = -10.0,
        x_max: float = 10.0,
        params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Extracts Key Graph Features (KGF):
        - y-intercept (0, f(0))
        - x-intercepts (Roots) via sign-change bisection search
        - Local Extrema (Minima and Maxima)
        """
        features = {
            "y_intercept": None,
            "roots": [],
            "extrema": [],
        }

        if not self.compiled_code:
            return features

        # 1. y-intercept: (0, f(0))
        if x_min <= 0.0 <= x_max:
            y_zero = self.evaluate(0.0, params)
            if y_zero is not None and not math.isnan(y_zero):
                features["y_intercept"] = (0.0, round(y_zero, 4))

        # 2. Roots (x-intercepts) search
        num_steps = 400
        step = (x_max - x_min) / float(num_steps)
        prev_x = x_min
        prev_y = self.evaluate(prev_x, params)

        roots = []
        for i in range(1, num_steps + 1):
            curr_x = x_min + i * step
            curr_y = self.evaluate(curr_x, params)

            if prev_y is not None and curr_y is not None:
                # Direct zero hit
                if abs(curr_y) < 1e-9:
                    roots.append((round(curr_x, 4), 0.0))
                # Sign change -> perform bisection refinement
                elif prev_y * curr_y < 0 and abs(curr_y - prev_y) < 50.0:
                    root = self._bisect_root(prev_x, curr_x, params)
                    if root is not None:
                        # Avoid duplicates
                        if not any(abs(root - r[0]) < 1e-3 for r in roots):
                            roots.append((round(root, 4), 0.0))

            prev_x = curr_x
            prev_y = curr_y

        features["roots"] = roots[:8]  # Limit to 8 primary visible roots

        # 3. Local Extrema (Minima and Maxima)
        extrema = []
        samples = []
        eval_steps = 200
        dx = (x_max - x_min) / float(eval_steps)
        for i in range(eval_steps + 1):
            x = x_min + i * dx
            y = self.evaluate(x, params)
            samples.append((x, y))

        for i in range(1, len(samples) - 1):
            y_prev = samples[i - 1][1]
            y_curr = samples[i][1]
            y_next = samples[i + 1][1]

            if y_prev is not None and y_curr is not None and y_next is not None:
                # Local Maximum
                if y_curr > y_prev and y_curr > y_next:
                    extrema.append(("Maximum", round(samples[i][0], 3), round(y_curr, 3)))
                # Local Minimum
                elif y_curr < y_prev and y_curr < y_next:
                    extrema.append(("Minimum", round(samples[i][0], 3), round(y_curr, 3)))

        features["extrema"] = extrema[:6]
        return features

    def _bisect_root(self, x1: float, x2: float, params: Optional[Dict[str, float]], max_iter: int = 24) -> Optional[float]:
        y1 = self.evaluate(x1, params)
        y2 = self.evaluate(x2, params)
        if y1 is None or y2 is None or y1 * y2 > 0:
            return None

        a, b = x1, x2
        for _ in range(max_iter):
            mid = 0.5 * (a + b)
            y_mid = self.evaluate(mid, params)
            if y_mid is None:
                return None
            if abs(y_mid) < 1e-9 or (b - a) < 1e-6:
                return mid
            if y1 * y_mid < 0:
                b = mid
                y2 = y_mid
            else:
                a = mid
                y1 = y_mid

        return 0.5 * (a + b)
