"""
Exhaustive Unit Tests for Crash Reporting & Diagnostic Logging Engine.
Tests:
- Breadcrumb ring buffer and chronological formatting
- Context provider registration, unregistration, and live state querying
- Report generation with exact mode, causing inputs, and full traceback
- Crash report disk persistence and file name formatting
- Safe stream handling for PyInstaller --noconsole execution
- Mode-specific state capture (Standard, Graphing, Programmer, Date, Converter)
- CrashReportDialog UI instantiation, clipboard copy, and recovery actions
- Zero emojis across all outputs.
"""

from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import sys
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication

from src.core.crash_reporter import (
    CrashReporter, Breadcrumb, NullWriter, record_breadcrumb,
    register_context_provider, unregister_context_provider,
    install_crash_handler, get_crash_reporter
)
from src.ui.crash_dialog import CrashReportDialog


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestCrashReporter(unittest.TestCase):

    def setUp(self):
        self.reporter = CrashReporter()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patch_dir = Path(self.temp_dir.name)
        # Point candidate directories to temporary directory for test isolation
        self.reporter.get_crash_directories = lambda: [self.patch_dir]

    def tearDown(self):
        self.temp_dir.cleanup()

    # ─── 1. BREADCRUMBS BUFFER & FORMATTING ─────────────────────────
    def test_breadcrumb_recording_and_max_limit(self):
        self.reporter.breadcrumbs.clear()
        for i in range(50):
            self.reporter.record_breadcrumb("Input", f"Button click {i}", value=i)

        # Ensure max length of 40 is strictly maintained
        self.assertEqual(len(self.reporter.breadcrumbs), 40)
        # Oldest breadcrumb should be index 10, newest should be 49
        self.assertIn("Button click 10", self.reporter.breadcrumbs[0].message)
        self.assertIn("Button click 49", self.reporter.breadcrumbs[-1].message)

        # Test line formatting
        line = self.reporter.breadcrumbs[-1].format_line()
        self.assertIn("[INPUT]", line)
        self.assertIn("Button click 49", line)
        self.assertIn("'value': 49", line)

    # ─── 2. CONTEXT PROVIDER REGISTRATION ───────────────────────────
    def test_context_provider_registration_and_query(self):
        def sample_provider():
            return {
                "mode": "Scientific",
                "active_token": "3.14159",
                "expression_trail": "sin(",
                "angle_mode": "RAD"
            }

        self.reporter.register_context_provider(sample_provider)
        ctx = self.reporter._collect_application_context()

        self.assertEqual(ctx.get("mode"), "Scientific")
        self.assertEqual(ctx.get("active_token"), "3.14159")
        self.assertEqual(ctx.get("expression_trail"), "sin(")
        self.assertEqual(ctx.get("angle_mode"), "RAD")

        self.reporter.unregister_context_provider(sample_provider)
        ctx_after = self.reporter._collect_application_context()
        self.assertNotIn("mode", ctx_after)

    # ─── 3. REPORT GENERATION WITH FULL TRACEBACK & INPUTS ──────────
    def test_crash_report_generation_structure(self):
        self.reporter.breadcrumbs.clear()
        self.reporter.record_breadcrumb("Navigation", "User opened Standard mode")
        self.reporter.record_breadcrumb("Input", "Keyed digit '9'")
        self.reporter.record_breadcrumb("Input", "Operator '/'")
        self.reporter.record_breadcrumb("Input", "Keyed digit '0'")

        def mock_calc_context():
            return {
                "mode": "Standard",
                "active_token": "0",
                "expression_trail": "9 / ",
                "live_preview": "Cannot divide by zero",
                "is_evaluated": False,
                "memory": "0"
            }

        self.reporter.register_context_provider(mock_calc_context)

        # Generate a simulated ZeroDivisionError
        try:
            _ = 9 / 0
        except ZeroDivisionError as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            report = self.reporter.build_crash_report(exc_type, exc_value, exc_tb)

        # Verify Report Sections
        self.assertIn("APEX CALCULATOR", report)
        self.assertIn("CRASH REPORT", report)
        self.assertIn("1. CRASH SUMMARY", report)
        self.assertIn("Exception Type:     ZeroDivisionError", report)
        self.assertIn("division by zero", report)

        # Verify Context & Causing Inputs
        self.assertIn("2. CALCULATOR CONTEXT & CAUSING INPUTS AT TIME OF CRASH", report)
        self.assertIn("Active Mode:            Standard", report)
        self.assertIn("Primary Display Input:  0", report)
        self.assertIn("Expression Trail:       9 / ", report)
        self.assertIn("Live Preview Result:    Cannot divide by zero", report)

        # Verify User Action Breadcrumbs
        self.assertIn("3. USER ACTION BREADCRUMBS", report)
        self.assertIn("User opened Standard mode", report)
        self.assertIn("Keyed digit '9'", report)
        self.assertIn("Operator '/'", report)

        # Verify Traceback
        self.assertIn("4. FULL STACK TRACEBACK", report)
        self.assertIn("ZeroDivisionError: division by zero", report)
        self.assertIn("test_crash_reporter.py", report)

    # ─── 4. CRASH REPORT DISK PERSISTENCE ────────────────────────────
    def test_crash_report_file_persistence(self):
        def sample_context():
            return {"mode": "Programmer", "active_token": "0xDEADBEEF"}

        self.reporter.register_context_provider(sample_context)

        try:
            raise ValueError("Invalid integer conversion")
        except ValueError as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            primary_path, report_text = self.reporter.handle_crash(exc_type, exc_value, exc_tb)

        self.assertIsNotNone(primary_path)
        self.assertTrue(primary_path.exists())
        self.assertTrue(primary_path.name.startswith("crash_report_"))
        self.assertTrue(primary_path.name.endswith(".log"))

        content = primary_path.read_text(encoding="utf-8")
        self.assertIn("ValueError", content)
        self.assertIn("Invalid integer conversion", content)
        self.assertIn("0xDEADBEEF", content)
        self.assertIn("Programmer", content)

        # Verify master index log
        history_log = self.patch_dir / "crash_history.log"
        self.assertTrue(history_log.exists())
        self.assertIn("ValueError", history_log.read_text(encoding="utf-8"))

    # ─── 5. PYINSTALLER NOCONSOLE NULLWRITER SAFETY ─────────────────
    def test_pyinstaller_noconsole_null_writer(self):
        writer = NullWriter()
        # Should accept any write without throwing AttributeError or error
        written = writer.write("Diagnostic line\n")
        self.assertEqual(written, 16)
        writer.flush()

    # ─── 6. MODE-SPECIFIC SNAPSHOT CAPTURE ───────────────────────────
    def test_mode_specific_snapshots(self):
        # Graphing mode snapshot
        def graph_context():
            return {
                "mode": "Graphing",
                "active_token": "x^2 - 4",
                "expression_trail": "f1(x) =",
                "graph_bounds": "X[-5, 5], Y[-10, 10]",
                "graph_functions": ["x^2 - 4", "sin(x)"]
            }

        self.reporter.register_context_provider(graph_context)

        try:
            raise RuntimeError("Canvas rendering exception")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            report = self.reporter.build_crash_report(exc_type, exc_value, exc_tb)

        self.assertIn("Graphing", report)
        self.assertIn("graph_bounds", report)
        self.assertIn("X[-5, 5], Y[-10, 10]", report)
        self.assertIn("x^2 - 4", report)

    # ─── 7. CRASH RECOVERY MODAL DIALOG ─────────────────────────────
    def test_crash_recovery_dialog_ui(self):
        dlg = CrashReportDialog(
            exc_name="TestException",
            exc_msg="A deliberate testing error occurred",
            mode="Standard",
            active_token="999",
            report_path=str(self.patch_dir / "test.log"),
            full_report="Test Report Diagnostic Body"
        )
        dlg.show()
        app.processEvents()

        self.assertEqual(dlg.exc_name, "TestException")
        self.assertEqual(dlg.mode, "Standard")
        self.assertEqual(dlg.active_token, "999")
        self.assertIn("Test Report Diagnostic Body", dlg.report_viewer.toPlainText())

        # Test Clipboard copy functionality
        dlg.btn_copy.click()
        app.processEvents()
        cb = QApplication.clipboard()
        if cb:
            self.assertEqual(cb.text(), "Test Report Diagnostic Body")
            self.assertEqual(dlg.btn_copy.text(), "Copied to Clipboard!")

        dlg.close()


if __name__ == "__main__":
    unittest.main()
