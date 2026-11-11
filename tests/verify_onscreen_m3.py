"""
tests/verify_onscreen_m3.py

On-Screen Visual & Layout Verification Harness for Milestone 3.
Launches the live Calculator application on-screen (visible, non-headless),
tests programmatic maximize, layout propagation, high-res visual capture,
and restore to normal geometry across Standard and Scientific modes.
"""

import sys
import os
import time
import ctypes
from pathlib import Path
from PIL import Image

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, QRect, QSize
from src.ui.main_window import MainWindow

SCREENSHOT_DIR = REPO_ROOT / "tests" / "screenshots_m3"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def verify_screenshot_pixels(image_path: Path, mode_name: str) -> dict:
    """Verifies that the screenshot contains active rendered UI content across all extremities."""
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # 1. Top-right pixel (Title Bar Close button area)
    tr_pixel = img.getpixel((w - 15, 17))
    # 2. Bottom-right pixel (Keypad '=' button or History Drawer)
    br_pixel = img.getpixel((w - 20, h - 20))
    # 3. Bottom-left pixel (Keypad bottom row button)
    bl_pixel = img.getpixel((20, h - 20))
    # 4. Center pixel (Display or Keypad grid)
    center_pixel = img.getpixel((w // 2, h // 2))

    # Assert that extremities have non-zero alpha and are rendered
    assert tr_pixel[3] > 0, f"Top-right pixel in {image_path.name} is fully transparent"
    assert br_pixel[3] > 0, f"Bottom-right pixel in {image_path.name} is fully transparent"
    assert bl_pixel[3] > 0, f"Bottom-left pixel in {image_path.name} is fully transparent"
    assert center_pixel[3] > 0, f"Center pixel in {image_path.name} is fully transparent"

    return {
        "dimensions": f"{w}x{h}",
        "tr_pixel": tr_pixel,
        "br_pixel": br_pixel,
        "bl_pixel": bl_pixel,
        "center_pixel": center_pixel,
    }


class OnScreenVerificationRunner:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.win = MainWindow(check_updates=False)
        self.hwnd = int(self.win.winId()) if sys.platform == "win32" else 0
        self.results = {}
        self.initial_geometry = None

    def start(self):
        # Launch visible, on-screen window
        self.win.show()
        self.win.activateWindow()
        self.win.raise_()
        # Allow 400ms for initial layout and window exposure
        QTimer.singleShot(400, self.step1_initial_normal)

    # --- STEP 1: INITIAL NORMAL STATE ---
    def step1_initial_normal(self):
        print("\n=== STEP 1: Verifying Initial Normal (Restored) State ===")
        w = self.win.width()
        h = self.win.height()
        self.initial_geometry = self.win.geometry()
        print(f"Normal Window Geometry: {self.initial_geometry} (size={w}x{h})")

        # Assertions
        assert not self.win.isMaximized(), "Window must not be maximized initially"
        if sys.platform == "win32":
            assert not ctypes.windll.user32.IsZoomed(ctypes.c_void_p(self.hwnd)), "Win32 IsZoomed must be False"
        assert self.win.root_container.size() == self.win.size(), "root_container must match window size"
        assert self.win.title_bar.width() == w, "title_bar must match window width"

        # Capture screenshot
        path1 = SCREENSHOT_DIR / "01_normal_initial.png"
        pix = self.win.grab()
        pix.save(str(path1))
        print(f"Captured: {path1} ({pix.width()}x{pix.height()})")
        self.results["01_normal_initial"] = verify_screenshot_pixels(path1, "Normal Initial")

        # Proceed to Step 2: Maximize
        QTimer.singleShot(500, self.step2_maximize_standard)

    # --- STEP 2: MAXIMIZE (STANDARD MODE) ---
    def step2_maximize_standard(self):
        print("\n=== STEP 2: Maximizing Window (Standard Mode) ===")
        # Maximize programmatically via the title bar button click
        self.win.title_bar.btn_maximize.click()
        # Wait 500ms for layout propagation and DWM animations
        QTimer.singleShot(500, self.verify_maximize_standard)

    def verify_maximize_standard(self):
        w = self.win.width()
        h = self.win.height()
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(self.hwnd))) if sys.platform == "win32" else True
        print(f"Maximized Window Geometry: {self.win.geometry()} (size={w}x{h}), IsZoomed={is_zoomed}, isMaximized={self.win.isMaximized()}")

        # Assertions: full expansion, no dead space
        assert self.win.isMaximized() or is_zoomed, "Window must be in maximized state"
        assert w >= 1024, f"Maximized width must be >= 1024, got {w}"
        assert h >= 700, f"Maximized height must be >= 700, got {h}"
        assert self.win.root_container.size() == self.win.size(), "root_container must expand to full window"
        assert self.win.title_bar.width() == w, "title_bar must stretch to full window width"
        assert self.win.title_bar.btn_close.geometry().right() >= w - 5, "Window close button must be anchored at the top-right screen edge"
        assert self.win.content_widget.geometry() == QRect(0, 34, w, h - 34), "content_widget must fill entire body under title bar"
        assert self.win.keypad.width() == self.win.center_container.width(), "keypad must expand edge-to-edge across center container"

        # Verify restore tooltip and icon state
        assert self.win.title_bar.btn_maximize.toolTip() == "Restore", "Tooltip must update to 'Restore'"

        # Capture screenshot
        path2 = SCREENSHOT_DIR / "02_standard_maximized.png"
        pix = self.win.grab()
        pix.save(str(path2))
        print(f"Captured: {path2} ({pix.width()}x{pix.height()})")
        self.results["02_standard_maximized"] = verify_screenshot_pixels(path2, "Standard Maximized")

        # Proceed to Step 3: Restore
        QTimer.singleShot(500, self.step3_restore_standard)

    # --- STEP 3: RESTORE (STANDARD MODE) ---
    def step3_restore_standard(self):
        print("\n=== STEP 3: Restoring Window Back to Normal ===")
        self.win.title_bar.btn_maximize.click()
        QTimer.singleShot(500, self.verify_restore_standard)

    def verify_restore_standard(self):
        w = self.win.width()
        h = self.win.height()
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(self.hwnd))) if sys.platform == "win32" else False
        print(f"Restored Window Geometry: {self.win.geometry()} (size={w}x{h}), IsZoomed={is_zoomed}, isMaximized={self.win.isMaximized()}")

        assert not self.win.isMaximized(), "Window must not be maximized after restore"
        assert not is_zoomed, "Win32 IsZoomed must be False"
        assert self.win.root_container.size() == self.win.size(), "root_container must match restored window size"
        assert self.win.title_bar.btn_maximize.toolTip() == "Maximize", "Tooltip must revert to 'Maximize'"

        # Capture screenshot
        path3 = SCREENSHOT_DIR / "03_standard_restored.png"
        pix = self.win.grab()
        pix.save(str(path3))
        print(f"Captured: {path3} ({pix.width()}x{pix.height()})")
        self.results["03_standard_restored"] = verify_screenshot_pixels(path3, "Standard Restored")

        # Proceed to Step 4: Defect Scenario
        QTimer.singleShot(500, self.step4_defect_scenario)

    # --- STEP 4: DEFECT SCENARIO (SCIENTIFIC + HISTORY DRAWER) ---
    def step4_defect_scenario(self):
        print("\n=== STEP 4: Defect Scenario (Scientific Mode + History Drawer Open) ===")
        self.win._switch_mode("Scientific", save_config=False)
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()

        QTimer.singleShot(400, self.maximize_defect_scenario)

    def maximize_defect_scenario(self):
        print("Maximizing in Scientific Mode with History Drawer open...")
        self.win.title_bar.btn_maximize.click()
        QTimer.singleShot(500, self.verify_defect_scenario_max)

    def verify_defect_scenario_max(self):
        w = self.win.width()
        h = self.win.height()
        print(f"Scientific Maximized Geometry: {self.win.geometry()} (size={w}x{h})")
        print(f"Center container: {self.win.center_container.geometry()}")
        print(f"History drawer: {self.win.history_drawer.geometry()}")
        print(f"Keypad: {self.win.keypad.geometry()}")

        # Assertions
        assert self.win.isMaximized(), "Window must be maximized"
        assert self.win.history_drawer.isVisible(), "History drawer must remain visible"
        # History drawer right edge must dock cleanly to the right edge of the window
        drawer_right = self.win.history_drawer.geometry().right()
        assert abs(drawer_right - (w - 1)) <= 2, f"History drawer must dock to right edge ({w-1}), got {drawer_right}"
        # Center container right edge must touch drawer left edge
        assert abs(self.win.center_container.geometry().right() - self.win.history_drawer.geometry().left()) <= 2
        # Title bar must span full width
        assert self.win.title_bar.width() == w
        assert self.win.title_bar.btn_close.geometry().right() >= w - 5

        # Capture screenshot
        path4 = SCREENSHOT_DIR / "04_scientific_history_maximized.png"
        pix = self.win.grab()
        pix.save(str(path4))
        print(f"Captured: {path4} ({pix.width()}x{pix.height()})")
        self.results["04_scientific_history_maximized"] = verify_screenshot_pixels(path4, "Scientific History Maximized")

        # Proceed to Step 5: Restore Scientific Mode
        QTimer.singleShot(500, self.step5_restore_scientific)

    # --- STEP 5: FINAL CLEAN RESTORE ---
    def step5_restore_scientific(self):
        print("\n=== STEP 5: Restoring Scientific Mode Back to Normal ===")
        self.win.title_bar.btn_maximize.click()
        QTimer.singleShot(500, self.finish_verification)

    def finish_verification(self):
        w = self.win.width()
        h = self.win.height()
        print(f"Scientific Restored Geometry: {self.win.geometry()} (size={w}x{h})")
        assert not self.win.isMaximized(), "Window must not be maximized"
        assert self.win.history_drawer.isVisible(), "History drawer must remain open"
        assert self.win.root_container.size() == self.win.size(), "root_container must match restored window size"

        # Capture screenshot
        path5 = SCREENSHOT_DIR / "05_scientific_history_restored.png"
        pix = self.win.grab()
        pix.save(str(path5))
        print(f"Captured: {path5} ({pix.width()}x{pix.height()})")
        self.results["05_scientific_history_restored"] = verify_screenshot_pixels(path5, "Scientific Restored")

        print("\n" + "=" * 60)
        print("=== ALL ON-SCREEN VISUAL & LAYOUT VERIFICATION CHECKS PASSED ===")
        print("=" * 60)
        for name, data in self.results.items():
            print(f" - {name}: {data['dimensions']}")

        self.win.close()
        self.app.quit()


if __name__ == "__main__":
    runner = OnScreenVerificationRunner()
    runner.start()
    sys.exit(runner.app.exec())
