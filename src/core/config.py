"""
Persistent Configuration and Settings Manager for Custom-Calculator.
Saves user preferences (active theme, active mode, window geometry, angle mode, etc.)
to data/config.json so settings persist across launches.
"""

import json
from pathlib import Path
from typing import Any, Dict


CURRENT_SCHEMA_VERSION = 2

DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": CURRENT_SCHEMA_VERSION,
    "theme_id": "dark_monokai",
    "mode": "Standard",
    "converter_category": "Length",
    "angle_mode": "DEG",
    "programmer_word_size": "QWORD",
    "programmer_radix": "DEC",
    "always_on_top": False,
    "history_open": False,
    "window_width": 360,
    "window_height": 560,
    "transparency_enabled": True,
    "window_transparency": 15,
}


class ConfigManager:
    _instances: Dict[str, "ConfigManager"] = {}

    def __new__(cls, config_path: str = "data/config.json"):
        resolved = str(Path(config_path).resolve())
        if resolved not in cls._instances:
            inst = super().__new__(cls)
            inst._initialized = False
            cls._instances[resolved] = inst
        return cls._instances[resolved]

    def __init__(self, config_path: str = "data/config.json"):
        if getattr(self, "_initialized", False):
            return
        self.config_path = Path(config_path)
        self.config = dict(DEFAULT_CONFIG)
        self.load()
        self._initialized = True

    def _migrate_schema(self, data: Dict[str, Any]) -> bool:
        """
        Backward-compatible schema migration engine.
        Assumes the user may upgrade from any older config schema version.
        Migrates legacy settings to current schema while preserving custom values.
        Returns True if changes were made and config should be saved.
        """
        modified = False

        # Migration from Schema v1 (or unversioned) -> v2:
        # 1. Migrate legacy blur toggles -> transparency_enabled
        if "transparency_enabled" not in data:
            if "blur_enabled" in data:
                data["transparency_enabled"] = bool(data.get("blur_enabled", True))
                modified = True
            elif "blur_effect" in data:
                data["transparency_enabled"] = bool(data.get("blur_effect", True))
                modified = True
            else:
                data["transparency_enabled"] = True

        # 2. Rescale legacy window_transparency to 0-25 range
        if "window_transparency" in data:
            val = data["window_transparency"]
            if isinstance(val, (int, float)):
                if val > 25:
                    if val > 50:
                        new_val = min(25, max(0, int(round((val / 100.0) * 25))))
                    else:
                        new_val = min(25, max(0, int(round((val / 50.0) * 25))))
                    data["window_transparency"] = new_val
                    modified = True
                elif val < 0:
                    data["window_transparency"] = 0
                    modified = True

        # 3. Clean up obsolete blur keys
        for legacy_key in ("blur_enabled", "blur_effect", "blur_intensity"):
            if legacy_key in data:
                data.pop(legacy_key, None)
                modified = True

        if data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            data["schema_version"] = CURRENT_SCHEMA_VERSION
            modified = True

        # 4. Fill in any missing default keys
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
                modified = True

        return modified

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        needs_save = self._migrate_schema(loaded)
                        self.config.update(loaded)
                        if needs_save:
                            self.save()
            except Exception:
                pass

    def reload(self):
        self.config = dict(DEFAULT_CONFIG)
        self.load()

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        # Backward-compatible fallbacks for legacy keys
        if key in ("blur_enabled", "blur_effect"):
            return self.config.get("transparency_enabled", default if default is not None else True)
        if key == "blur_intensity":
            return "none"
        return self.config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.config[key] = value
        if auto_save:
            self.save()

