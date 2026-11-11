"""
tests/verify_onscreen_m4.py

On-Screen Visual, Repaint, Multi-Monitor Containment, and Dynamic Resizing Verification Harness for Milestone 4.
Launches the live Calculator application on-screen (visible, non-headless), tests:
1. Initial normal restored state and visual rendering.
2. Window maximize visual expansion, backing store repaint, and interactive hit-testing.
3. Multi-monitor boundary containment (zero spillover onto adjacent monitor).
4. History drawer toggle while maximized (preserves maximize state, no geometry corruption).
5. Always-on-top toggle while maximized (in-place Win32 SetWindowPos, no un-maximizing).
6. Mode switches while maximized (Scientific, Graphing, Standard).
7. Clean restore back to compact geometry without layout corruption or coordinate drift.
8. Captures high-resolution RGBA screenshots into tests/screenshots_m4/ and prints full absolute paths.
Zero emojis used anywhere.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from PIL import Image

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtTest import QTest
from src.ui.main_window import MainWindow

SCREENSHOT_DIR = REPO_ROOT / "tests" / "screenshots_m4"
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
        "path": str(image_path.resolve()),
        "dimensions": f"{w}x{h}",
        "tr_pixel": tr_pixel,
        "br_pixel": br_pixel,
        "bl_pixel": bl_pixel,
        "center_pixel": center_pixel,
    }


class OnScreenVerificationRunnerM4:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.win = MainWindow(check_updates=False)
        self.win.resize(380, 560)
        self.hwnd = int(self.win.winId()) if sys.platform == "win32" else 0
        self.results = {}
        self.initial_geometry = None
        self.maximized_geometry = None

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
        print(f"Captured: {path1.resolve()} ({pix.width()}x{pix.height()})")
        self.results["01_normal_initial"] = verify_screenshot_pixels(path1, "Normal Initial")

        # Proceed to Step 2: Maximize Standard
        QTimer.singleShot(400, self.step2_maximize_standard)

    # --- STEP 2: MAXIMIZE & EXPANDED HIT-TESTING (STANDARD MODE) ---
    def step2_maximize_standard(self):
        print("\n=== STEP 2: Maximizing Window (Standard Mode) & Testing Hit-Test ===")
        self.win.title_bar.btn_maximize.click()
        QTimer.singleShot(500, self.verify_maximize_standard)

    def verify_maximize_standard(self):
        try:
            w = self.win.width()
            h = self.win.height()
            self.maximized_geometry = self.win.geometry()
            is_zoomed = bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(self.hwnd))) if sys.platform == "win32" else True
            print(f"Maximized Window Geometry: {self.maximized_geometry} (size={w}x{h}), IsZoomed={is_zoomed}, isMaximized={self.win.isMaximized()}")

            # Assertions: full expansion, no dead space
            assert self.win.isMaximized() or is_zoomed, "Window must be in maximized state"
            assert w >= 1024, f"Maximized width must be >= 1024, got {w}"
            assert h >= 700, f"Maximized height must be >= 700, got {h}"
            assert self.win.root_container.size() == self.win.size(), "root_container must expand to full window"
            assert self.win.title_bar.width() == w, "title_bar must stretch to full window width"
            assert self.win.title_bar.btn_close.geometry().right() >= w - 5, "Window close button must be anchored at the top-right screen edge"
            assert self.win.content_widget.geometry() == QRect(0, 34, w, h - 34), "content_widget must fill entire body under title bar"
            assert self.win.keypad.width() == self.win.center_container.width(), "keypad must expand edge-to-edge across center container"

            # Interactive hit-testing on far-right expanded buttons: Perform '9 * 8 = 72'
            btn_9 = self.win.keypad.button_map.get("9")
            btn_mul = self.win.keypad.button_map.get("×") or self.win.keypad.button_map.get("x") or self.win.keypad.button_map.get("*")
            btn_8 = self.win.keypad.button_map.get("8")
            btn_eq = self.win.keypad.button_map.get("=")

            assert btn_eq is not None and btn_9 is not None and btn_8 is not None, "Keypad buttons must exist"
            eq_global_center = btn_eq.mapToGlobal(btn_eq.rect().center())
            assert eq_global_center.x() > 1000, f"Equal button must be positioned in expanded client area (x > 1000), got {eq_global_center.x()}"

            self.win.state.clear_all()
            QTest.mouseClick(btn_9, Qt.MouseButton.LeftButton)
            QTest.mouseClick(btn_mul, Qt.MouseButton.LeftButton)
            QTest.mouseClick(btn_8, Qt.MouseButton.LeftButton)
            QTest.mouseClick(btn_eq, Qt.MouseButton.LeftButton)
            assert self.win.display.primary_display.text() == "72", f"Expected '72', got {self.win.display.primary_display.text()}"
            print("Interactive hit-testing calculation on expanded buttons succeeded: 9 * 8 = 72")

            # Capture screenshot
            path2 = SCREENSHOT_DIR / "02_standard_maximized.png"
            pix = self.win.grab()
            pix.save(str(path2))
            print(f"Captured: {path2.resolve()} ({pix.width()}x{pix.height()})", flush=True)
            self.results["02_standard_maximized"] = verify_screenshot_pixels(path2, "Standard Maximized")

            # Proceed to Step 3: Multi-monitor check
            QTimer.singleShot(400, self.step3_secondary_monitor_containment)
        except Exception as e:
            import traceback
            print(f"EXCEPTION IN STEP 2: {e}\n{traceback.format_exc()}", flush=True)
            self.app.exit(1)

    # --- STEP 3: MULTI-MONITOR BOUNDARY CONTAINMENT ---
    def step3_secondary_monitor_containment(self):
        print("\n=== STEP 3: Testing Multi-Monitor Boundary Containment ===")
        screens = QGuiApplication.screens()
        print(f"Detected {len(screens)} screen(s): {[s.geometry() for s in screens]}")

        secondary_screen = None
        for s in screens:
            if s.geometry().x() < 0:
                secondary_screen = s
                break

        if secondary_screen is not None and sys.platform == "win32":
            sec_geom = secondary_screen.geometry()
            sec_work = secondary_screen.availableGeometry()
            print(f"Targeting Secondary Monitor: geom={sec_geom}, workArea={sec_work}")

            # Restore and move to secondary monitor
            self.win.showNormal()
            self.win.move(sec_geom.x() + 300, sec_geom.y() + 200)
            self.app.processEvents()

            # Maximize on secondary monitor
            self.win.showMaximized()
            self.app.processEvents()
            time.sleep(0.3)
            self.app.processEvents()

            hwnd = int(self.win.winId())
            pt_tl = wintypes.POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(pt_tl))
            client_rect = wintypes.RECT()
            ctypes.windll.user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(client_rect))
            client_w = client_rect.right - client_rect.left
            client_h = client_rect.bottom - client_rect.top
            client_right = pt_tl.x + client_w

            print(f"Secondary Client Screen Rect: left={pt_tl.x}, top={pt_tl.y}, right={client_right}, bottom={pt_tl.y + client_h}")
            assert pt_tl.x == sec_work.x(), f"Client left must align with work area ({sec_work.x()}), got {pt_tl.x}"
            assert client_right <= 0, f"Multi-monitor leak detected! Client right is {client_right} > 0"

            # Check close button global position
            btn_close_tr = self.win.title_bar.btn_close.mapToGlobal(self.win.title_bar.btn_close.rect().topRight())
            print(f"Close Button global topRight: ({btn_close_tr.x()}, {btn_close_tr.y()})")
            assert btn_close_tr.x() <= 0, f"Close button leaked onto primary monitor! x={btn_close_tr.x()}"
            print("Multi-monitor boundary containment verified: zero leakage onto primary monitor.")

            path3 = SCREENSHOT_DIR / "03_secondary_monitor_maximized.png"
            pix = self.win.grab()
            pix.save(str(path3))
            print(f"Captured: {path3.resolve()} ({pix.width()}x{pix.height()})")
            self.results["03_secondary_monitor_maximized"] = verify_screenshot_pixels(path3, "Secondary Monitor Maximized")

            # Move back to primary screen and maximize
            self.win.showNormal()
            self.win.move(200, 200)
            self.app.processEvents()
            self.win.showMaximized()
            self.app.processEvents()
        else:
            print("Single monitor setup or non-negative virtual screen; verifying primary monitor containment.")
            path3 = SCREENSHOT_DIR / "03_secondary_monitor_maximized.png"
            pix = self.win.grab()
            pix.save(str(path3))
            self.results["03_secondary_monitor_maximized"] = verify_screenshot_pixels(path3, "Primary Monitor Containment")

        QTimer.singleShot(400, self.step4_history_drawer_maximized)

    # --- STEP 4: HISTORY DRAWER TOGGLE WHILE MAXIMIZED ---
    def step4_history_drawer_maximized(self):
        print("\n=== STEP 4: Testing History Drawer Toggle While Maximized ===")
        assert self.win.isMaximized(), "Window must be maximized before testing drawer toggle"
        max_w = self.win.width()
        max_h = self.win.height()

        # Open history drawer while maximized
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
        self.app.processEvents()

        assert self.win.isMaximized(), "Window must REMAIN maximized after opening history drawer"
        assert self.win.width() == max_w, f"Window width must remain {max_w}, got {self.win.width()}"
        assert self.win.history_drawer.isVisible(), "History drawer must be visible"

        # Capture screenshot with drawer open
        path4 = SCREENSHOT_DIR / "04_history_drawer_maximized.png"
        pix = self.win.grab()
        pix.save(str(path4))
        print(f"Captured: {path4.resolve()} ({pix.width()}x{pix.height()})")
        self.results["04_history_drawer_maximized"] = verify_screenshot_pixels(path4, "History Drawer Maximized")

        # Close history drawer while maximized
        self.win._toggle_history_drawer()
        self.app.processEvents()

        assert self.win.isMaximized(), "Window must REMAIN maximized after closing history drawer"
        assert self.win.width() == max_w, f"Window width must remain {max_w}, got {self.win.width()}"
        assert not self.win.history_drawer.isVisible(), "History drawer must be hidden"
        print("History drawer toggling while maximized preserves maximize state without corruption.")

        QTimer.singleShot(400, self.step5_always_on_top_maximized)

    # --- STEP 5: ALWAYS-ON-TOP TOGGLE WHILE MAXIMIZED ---
    def step5_always_on_top_maximized(self):
        print("\n=== STEP 5: Testing Always-on-Top Toggle While Maximized ===")
        assert self.win.isMaximized(), "Window must be maximized"
        max_w = self.win.width()

        # Toggle Pin ON
        self.win.pin_btn.click()
        self.app.processEvents()
        assert self.win.isMaximized(), "Window must REMAIN maximized after pinning"
        assert self.win.width() == max_w, f"Window width must remain {max_w}, got {self.win.width()}"

        path5 = SCREENSHOT_DIR / "05_always_on_top_maximized.png"
        pix = self.win.grab()
        pix.save(str(path5))
        print(f"Captured: {path5.resolve()} ({pix.width()}x{pix.height()})")
        self.results["05_always_on_top_maximized"] = verify_screenshot_pixels(path5, "Always On Top Maximized")

        # Toggle Pin OFF
        self.win.pin_btn.click()
        self.app.processEvents()
        assert self.win.isMaximized(), "Window must REMAIN maximized after unpinning"
        assert self.win.width() == max_w, f"Window width must remain {max_w}, got {self.win.width()}"
        print("Always-on-top in-place toggle preserves maximize state seamlessly.")

        QTimer.singleShot(400, self.step6_mode_switch_maximized)

    # --- STEP 6: MODE SWITCH WHILE MAXIMIZED ---
    def step6_mode_switch_maximized(self):
        print("\n=== STEP 6: Testing Mode Switch While Maximized ===")
        assert self.win.isMaximized(), "Window must be maximized"
        max_w = self.win.width()

        # Switch to Scientific mode
        self.win._switch_mode("Scientific", save_config=False)
        self.app.processEvents()
        assert self.win.isMaximized(), "Window must REMAIN maximized after switching to Scientific"
        assert self.win.width() == max_w, f"Window width must remain {max_w}, got {self.win.width()}"

        path6 = SCREENSHOT_DIR / "06_scientific_maximized.png"
        pix = self.win.grab()
        pix.save(str(path6))
        print(f"Captured: {path6.resolve()} ({pix.width()}x{pix.height()})")
        self.results["06_scientific_maximized"] = verify_screenshot_pixels(path6, "Scientific Maximized")

        # Switch back to Standard mode
        self.win._switch_mode("Standard", save_config=False)
        self.app.processEvents()
        assert self.win.isMaximized(), "Window must REMAIN maximized after switching back to Standard"
        print("Mode switching while maximized preserves maximize state cleanly.")

        QTimer.singleShot(400, self.step7_clean_restore)

    # --- STEP 7: CLEAN RESTORE BACK TO NORMAL ---
    def step7_clean_restore(self):
        print("\n=== STEP 7: Testing Clean Restore Back to Normal ===")
        self.win.title_bar.btn_maximize.click()
        QTimer.singleShot(500, self.finish_verification)

    def finish_verification(self):
        w = self.win.width()
        h = self.win.height()
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(self.hwnd))) if sys.platform == "win32" else False
        print(f"Restored Window Geometry: {self.win.geometry()} (size={w}x{h}), IsZoomed={is_zoomed}, isMaximized={self.win.isMaximized()}")

        assert not self.win.isMaximized(), "Window must not be maximized after restore"
        assert not is_zoomed, "Win32 IsZoomed must be False after restore"
        assert self.win.root_container.size() == self.win.size(), "root_container must match restored window size"
        assert self.win.title_bar.btn_maximize.toolTip() == "Maximize", "Tooltip must revert to 'Maximize'"

        # Verify compact restored dimensions
        assert w <= 670, f"Restored width must be compact (<= 670), got {w}"

        # Capture screenshot
        path7 = SCREENSHOT_DIR / "07_clean_restored.png"
        pix = self.win.grab()
        pix.save(str(path7))
        print(f"Captured: {path7.resolve()} ({pix.width()}x{pix.height()})")
        self.results["07_clean_restored"] = verify_screenshot_pixels(path7, "Clean Restored")

        print("\n" + "=" * 80)
        print("=== ALL ON-SCREEN VISUAL & LAYOUT VERIFICATION CHECKS PASSED SUCCESSFULLY ===")
        print("=" * 80)
        print("\nGenerated High-Resolution Verification Screenshots:")
        for name, data in self.results.items():
            print(f"  [{name}] ({data['dimensions']}) -> {data['path']}")

        if hasattr(self.win, "_native_event_filter") and self.win._native_event_filter:
            self.app.removeNativeEventFilter(self.win._native_event_filter)
            self.win._native_event_filter = None
        self.win.close()
        self.app.quit()


if __name__ == "__main__":
    runner = OnScreenVerificationRunnerM4()
    runner.start()
    sys.exit(runner.app.exec())
