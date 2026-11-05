"""
Enterprise-Grade Crash Reporting & Diagnostic Logging Engine for Custom-Calculator (ApexCalc).
Designed specifically to work reliably in frozen PyInstaller EXEs (--noconsole/--windowed)
as well as standard development environments.

Key Features:
1. Global exception hooks for MainThread (sys.excepthook) and Worker Threads (threading.excepthook).
2. PyInstaller safety: prevents crashes caused by sys.stderr / sys.stdout being None in --noconsole mode.
3. Automatically writes structured, timestamped crash reports to:
   - Primary: %LOCALAPPDATA%/ApexCalculator/CrashReports
   - Secondary: <app_dir>/crash_reports (if writable)
4. Captures exact error type, error message, and full formatted stack traceback.
5. Captures real-time application context:
   - Active Mode (Standard, Scientific, Programmer, Graphing, Date Calculation, Converter)
   - Primary value display / active token
   - Expression trail / formula string
   - Live preview result
   - Mode-specific state (radix, bit size, equations, date inputs, converter units)
6. Circular Action Breadcrumb buffer (last 40 user interactions) tracking the exact sequence of clicks/inputs.
7. Interactive Crash Recovery Dialog with options to copy report, open crash folder, restart, or exit.
8. Native Win32 MessageBox fallback if Qt GUI is corrupted or unavailable. Zero emojis throughout.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import sys
import threading
import time
import traceback
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


@dataclass
class Breadcrumb:
    timestamp: float
    time_str: str
    category: str
    message: str
    data: Optional[Dict[str, Any]] = None

    def format_line(self) -> str:
        data_str = f" | {self.data}" if self.data else ""
        return f"[{self.time_str}] [{self.category.upper()}] {self.message}{data_str}"


class NullWriter:
    """Safe dummy stream to prevent AttributeError when sys.stderr/sys.stdout is None in PyInstaller --noconsole."""
    def write(self, s: Any) -> int:
        return len(str(s))

    def flush(self) -> None:
        pass


class CrashReporter:
    """
    Singleton Crash Reporting engine. Collects breadcrumbs, queries context providers,
    formats diagnostics, writes reports to disk, and triggers user-facing crash notifications.
    """
    _instance: Optional["CrashReporter"] = None

    def __init__(self):
        self.breadcrumbs: Deque[Breadcrumb] = deque(maxlen=40)
        self.context_providers: List[Callable[[], Dict[str, Any]]] = []
        self._installed = False
        self._is_handling_crash = False
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "CrashReporter":
        if cls._instance is None:
            cls._instance = CrashReporter()
        return cls._instance

    def record_breadcrumb(self, category: str, message: str, **kwargs) -> None:
        """Records an action or state transition into the rolling ring buffer."""
        now = time.time()
        time_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        crumb = Breadcrumb(
            timestamp=now,
            time_str=time_str,
            category=category,
            message=message,
            data=kwargs if kwargs else None
        )
        with self._lock:
            self.breadcrumbs.append(crumb)

    def register_context_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        """Registers a callback that returns contextual application state at crash time."""
        if provider not in self.context_providers:
            self.context_providers.append(provider)

    def unregister_context_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        if provider in self.context_providers:
            self.context_providers.remove(provider)

    def get_crash_directories(self) -> List[Path]:
        """
        Returns candidate crash report directories in priority order:
        1. %LOCALAPPDATA%/ApexCalculator/CrashReports
        2. %APPDATA%/ApexCalculator/CrashReports
        3. Local <app_dir>/crash_reports
        """
        dirs: List[Path] = []

        # 1. Windows Local AppData
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            dirs.append(Path(local_appdata) / "ApexCalculator" / "CrashReports")

        # 2. Windows Roaming AppData
        roaming_appdata = os.environ.get("APPDATA")
        if roaming_appdata:
            dirs.append(Path(roaming_appdata) / "ApexCalculator" / "CrashReports")

        # 3. User Home fallback
        dirs.append(Path.home() / ".apexcalculator" / "crash_reports")

        # 4. Local application directory
        try:
            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).resolve().parent
            else:
                exe_dir = Path(__file__).resolve().parent.parent.parent
            dirs.append(exe_dir / "crash_reports")
        except Exception:
            pass

        return dirs

    def _collect_application_context(self) -> Dict[str, Any]:
        """Queries all registered providers to build an exhaustive state dictionary."""
        combined_context: Dict[str, Any] = {}
        for provider in list(self.context_providers):
            try:
                data = provider()
                if isinstance(data, dict):
                    combined_context.update(data)
            except Exception as e:
                combined_context[f"provider_error_{id(provider)}"] = str(e)
        return combined_context

    def build_crash_report(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Any,
        thread: Optional[threading.Thread] = None
    ) -> str:
        """
        Builds a comprehensive, human-readable text crash report
        documenting the error, full traceback, mode, inputs, and action history.
        """
        now_local = datetime.now()
        now_utc = datetime.now(timezone.utc)
        thread_name = thread.name if thread else threading.current_thread().name
        thread_id = thread.ident if thread else threading.current_thread().ident

        # Version & Metadata
        try:
            from src.version import APP_NAME, APP_VERSION, BUILD_COMMIT, GITHUB_REPO
        except Exception:
            APP_NAME, APP_VERSION, BUILD_COMMIT, GITHUB_REPO = "Custom-Calculator", "Unknown", "Unknown", ""

        is_frozen = getattr(sys, "frozen", False)
        exe_path = sys.executable

        # Application state snapshot
        app_context = self._collect_application_context()
        active_mode = app_context.get("mode", "Unknown")
        active_token = app_context.get("active_token", "N/A")
        expression_trail = app_context.get("expression_trail", "N/A")
        live_preview = app_context.get("live_preview", "N/A")

        # Format Traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        formatted_tb = "".join(tb_lines).rstrip()

        # Format Breadcrumbs
        with self._lock:
            crumbs_snapshot = list(self.breadcrumbs)

        if crumbs_snapshot:
            crumb_text = "\n".join(f"  {c.format_line()}" for c in crumbs_snapshot)
        else:
            crumb_text = "  (No user actions recorded prior to crash)"

        # Mode Specific Details
        mode_specific_lines = []
        for k, v in app_context.items():
            if k not in ("mode", "active_token", "expression_trail", "live_preview", "is_evaluated", "has_error", "memory"):
                mode_specific_lines.append(f"  {k:<24}: {v}")
        mode_specific_text = "\n".join(mode_specific_lines) if mode_specific_lines else "  None"

        report = f"""======================================================================
