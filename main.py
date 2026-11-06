"""
Custom-Calculator (ApexCalc) Entry Point.
Initializes High-DPI support, application lifecycle, and main UI.
"""

from pathlib import Path
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from src.core.crash_reporter import install_crash_handler
from src.ui.main_window import MainWindow


def main():
    # Install robust crash logging and PyInstaller safe stream handler immediately
    install_crash_handler()

    # Set Windows AppUserModelID so taskbar groups and shows the native app icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Usama1k99.CustomCalculator.App.0.2.0")
        except Exception:
            pass

    # Enable High DPI attribute
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Custom-Calculator")
    app.setOrganizationName("Custom-Calculator")

    # Set App-Level Icon (multi-resolution ICO required for Windows Taskbar)
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_path = base_dir / "assets" / "icons" / "app_icon.ico"
    if not icon_path.exists():
        icon_path = Path("assets") / "icons" / "app_icon.ico"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

