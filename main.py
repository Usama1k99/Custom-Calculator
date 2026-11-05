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

    # Enable High DPI attribute
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Custom-Calculator")
    app.setOrganizationName("Custom-Calculator")

    # Set App-Level Icon
    icon_path = Path("assets") / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