APEX CALCULATOR ({APP_NAME}) CRASH REPORT
======================================================================
Timestamp (Local):  {now_local.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}
Timestamp (UTC):    {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}
App Version:        v{APP_VERSION} (Commit: {BUILD_COMMIT})
Executable:         {exe_path}
Execution Mode:     {'Frozen Standalone Binary (PyInstaller)' if is_frozen else 'Python Source'}
Operating System:   {platform.platform()} ({platform.version()}, {platform.architecture()[0]})
Python Runtime:     {platform.python_version()} ({platform.python_implementation()})
Repository:         https://github.com/{GITHUB_REPO}

----------------------------------------------------------------------
1. CRASH SUMMARY
----------------------------------------------------------------------
Exception Type:     {exc_type.__name__ if hasattr(exc_type, '__name__') else str(exc_type)}
Exception Message:  {str(exc_value) or '(No message)'}
Triggering Thread:  {thread_name} (ID: {thread_id})
Active Mode:        {active_mode}

----------------------------------------------------------------------
2. CALCULATOR CONTEXT & CAUSING INPUTS AT TIME OF CRASH
----------------------------------------------------------------------
Active Mode:            {active_mode}
Primary Display Input:  {active_token}
Expression Trail:       {expression_trail}
Live Preview Result:    {live_preview}
Evaluated State:        {app_context.get('is_evaluated', 'N/A')}
Error State:            {app_context.get('has_error', 'N/A')}
Memory Register:        {app_context.get('memory', 'N/A')}
Angle Mode:             {app_context.get('angle_mode', 'N/A')}

Mode-Specific State:
{mode_specific_text}

----------------------------------------------------------------------
3. USER ACTION BREADCRUMBS (CHRONOLOGICAL PRE-CRASH ACTIONS)
----------------------------------------------------------------------
{crumb_text}

----------------------------------------------------------------------
4. FULL STACK TRACEBACK
----------------------------------------------------------------------
{formatted_tb}

