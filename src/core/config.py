"""
Persistent Configuration and Settings Manager for Custom-Calculator.
Saves user preferences (active theme, active mode, window geometry, angle mode, etc.)
to data/config.json so settings persist across launches.
"""

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "theme_id": "dark_monokai",
    "mode": "Standard",
    "converter_category": "Length",
    "angle_mode": "DEG",
    "programmer_word_size": "QWORD",
    "programmer_radix": "DEC",
    "always_on_top": False,
    "history_open": False,
    "window_width": 360,
    "window_height": 560
}


class ConfigManager:
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = Path(config_path)
        self.config = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.config.update(loaded)
            except Exception:
                pass

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.config[key] = value
        if auto_save:
            self.save()

