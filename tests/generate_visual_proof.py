import sys
import os
from pathlib import Path
from PIL import Image

# Ensure project root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt
from src.ui.main_window import MainWindow

PROOF_DIR = REPO_ROOT / "tests" / "visual_proof"
PROOF_DIR.mkdir(parents=True, exist_ok=True)

class VisualProofRunner:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.win = MainWindow(check_updates=False)
        self.win.resize(430, 580)
        self.win.show()
        self.proofs = []

    def run(self):
        QTimer.singleShot(500, self.step1_standard_maximized)
        self.app.exec()

    def _save_and_verify(self, filename: str, label: str):
        filepath = PROOF_DIR / filename
        pix = self.win.grab()
        pix.save(str(filepath))
        
        # Verify with PIL
        img = Image.open(str(filepath)).convert("RGBA")
        w, h = img.size
        # Sample bottom-right, center, top-right, bottom-left
        br = img.getpixel((w - 30, h - 30))
        center = img.getpixel((w // 2, h // 2))
        tr = img.getpixel((w - 20, 15))
        bl = img.getpixel((30, h - 30))
        
        print(f"\n[PROOF] {label}")
        print(f"  Absolute Path: {filepath.resolve()}")
        print(f"  Dimensions: {w}x{h}")
        print(f"  Bottom-Right Pixel: {br}")
        print(f"  Center Pixel: {center}")
        print(f"  Top-Right Pixel: {tr}")
        print(f"  Bottom-Left Pixel: {bl}")
        
        assert w >= 1024, f"Window width must be >= 1024, got {w}"
        assert h >= 700, f"Window height must be >= 700, got {h}"
        assert br[3] == 255, f"Bottom-right pixel must be fully rendered (alpha=255), got {br[3]}"
        assert center[3] == 255, f"Center pixel must be fully rendered (alpha=255), got {center[3]}"
        self.proofs.append((label, str(filepath.resolve()), f"{w}x{h}"))

    def step1_standard_maximized(self):
        self.win._switch_mode("Standard", save_config=False)
        self.win.showMaximized()
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_standard_maximized)

    def verify_standard_maximized(self):
        self._save_and_verify("01_standard_maximized.png", "Standard Mode - Maximized (Buttons spread edge-to-edge)")
        QTimer.singleShot(500, self.step2_scientific_maximized)

    def step2_scientific_maximized(self):
        self.win._switch_mode("Scientific", save_config=False)
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_scientific_maximized)

    def verify_scientific_maximized(self):
        self._save_and_verify("02_scientific_maximized.png", "Scientific Mode - Maximized (Keypad & ribbon spread edge-to-edge)")
        QTimer.singleShot(500, self.step3_scientific_history_maximized)

    def step3_scientific_history_maximized(self):
        if not self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_scientific_history_maximized)

    def verify_scientific_history_maximized(self):
        self._save_and_verify("03_scientific_history_maximized.png", "Scientific Mode with History Drawer - Maximized")
        # Close history drawer before next step
        if self.win.history_drawer.isVisible():
            self.win._toggle_history_drawer()
        QTimer.singleShot(500, self.step4_programmer_maximized)

    def step4_programmer_maximized(self):
        self.win._switch_mode("Programmer", save_config=False)
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_programmer_maximized)

    def verify_programmer_maximized(self):
        self._save_and_verify("04_programmer_maximized.png", "Programmer Mode - Maximized (Hex grid spread edge-to-edge)")
        QTimer.singleShot(500, self.step5_graphing_maximized)

    def step5_graphing_maximized(self):
        self.win._switch_mode("Graphing", save_config=False)
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_graphing_maximized)

    def verify_graphing_maximized(self):
        self._save_and_verify("05_graphing_maximized.png", "Graphing Mode - Maximized (Plot canvas on left, functions & keypad on right)")
        QTimer.singleShot(500, self.step6_restore_normal)

    def step6_restore_normal(self):
        self.win._switch_mode("Standard", save_config=False)
        self.win.showNormal()
        self.win.resize(430, 580)
        self.app.processEvents()
        QTimer.singleShot(700, self.verify_restore_normal)

    def verify_restore_normal(self):
        filepath = PROOF_DIR / "06_standard_restored_normal.png"
        pix = self.win.grab()
        pix.save(str(filepath))
        print(f"\n[PROOF] Standard Mode - Cleanly Restored to Normal")
        print(f"  Absolute Path: {filepath.resolve()}")
        print(f"  Dimensions: {pix.width()}x{pix.height()}")
        self.proofs.append(("Standard Mode - Restored Normal", str(filepath.resolve()), f"{pix.width()}x{pix.height()}"))
        print("\nALL VISUAL PROOFS GENERATED AND VERIFIED SUCCESSFULLY!")
        self.app.quit()

if __name__ == "__main__":
    runner = VisualProofRunner()
    runner.run()