======================================================================
END OF CRASH REPORT
======================================================================
"""
        return report

    def save_crash_report(self, report_text: str, exc_type_name: str) -> Tuple[Optional[Path], List[Path]]:
        """
        Persists the crash report to disk across candidate directories.
        Returns the primary saved path and a list of all successfully written paths.
        """
        timestamp_slug = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_exc_name = "".join(c if c.isalnum() else "_" for c in exc_type_name)
        file_name = f"crash_report_{timestamp_slug}_{safe_exc_name}.log"

        saved_paths: List[Path] = []
        candidate_dirs = self.get_crash_directories()

        for directory in candidate_dirs:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                target_file = directory / file_name
                target_file.write_text(report_text, encoding="utf-8")
                saved_paths.append(target_file)

                # Append to master crash index
                index_file = directory / "crash_history.log"
                summary_line = f"[{timestamp_slug}] {exc_type_name} in mode -> {file_name}\n"
                try:
                    with open(index_file, "a", encoding="utf-8") as f:
                        f.write(summary_line)
                except Exception:
                    pass
            except Exception:
                continue

        primary_path = saved_paths[0] if saved_paths else None
        return primary_path, saved_paths

    def handle_crash(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Any,
        thread: Optional[threading.Thread] = None
    ) -> Tuple[Optional[Path], str]:
        """
        Builds the crash report, records final breadcrumb, saves to disk,
        and returns the primary report file path along with the full report text.
        """
        exc_name = exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type)
        self.record_breadcrumb("Crash", f"Fatal Unhandled Exception: {exc_name} -> {str(exc_value)}")

        report_text = self.build_crash_report(exc_type, exc_value, exc_tb, thread=thread)
        primary_path, all_paths = self.save_crash_report(report_text, exc_name)

        return primary_path, report_text

    def show_crash_dialog(
        self,
        exc_type: type,
        exc_value: BaseException,
        report_path: Optional[Path],
        report_text: str
    ) -> None:
        """
        Presents the user with a recovery dialog showing where the report is stored,
        with buttons to copy details, open folder, restart, or close.
        Falls back to native Win32 MessageBox if Qt is unavailable or corrupted.
        """
        app_context = self._collect_application_context()
        mode_name = app_context.get("mode", "Unknown")
        active_token = app_context.get("active_token", "N/A")
        exc_name = exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type)
        report_file_str = str(report_path.resolve()) if report_path else "Could not write to disk"

        # Attempt 1: PyQt6 Rich Modal Dialog
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                from src.ui.crash_dialog import CrashReportDialog
                dlg = CrashReportDialog(
                    exc_name=exc_name,
                    exc_msg=str(exc_value),
                    mode=mode_name,
                    active_token=active_token,
                    report_path=report_file_str,
                    full_report=report_text
                )
                dlg.exec()
                return
        except Exception:
            pass

        # Attempt 2: Native Win32 MessageBox fallback (100% reliable even if Qt crashes)
        try:
            if platform.system() == "Windows":
                import ctypes
                msg = (
                    f"Apex Calculator has encountered an unexpected error.\n\n"
                    f"Error: {exc_name}: {exc_value}\n"
                    f"Mode: {mode_name}\n"
                    f"Input: {active_token}\n\n"
                    f"A detailed crash report has been saved to:\n"
                    f"{report_file_str}\n\n"
                    f"The application will now close."
                )
                # MB_OK | MB_ICONERROR | MB_TOPMOST
                ctypes.windll.user32.MessageBoxW(0, msg, "Apex Calculator - Error", 0x00000010 | 0x00040000)
                return
        except Exception:
            pass

        # Attempt 3: Terminal stderr fallback (development)
        if sys.stderr:
            try:
                sys.stderr.write(f"\nCRASH OCCURRED:\n{report_text}\n")
                sys.stderr.flush()
            except Exception:
                pass

    def install_crash_handler(self) -> None:
        """
        Installs global unhandled exception hooks for the main thread and all background threads.
        Safeguards sys.stdout and sys.stderr for frozen --noconsole execution.
        """
        if self._installed:
            return

        # 1. Protect against None stdout/stderr in PyInstaller --noconsole
        if sys.stdout is None:
            sys.stdout = NullWriter()
        if sys.stderr is None:
            sys.stderr = NullWriter()

        # 2. Main Thread excepthook
        def global_excepthook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return

            # Prevent recursion
            if self._is_handling_crash:
                return
            self._is_handling_crash = True

            try:
                report_path, report_text = self.handle_crash(exc_type, exc_value, exc_tb)
                self.show_crash_dialog(exc_type, exc_value, report_path, report_text)
            finally:
                self._is_handling_crash = False
                sys.exit(1)

        sys.excepthook = global_excepthook

        # 3. Secondary/Worker Thread excepthook (Python 3.8+)
        def thread_excepthook(args):
            if issubclass(args.exc_type, KeyboardInterrupt):
                return

            if self._is_handling_crash:
                return
            self._is_handling_crash = True

            try:
                report_path, report_text = self.handle_crash(
                    args.exc_type, args.exc_value, args.exc_tb, thread=args.thread
                )
                self.show_crash_dialog(args.exc_type, args.exc_value, report_path, report_text)
            finally:
                self._is_handling_crash = False
                sys.exit(1)

        if hasattr(threading, "excepthook"):
            threading.excepthook = thread_excepthook

        self._installed = True


# Global convenience helpers
_reporter = CrashReporter.get_instance()
record_breadcrumb = _reporter.record_breadcrumb
register_context_provider = _reporter.register_context_provider
unregister_context_provider = _reporter.unregister_context_provider
install_crash_handler = _reporter.install_crash_handler
get_crash_reporter = CrashReporter.get_instance

