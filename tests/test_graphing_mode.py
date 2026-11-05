"""
Rigorous test suite for Graphing Mode and Windows Blur Effect:
- GraphFunction engine: preprocessing, implicit multiplication, sandboxed evaluation,
  asymptote splitting, parameter resolution, Key Graph Features (roots, y-intercepts, extrema).
- GraphCanvas: coordinate transformation, zooming, panning, theme token propagation.
- GraphingView UI: equation deck, multi-function rows, dynamic parameter sliders, KGF panel.
- MainWindow: mode switching to 'Graphing', theme integration.
- Windows Blur Effect: safe Win32 API invocation and semi-transparent QSS styling.
- Zero emojis compliance across all components.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import math
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtWidgets import QApplication

from src.core.graph_engine import GraphFunction
from src.ui.graph_canvas import GraphCanvas, CURVE_PALETTE
from src.ui.graphing_view import GraphingView, FunctionRowWidget
from src.ui.main_window import MainWindow
from src.ui.theme_manager import ThemeManager
from src.ui.window_effects import apply_window_blur, remove_window_blur

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestGraphEngine(unittest.TestCase):
    """Rigorous tests for the mathematical graph expression engine."""

    def test_polynomial_evaluation(self):
        fn = GraphFunction("x^2 - 4")
        self.assertTrue(fn.is_valid)
        self.assertAlmostEqual(fn.eval_single(0.0), -4.0)
        self.assertAlmostEqual(fn.eval_single(2.0), 0.0)
        self.assertAlmostEqual(fn.eval_single(-2.0), 0.0)
        self.assertAlmostEqual(fn.eval_single(3.0), 5.0)

    def test_implicit_multiplication(self):
        # 2x
        fn1 = GraphFunction("2x + 1")
        self.assertTrue(fn1.is_valid)
        self.assertAlmostEqual(fn1.eval_single(3.0), 7.0)

        # 3(x + 2)
        fn2 = GraphFunction("3(x + 2)")
        self.assertTrue(fn2.is_valid)
        self.assertAlmostEqual(fn2.eval_single(4.0), 18.0)

        # (x - 1)(x + 1)
        fn3 = GraphFunction("(x - 1)(x + 1)")
        self.assertTrue(fn3.is_valid)
        self.assertAlmostEqual(fn3.eval_single(3.0), 8.0)

        # 4sin(x)
        fn4 = GraphFunction("4sin(x)")
        self.assertTrue(fn4.is_valid)
        self.assertAlmostEqual(fn4.eval_single(0.0), 0.0)

    def test_trigonometric_and_transcendental_functions(self):
        fn = GraphFunction("sin(x) + cos(x)")
        self.assertTrue(fn.is_valid)
        self.assertAlmostEqual(fn.eval_single(0.0), 1.0)

        fn_exp = GraphFunction("exp(x)")
        self.assertTrue(fn_exp.is_valid)
        self.assertAlmostEqual(fn_exp.eval_single(0.0), 1.0)
        self.assertAlmostEqual(fn_exp.eval_single(1.0), math.e)

        fn_log = GraphFunction("log(x)")
        self.assertTrue(fn_log.is_valid)
        self.assertAlmostEqual(fn_log.eval_single(math.e), 1.0)
        # Undefined for non-positive values
        self.assertIsNone(fn_log.eval_single(-1.0))
        self.assertIsNone(fn_log.eval_single(0.0))

    def test_parameter_detection_and_dynamic_evaluation(self):
        fn = GraphFunction("m*x + b")
        self.assertTrue(fn.is_valid)
        self.assertIn("m", fn.parameters)
        self.assertIn("b", fn.parameters)
        self.assertNotIn("x", fn.parameters)

        # Evaluate with custom parameter dictionary
        res1 = fn.eval_single(5.0, params={"m": 2.0, "b": 3.0})
        self.assertAlmostEqual(res1, 13.0)

        res2 = fn.eval_single(5.0, params={"m": -1.0, "b": 10.0})
        self.assertAlmostEqual(res2, 5.0)

    def test_invalid_and_malicious_inputs_handled_safely(self):
        # Empty string
        empty_fn = GraphFunction("")
        self.assertFalse(empty_fn.is_valid)
        self.assertIsNone(empty_fn.eval_single(1.0))

        # Syntax errors
        bad_syntax = GraphFunction("x + * 5")
        self.assertFalse(bad_syntax.is_valid)
        self.assertIsNone(bad_syntax.eval_single(1.0))

        # Malicious code injection attempt
        injection = GraphFunction("__import__('os').system('dir')")
        self.assertFalse(injection.is_valid)
        self.assertIsNone(injection.eval_single(0.0))

    def test_asymptote_and_discontinuity_splitting(self):
        fn = GraphFunction("tan(x)")
        # Range across discontinuity at x = pi/2 (~1.5707)
        segments = fn.eval_range(0.0, 3.14, num_points=200)
        # Should produce multiple segments rather than one continuous line across asymptote
        self.assertGreater(len(segments), 1)

    def test_key_graph_features_extraction(self):
        # f(x) = x^2 - 4
        fn = GraphFunction("x^2 - 4")
        kgf = fn.compute_key_features(x_min=-5.0, x_max=5.0)

        # Roots should include -2.0 and 2.0
        self.assertEqual(len(kgf["roots"]), 2)
        roots_x = sorted([r[0] for r in kgf["roots"]])
        self.assertAlmostEqual(roots_x[0], -2.0, places=1)
        self.assertAlmostEqual(roots_x[1], 2.0, places=1)

        # y-intercept at (0, -4)
        self.assertIsNotNone(kgf["y_intercept"])
        self.assertAlmostEqual(kgf["y_intercept"][0], 0.0)
        self.assertAlmostEqual(kgf["y_intercept"][1], -4.0)

        # Local minimum at (0, -4)
        minima = [e for e in kgf["extrema"] if e[0] == "Minimum"]
        self.assertGreaterEqual(len(minima), 1)
        self.assertAlmostEqual(minima[0][1], 0.0, places=1)
        self.assertAlmostEqual(minima[0][2], -4.0, places=1)


class TestGraphCanvas(unittest.TestCase):
    """Tests for the interactive Cartesian coordinate graph canvas."""

    def setUp(self):
        self.canvas = GraphCanvas()
        self.canvas.resize(400, 300)
        self.canvas.show()

    def tearDown(self):
        self.canvas.deleteLater()

    def test_coordinate_transforms(self):
        # Default bounds [-10, 10] on 400x300 widget
        pt_origin = self.canvas.math_to_pixel(0.0, 0.0)
        self.assertAlmostEqual(pt_origin.x(), 200.0, delta=2.0)
        self.assertAlmostEqual(pt_origin.y(), 150.0, delta=2.0)

        # Invert pixel back to math
        mx, my = self.canvas.pixel_to_math(pt_origin.x(), pt_origin.y())
        self.assertAlmostEqual(mx, 0.0, delta=0.1)
        self.assertAlmostEqual(my, 0.0, delta=0.1)

    def test_zoom_functionality(self):
        # Zoom in by factor 0.5
        orig_w = self.canvas.x_max - self.canvas.x_min
        self.canvas.zoom(0.5)
        new_w = self.canvas.x_max - self.canvas.x_min
        self.assertAlmostEqual(new_w, orig_w * 0.5)

        # Reset view
        self.canvas.reset_view()
        self.assertEqual(self.canvas.x_min, -10.0)
        self.assertEqual(self.canvas.x_max, 10.0)

    def test_theme_tokens_applied(self):
        tokens = {
            "bg_surface": "#123456",
            "border_subtle": "#654321",
            "text_secondary": "#ABCDEF",
            "bg_card": "#FEDCBA"
        }
        self.canvas.set_theme_tokens(tokens)
        self.assertEqual(self.canvas.theme_colors["bg"], "#123456")
        self.assertEqual(self.canvas.theme_colors["grid_major"], "#654321")
        self.assertEqual(self.canvas.theme_colors["axis"], "#ABCDEF")


class TestGraphingView(unittest.TestCase):
    """Tests for the GraphingView equation deck, sliders, and KGF card."""

    def setUp(self):
        self.view = GraphingView()
        self.view.resize(500, 600)
        self.view.show()

    def tearDown(self):
        self.view.deleteLater()

    def test_initial_seed_function(self):
        self.assertEqual(len(self.view.function_rows), 1)
        first_row = self.view.function_rows[0]
        self.assertEqual(first_row.expr_input.text(), "x^2 - 4")
        self.assertTrue(first_row.graph_fn.is_valid)

    def test_add_and_remove_functions(self):
        # Add second function
        self.view._add_function_row("sin(x)")
        self.assertEqual(len(self.view.function_rows), 2)
        self.assertEqual(self.view.function_rows[1].lbl_fn.text(), "f2(x) =")

        # Delete first function
        first_row = self.view.function_rows[0]
        self.view._remove_function_row(first_row)
        self.assertEqual(len(self.view.function_rows), 1)
        # Remaining row should be re-indexed to f1
        self.assertEqual(self.view.function_rows[0].lbl_fn.text(), "f1(x) =")

    def test_dynamic_parameter_slider_generation(self):
        # Add equation with parameters 'm' and 'b'
        self.view._add_function_row("m*x + b")
        self.assertTrue(self.view.sliders_container.isVisible())
        self.assertIn("m", self.view.parameter_sliders)
        self.assertIn("b", self.view.parameter_sliders)

        # Move 'm' slider
        m_slider, m_lbl = self.view.parameter_sliders["m"]
        m_slider.setValue(25)  # maps to 2.5
        self.assertAlmostEqual(self.view.parameter_values["m"], 2.5)

    def test_key_features_toggle(self):
        self.assertTrue(self.view.kgf_card.isVisible())
        self.view.btn_kgf_toggle.setChecked(False)
        self.view._toggle_kgf_panel()
        self.assertFalse(self.view.kgf_card.isVisible())


class TestMainWindowGraphingIntegration(unittest.TestCase):
    """Integration tests verifying Graphing mode within MainWindow."""

    @classmethod
    def setUpClass(cls):
        cls.win = MainWindow(check_updates=False)
        cls.win._disable_win32_filter_for_testing = True
        cls.win.resize(380, 600)
        cls.win.show()

    @classmethod
    def tearDownClass(cls):
        cls.win.deleteLater()

    def test_switch_to_graphing_mode(self):
        self.win._switch_mode("Graphing", save_config=False)
        self.assertEqual(self.win.mode_title.text(), "Graphing")
        self.assertEqual(self.win.stack.currentIndex(), 3)
        self.assertEqual(self.win.stack.currentWidget(), self.win.graphing_page)
        self.assertFalse(self.win.display.isVisible())
        self.assertFalse(self.win.mem_bar.isVisible())
        self.assertFalse(self.win.history_btn.isVisible())
        self.assertTrue(self.win.graphing_page.isVisible())

    def test_theme_propagation_to_graph_canvas(self):
        # Apply dark monokai theme
        self.win.theme_mgr.set_theme("dark_monokai")
        self.win._apply_theme()
        canvas = self.win.graphing_page.canvas
        tokens = self.win.theme_mgr.current_tokens
        self.assertEqual(canvas.theme_colors["bg"], tokens["bg_surface"])

    def test_zero_emojis_in_graphing_view(self):
        # Scan all buttons and labels in GraphingView
        graph_view = self.win.graphing_page
        all_widgets = graph_view.findChildren((FunctionRowWidget, GraphCanvas))
        buttons = graph_view.findChildren(type(self.win.hamburger_btn))
        labels = graph_view.findChildren(type(self.win.mode_title))

        for btn in buttons:
            txt = btn.text()
            # Ensure no unicode emoji range
            for ch in txt:
                self.assertFalse(
                    0x1F300 <= ord(ch) <= 0x1FAD6 or 0x2600 <= ord(ch) <= 0x27BF,
                    f"Forbidden emoji found in button text: '{txt}'"
                )

        for lbl in labels:
            txt = lbl.text()
            for ch in txt:
                self.assertFalse(
                    0x1F300 <= ord(ch) <= 0x1FAD6 or 0x2600 <= ord(ch) <= 0x27BF,
                    f"Forbidden emoji found in label text: '{txt}'"
                )


class TestWindowsBlurEffect(unittest.TestCase):
    """Tests for native Windows Acrylic/Mica blur behind effect."""

    def test_blur_toggle_in_theme_manager(self):
        tm = ThemeManager()
        # With blur enabled: rgba background with transparency
        qss_blur = tm.generate_qss(blur_enabled=True)
        self.assertIn("rgba(", qss_blur)

        # With blur disabled: opaque background
        qss_solid = tm.generate_qss(blur_enabled=False)
        self.assertIn("background-color: #", qss_solid)

    def test_safe_invocation_of_blur_helpers(self):
        # Test calling the helper functions with a mock window handle
        # Should execute safely on Windows without throwing unhandled exceptions
        try:
            apply_window_blur(0, dark_mode=True)
            remove_window_blur(0)
        except Exception as e:
            self.fail(f"Window blur helpers raised an unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
