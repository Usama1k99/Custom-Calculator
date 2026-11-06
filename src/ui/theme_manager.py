"""
Comprehensive Theme Manager for Custom-Calculator.
Supports 6 curated themes (3 Dark, 3 Light) + custom user theme editing.
Purple themes have been replaced with Monokai (Dark) and Soft Pink (Light).
Generates refined Windows Calculator-style Qt Style Sheets (QSS).
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


BUILTIN_THEMES = {
    # ─── DARK THEMES ─────────────────────────────────────────────────────────
    "dark_monokai": {
        "name": "Monokai Pro",
        "category": "dark",
        "bg_base": "#272822",
        "bg_surface": "#1E1F1C",
        "bg_card": "#383830",
        "bg_card_hover": "#49483E",
        "bg_card_active": "#57564B",
        "bg_op": "#3E3D32",
        "bg_op_hover": "#4E4D40",
        "bg_fn": "#323129",
        "bg_fn_hover": "#424137",
        "text_primary": "#F8F8F2",
        "text_secondary": "#A6A28C",
        "text_accent": "#FFFFFF",
        "accent_primary": "#F92672",  # Iconic Monokai Magenta / Pink
        "accent_hover": "#E0185F",
        "accent_cyan": "#66D9EF",
        "accent_green": "#A6E22E",
        "action_danger": "#FD971F",
        "border_subtle": "rgba(255, 255, 255, 0.08)",
        "shadow_key": "none"
    },
    "dark_obsidian": {
        "name": "Obsidian OLED",
        "category": "dark",
        "bg_base": "#000000",
        "bg_surface": "#0C0C0C",
        "bg_card": "#181818",
        "bg_card_hover": "#242424",
        "bg_card_active": "#303030",
        "bg_op": "#1E1E1E",
        "bg_op_hover": "#2B2B2B",
        "bg_fn": "#141414",
        "bg_fn_hover": "#202020",
        "text_primary": "#FFFFFF",
        "text_secondary": "#8A8A8A",
        "text_accent": "#000000",
        "accent_primary": "#10B981",  # Vivid Emerald
        "accent_hover": "#059669",
        "accent_cyan": "#06B6D4",
        "accent_green": "#10B981",
        "action_danger": "#EF4444",
        "border_subtle": "rgba(255, 255, 255, 0.07)",
        "shadow_key": "none"
    },
    "dark_graphite": {
        "name": "Charcoal Graphite",
        "category": "dark",
        "bg_base": "#1C1C1E",
        "bg_surface": "#252528",
        "bg_card": "#323236",
        "bg_card_hover": "#3F3F44",
        "bg_card_active": "#4C4C52",
        "bg_op": "#3A3A3F",
        "bg_op_hover": "#47474D",
        "bg_fn": "#2B2B2F",
        "bg_fn_hover": "#38383D",
        "text_primary": "#F5F5F7",
        "text_secondary": "#98989F",
        "text_accent": "#FFFFFF",
        "accent_primary": "#F97316",  # Bauhaus / Braun Safety Amber
        "accent_hover": "#EA580C",
        "accent_cyan": "#38BDF8",
        "accent_green": "#22C55E",
        "action_danger": "#EF4444",
        "border_subtle": "rgba(255, 255, 255, 0.06)",
        "shadow_key": "none"
    },

    # ─── LIGHT THEMES ────────────────────────────────────────────────────────
    "light_soft_pink": {
        "name": "Soft Rose Pink",
        "category": "light",
        "bg_base": "#FFF1F2",       # Rose 50
        "bg_surface": "#FFE4E6",    # Rose 100
        "bg_card": "#FFFFFF",       # Crisp card
        "bg_card_hover": "#FECDD3", # Rose 200
        "bg_card_active": "#FDA4AF",# Rose 300
        "bg_op": "#FEE2E2",
        "bg_op_hover": "#FECACA",
        "bg_fn": "#FFF5F5",
        "bg_fn_hover": "#FEE2E2",
        "text_primary": "#881337",   # Rose 900
        "text_secondary": "#9F1239", # Rose 800
        "text_accent": "#FFFFFF",
        "accent_primary": "#F43F5E", # Rose 500
        "accent_hover": "#E11D48",
        "accent_cyan": "#0284C7",
        "accent_green": "#059669",
        "action_danger": "#DC2626",
        "border_subtle": "rgba(244, 63, 94, 0.15)",
        "shadow_key": "none"
    },
    "light_snow": {
        "name": "Snow Minimalist",
        "category": "light",
        "bg_base": "#F3F3F3",
        "bg_surface": "#F9F9F9",
        "bg_card": "#FFFFFF",
        "bg_card_hover": "#E5E5E5",
        "bg_card_active": "#D8D8D8",
        "bg_op": "#F8F8F8",
        "bg_op_hover": "#EBEBEB",
        "bg_fn": "#EFEFEF",
        "bg_fn_hover": "#E2E2E2",
        "text_primary": "#1A1A1A",
        "text_secondary": "#5C5C5C",
        "text_accent": "#FFFFFF",
        "accent_primary": "#0067C0", # Windows Blue Accent
        "accent_hover": "#005A9E",
        "accent_cyan": "#0284C7",
        "accent_green": "#16A34A",
        "action_danger": "#D13438",
        "border_subtle": "rgba(0, 0, 0, 0.08)",
        "shadow_key": "none"
    },
    "light_parchment": {
        "name": "Warm Parchment",
        "category": "light",
        "bg_base": "#FAF8F5",
        "bg_surface": "#F2EEE7",
        "bg_card": "#FFFFFF",
        "bg_card_hover": "#EAE4D9",
        "bg_card_active": "#DFD8CB",
        "bg_op": "#F4EFE6",
        "bg_op_hover": "#EAE3D6",
        "bg_fn": "#ECE6DA",
        "bg_fn_hover": "#DFD7C8",
        "text_primary": "#292524",
        "text_secondary": "#78716C",
        "text_accent": "#FFFFFF",
        "accent_primary": "#C2410C", # Terracotta
        "accent_hover": "#9A3412",
        "accent_cyan": "#0891B2",
        "accent_green": "#15803D",
        "action_danger": "#B91C1C",
        "border_subtle": "rgba(41, 37, 36, 0.08)",
        "shadow_key": "none"
    }
}


class ThemeManager:
    def __init__(self, initial_theme_id: str = "dark_monokai"):
        self.themes = dict(BUILTIN_THEMES)
        self.custom_themes_file = Path("data") / "custom_themes.json"
        self.legacy_custom_file = Path("data") / "custom_theme.json"
        self._load_custom_themes()

        self.current_theme_id = initial_theme_id if initial_theme_id in self.themes else "dark_monokai"

    def _load_custom_themes(self):
        # 1. Load multi-theme repository if it exists
        if self.custom_themes_file.exists():
            try:
                with open(self.custom_themes_file, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    if isinstance(stored, dict):
                        for t_id, data in stored.items():
                            if isinstance(data, dict):
                                self.themes[t_id] = data
            except Exception:
                pass

        # 2. Migrate legacy single custom_theme.json if not already loaded
        if self.legacy_custom_file.exists():
            try:
                with open(self.legacy_custom_file, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
                    if isinstance(legacy, dict) and "custom" not in self.themes:
                        self.themes["custom"] = legacy
            except Exception:
                pass

    def get_custom_themes_map(self) -> Dict[str, Dict[str, Any]]:
        """Returns all user-created or imported custom themes."""
        return {k: v for k, v in self.themes.items() if k not in BUILTIN_THEMES and not k.endswith("_preview")}

    def get_next_custom_theme_name(self) -> str:
        """
        Inspects stored custom themes and returns an auto-incremented name like CustomTheme1, CustomTheme2, etc.
        """
        existing_nums = []
        pattern = re.compile(r"^CustomTheme(\d+)$", re.IGNORECASE)

        for theme in self.themes.values():
            if isinstance(theme, dict):
                name = theme.get("name", "")
                m = pattern.match(name.strip())
                if m:
                    existing_nums.append(int(m.group(1)))

        next_num = max(existing_nums, default=0) + 1
        return f"CustomTheme{next_num}"

    def save_new_custom_theme(self, theme_name: str, tokens: Dict[str, Any]) -> str:
        """
        Saves a newly customized theme with user-chosen name and persists to data/custom_themes.json.
        """
        self.custom_themes_file.parent.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_]", "_", theme_name.lower().strip())
        t_id = f"custom_{slug}_{int(time.time())}"

        data = dict(tokens)
        data["name"] = theme_name.strip() or self.get_next_custom_theme_name()
        if "category" not in data:
            data["category"] = "dark" if self._estimate_is_dark(data) else "light"

        # Register in memory
        self.themes[t_id] = data
        self.current_theme_id = t_id

        # Persist to disk
        self._persist_custom_themes()
        return t_id

    def save_custom_theme(self, theme_data: Dict[str, Any]):
        """Legacy helper for backward compatibility."""
        self.save_new_custom_theme(theme_data.get("name", "Custom Palette"), theme_data)

    def _persist_custom_themes(self):
        custom_map = self.get_custom_themes_map()
        try:
            self.custom_themes_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.custom_themes_file, "w", encoding="utf-8") as f:
                json.dump(custom_map, f, indent=2)
        except Exception:
            pass

    def export_theme(self, theme_id: str, file_path: str) -> bool:
        """Exports theme tokens as a portable JSON file."""
        data = self.themes.get(theme_id, self.current_tokens)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def import_theme_data(self, data: Any) -> Tuple[bool, str, str]:
        """
        Imports and validates theme dictionary data.
        Returns: (success: bool, theme_id: str, message_or_error: str)
        """
        try:
            if not isinstance(data, dict):
                return False, "", "Payload must be a valid JSON object."

            # Verify minimum color tokens exist
            essential_keys = ("bg_base", "bg_card", "accent_primary")
            if not any(k in data for k in essential_keys):
                return False, "", "Theme definition is missing essential color tokens (bg_base, bg_card, accent_primary)."

            # Fill missing tokens from baseline
            base = dict(BUILTIN_THEMES["dark_monokai"])
            for k, v in data.items():
                if isinstance(v, str):
                    base[k] = v

            imported_name = str(data.get("name", "")).strip()
            if not imported_name or any(t.get("name") == imported_name for t in self.themes.values()):
                imported_name = self.get_next_custom_theme_name()

            base["name"] = imported_name
            t_id = self.save_new_custom_theme(imported_name, base)
            return True, t_id, f"Theme '{imported_name}' imported successfully."
        except Exception as e:
            return False, "", f"Failed to parse theme data: {str(e)}"

    def import_theme(self, file_path: str) -> Tuple[bool, str, str]:
        """
        Imports and validates a JSON theme file. Handles missing tokens and invalid properties safely.
        Returns: (success: bool, theme_id: str, message_or_error: str)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self.import_theme_data(data)
        except Exception as e:
            return False, "", f"Failed to read theme file: {str(e)}"

    def _estimate_is_dark(self, tokens: Dict[str, Any]) -> bool:
        bg = tokens.get("bg_base", "#272822").lstrip("#")
        if len(bg) == 6:
            try:
                r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b)
                return luminance < 128
            except Exception:
                pass
        return True

    def set_theme(self, theme_id: str):
        if theme_id in self.themes:
            self.current_theme_id = theme_id

    @property
    def current_tokens(self) -> Dict[str, str]:
        return self.themes.get(self.current_theme_id, BUILTIN_THEMES["dark_monokai"])

    @property
    def current_category(self) -> str:
        tokens = self.themes.get(self.current_theme_id, BUILTIN_THEMES["dark_monokai"])
        return tokens.get("category", "dark")

    @property
    def is_dark(self) -> bool:
        return self.current_category == "dark"

    def _hex_to_rgba(self, hex_val: str, alpha: float = 0.82) -> str:
        clean = hex_val.strip().lstrip("#")
        if len(clean) == 6:
            try:
                r, g, b = int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)
                return f"rgba({r}, {g}, {b}, {alpha})"
            except Exception:
                pass
        return hex_val

    def generate_qss(self, blur_enabled: bool = True) -> str:
        """
        Builds the refined Windows Calculator-style stylesheet with theme-reactive SVGs.
        """
        t = self.current_tokens
        bg_window = self._hex_to_rgba(t['bg_base'], 0.65) if blur_enabled else t['bg_base']

        # Ensure dynamically tinted SVGs are written and absolute posix paths are used in QSS
        from src.ui.mode_icons import get_themed_svg_path
        sec_color = t.get("text_secondary", "#CCCCCC")
        chevron_down_path = get_themed_svg_path("ChevronDown", sec_color)
        chevron_up_path = get_themed_svg_path("ChevronUp", sec_color)
        date_picker_path = get_themed_svg_path("Date Calculation", sec_color)

        return f"""
        /* ─── ROOT WINDOW & CENTRAL CONTAINER ──────────────────────── */
        QMainWindow {{
            background: transparent;
        }}
        QWidget#CentralWidget {{
            background-color: {bg_window};
            border-radius: 8px;
            color: {t['text_primary']};
            font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif;
        }}

        /* ─── HEADER BAR (WINDOWS CALC STYLE) ──────────────────────── */
        QFrame#HeaderBar {{
            background-color: transparent;
            border: none;
            padding: 2px 4px;
        }}
        QPushButton#HamburgerBtn {{
            background-color: transparent;
            color: {t['text_primary']};
            border: none;
            border-radius: 4px;
            padding: 1px;
        }}
        QPushButton#HamburgerBtn:hover {{
            background-color: {t['bg_card_hover']};
        }}
        QLabel#ModeTitle {{
            color: {t['text_primary']};
            font-size: 19px;
            font-weight: 600;
            padding-left: 2px;
        }}
        QPushButton.iconHeaderBtn {{
            background-color: transparent;
            color: {t['text_secondary']};
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            padding: 4px 8px;
        }}
        QPushButton.iconHeaderBtn:hover {{
            background-color: {t['bg_card_hover']};
            color: {t['text_primary']};
        }}
        QPushButton.iconHeaderBtn:checked {{
            background-color: {t['bg_card_active']};
            color: {t['accent_primary']};
        }}

        /* ─── DISPLAY AREA (FLUSH & AIRY) ─────────────────────────── */
        QFrame#DisplayArea {{
            background-color: transparent;
            border: none;
            padding: 4px 16px 8px 16px;
        }}
        QLabel#ExpressionTrail {{
            color: {t['text_secondary']};
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            font-weight: 400;
            background: transparent;
        }}
        QLabel#GhostPreviewLine {{
            color: {t['text_secondary']};
            font-family: 'Segoe UI Variable Display', 'Segoe UI', monospace;
            font-size: 15px;
            font-weight: 400;
            opacity: 0.65;
            background: transparent;
        }}
        QLineEdit#PrimaryValueDisplay, QLabel#PrimaryValueDisplay {{
            color: {t['text_primary']};
            background-color: transparent;
            font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif;
            font-size: 44px;
            font-weight: 600;
            border: none;
            padding: 0;
            margin: 0;
            selection-background-color: {t['accent_primary']};
            selection-color: {t['text_accent']};
        }}
        QLineEdit#PrimaryValueDisplay[is_error="true"] {{
            color: {t['action_danger']};
            font-size: 30px;
            font-weight: 500;
        }}

        /* ─── MEMORY BAR (WINDOWS CALC RIBBON) ─────────────────────── */
        QFrame#MemoryBar {{
            background-color: transparent;
            border: none;
            padding: 0 8px 4px 8px;
        }}
        QPushButton.memBtn {{
            background-color: transparent;
            color: {t['text_secondary']};
            border: none;
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton.memBtn:hover {{
            background-color: {t['bg_card_hover']};
            color: {t['text_primary']};
        }}
        QPushButton.memBtn:disabled {{
            color: rgba(140, 140, 140, 0.4);
        }}

        /* ─── KEYPAD GRID (TIGHT 2PX SPACING & SUBTLE RADIUS) ──────── */
        QFrame#KeypadFrame {{
            background-color: transparent;
            border: none;
            padding: 0 4px 4px 4px;
        }}
        QPushButton.calcKey {{
            font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            border-radius: 4px;
            font-size: 15px;
            font-weight: 400;
            border: 1px solid {t['border_subtle']};
        }}
        QPushButton.numKey {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            font-size: 17px;
            font-weight: 600;
        }}
        QPushButton.numKey:hover {{
            background-color: {t['bg_card_hover']};
            border-color: rgba(255, 255, 255, 0.14);
        }}
        QPushButton.numKey:pressed {{
            background-color: {t['bg_card_active']};
        }}
        QPushButton.opKey {{
            background-color: {t['bg_op']};
            color: {t['text_primary']};
            font-size: 17px;
        }}
        QPushButton.opKey:hover {{
            background-color: {t['bg_op_hover']};
            border-color: rgba(255, 255, 255, 0.14);
        }}
        QPushButton.fnKey {{
            background-color: {t['bg_fn']};
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QPushButton.fnKey:hover {{
            background-color: {t['bg_fn_hover']};
        }}
        QPushButton.equalsKey {{
            background-color: {t['accent_primary']};
            color: {t['text_accent']};
            font-size: 18px;
            font-weight: bold;
            border: none;
        }}
        QPushButton.equalsKey:hover {{
            background-color: {t['accent_hover']};
        }}

        /* ─── MODERN WINDOWS 11 FLUENT SCROLLBAR ─────────────────── */
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            margin: 2px 0 2px 0;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: {t['border_subtle']};
            min-height: 28px;
            border-radius: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {t['text_secondary']};
        }}
        QScrollBar::handle:vertical:pressed {{
            background-color: {t['accent_primary']};
        }}
        QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
            height: 0px;
            width: 0px;
            background: transparent;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        /* ─── NAVIGATION SIDEBAR (WINDOWS CALC HAMBURGER DRAWER) ───── */
        QFrame#NavSidebar {{
            background-color: {t['bg_surface']};
            border-right: 1px solid {t['border_subtle']};
        }}
        QScrollArea#NavScrollArea,
        QWidget#NavScrollContainer,
        QScrollArea#NavScrollArea > QWidget > QWidget {{
            background: transparent;
            border: none;
        }}
        QLabel.sidebarCategory, QLabel[class="sidebarCategory"] {{
            color: {t['text_secondary']};
            font-size: 11px;
            font-weight: bold;
            padding: 10px 14px 4px 14px;
            letter-spacing: 0.5px;
        }}
        #NavSidebar QPushButton.navItem,
        #NavSidebar QPushButton[class="navItem"] {{
            text-align: left;
            background-color: transparent;
            color: {t['text_primary']};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 13px;
            margin: 1px 6px;
        }}
        #NavSidebar QPushButton.navItem:hover,
        #NavSidebar QPushButton[class="navItem"]:hover {{
            background-color: {t['bg_card_hover']};
            border: 1px solid {t['border_subtle']};
            color: {t['text_primary']};
        }}
        #NavSidebar QPushButton.navItem:pressed,
        #NavSidebar QPushButton[class="navItem"]:pressed {{
            background-color: {t['bg_card_active']};
        }}
        #NavSidebar QPushButton.navItemActive,
        #NavSidebar QPushButton[class="navItemActive"] {{
            text-align: left;
            background-color: transparent;
            color: {t['accent_primary']};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 8px 12px 8px 9px;
            font-size: 13px;
            font-weight: 600;
            margin: 1px 6px;
        }}
        #NavSidebar QPushButton.navItemActive:hover,
        #NavSidebar QPushButton[class="navItemActive"]:hover {{
            background-color: {t['bg_card_hover']};
            border: 1px solid transparent;
            color: {t['accent_primary']};
        }}
        #NavSidebar QPushButton.navItemActive:pressed,
        #NavSidebar QPushButton[class="navItemActive"]:pressed {{
            background-color: {t['bg_card_active']};
            border: 1px solid transparent;
            color: {t['accent_primary']};
        }}
        QFrame#SidebarSettingsDivider {{
            background-color: {t['border_subtle']};
            max-height: 1px;
            margin: 6px 12px;
            border: none;
        }}

        /* ─── CONVERTER VIEW ──────────────────────────────────────── */
        QFrame#ConverterView {{
            background-color: transparent;
            border: none;
            padding: 12px 18px;
        }}
        QComboBox.unitCombo {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 13px;
            font-weight: 500;
        }}
        QComboBox.unitCombo:hover {{
            background-color: {t['bg_card_hover']};
            border-color: rgba(255, 255, 255, 0.2);
        }}
        QComboBox.unitCombo:focus {{
            border: 1px solid {t['accent_primary']};
        }}
        QComboBox.unitCombo::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: none;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        QComboBox.unitCombo::down-arrow {{
            image: url({chevron_down_path});
            width: 12px;
            height: 12px;
        }}
        QComboBox.unitCombo QAbstractItemView {{
            background-color: {t['bg_surface']};
            color: {t['text_primary']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
            padding: 4px;
            selection-background-color: {t['accent_primary']};
            selection-color: {t['text_accent']};
            outline: none;
        }}
        QLineEdit.converterInput {{
            background-color: transparent;
            color: {t['text_primary']};
            border: none;
            border-bottom: 2px solid {t['accent_primary']};
            font-size: 32px;
            font-weight: 600;
            padding: 4px 0;
        }}

        /* ─── PROGRAMMER VIEW ─────────────────────────────────────── */
        QFrame#ProgrammerRadixFrame {{
            background-color: transparent;
            padding: 4px 16px;
        }}
        QLabel.radixLabel {{
            color: {t['text_secondary']};
            font-family: 'Consolas', monospace;
            font-size: 12px;
            font-weight: bold;
        }}
        QLabel.radixValue {{
            color: {t['text_primary']};
            font-family: 'Consolas', monospace;
            font-size: 14px;
        }}

        /* ─── SCIENTIFIC RIBBON & FLYOUT PANELS ───────────────────── */
        QFrame#ScientificHeaderBar {{
            background-color: transparent;
            padding: 2px 4px;
        }}
        QPushButton.sciRibbonBtn {{
            background-color: transparent;
            color: {t['text_primary']};
            border: 1px solid transparent;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            padding: 4px 10px;
        }}
        QPushButton.sciRibbonBtn:hover {{
            background-color: {t['bg_card_hover']};
            border-color: {t['border_subtle']};
        }}
        QPushButton.sciRibbonBtn:checked {{
            background-color: {t['bg_card_active']};
            color: {t['accent_primary']};
        }}
        QPushButton.sciDropdownBtn {{
            background-color: transparent;
            color: {t['text_primary']};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 8px;
            text-align: left;
        }}
        QPushButton.sciDropdownBtn:hover {{
            background-color: {t['bg_card_hover']};
            border-color: {t['border_subtle']};
        }}
        QPushButton.sciDropdownBtn:checked {{
            background-color: {t['bg_card_active']};
            color: {t['accent_primary']};
        }}
        QFrame#SciFlyoutPanel {{
            background-color: {t['bg_surface']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
            padding: 0px;
        }}
        QPushButton.sciFlyoutKey {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_subtle']};
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            padding: 1px 2px;
            min-height: 24px;
            max-height: 28px;
            min-width: 34px;
        }}
        QPushButton.sciFlyoutKey:hover {{
            background-color: {t['bg_card_hover']};
            border-color: {t['accent_primary']};
            color: {t['text_primary']};
        }}
        QPushButton.sciFlyoutKey:pressed {{
            background-color: {t['bg_card_active']};
            border-color: {t['accent_primary']};
        }}
        QPushButton.sciFlyoutKey:checked {{
            background-color: {t['accent_primary']};
            color: {t['text_accent']};
            border: 1px solid {t['accent_primary']};
            font-weight: 600;
        }}

        /* ─── DATE CALCULATION VIEW ───────────────────────────────── */
        QFrame#DateCalcView {{
            background-color: transparent;
            border: none;
        }}
        QLabel[class="dateSectionLabel"], QLabel.dateSectionLabel {{
            font-size: 12px;
            font-weight: 600;
            color: {t['text_secondary']};
            margin-bottom: 2px;
        }}
        QDateEdit[class="dateEdit"], QDateEdit.dateEdit,
        QSpinBox[class="dateSpinBox"], QSpinBox.dateSpinBox {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_subtle']};
            border-radius: 5px;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 500;
        }}
        QDateEdit[class="dateEdit"]:hover, QDateEdit.dateEdit:hover,
        QSpinBox[class="dateSpinBox"]:hover, QSpinBox.dateSpinBox:hover {{
            border-color: {t['accent_primary']};
        }}
        QDateEdit[class="dateEdit"]::drop-down, QDateEdit.dateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            border: none;
            width: 28px;
            background: transparent;
        }}
        QDateEdit[class="dateEdit"]::down-arrow, QDateEdit.dateEdit::down-arrow {{
            image: url({date_picker_path});
            width: 14px;
            height: 14px;
        }}
        QSpinBox[class="dateSpinBox"]::up-button, QSpinBox.dateSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid {t['border_subtle']};
            border-bottom: 1px solid {t['border_subtle']};
            background: transparent;
            border-top-right-radius: 5px;
        }}
        QSpinBox[class="dateSpinBox"]::up-button:hover, QSpinBox.dateSpinBox::up-button:hover {{
            background-color: {t['bg_card_hover']};
        }}
        QSpinBox[class="dateSpinBox"]::up-arrow, QSpinBox.dateSpinBox::up-arrow {{
            image: url({chevron_up_path});
            width: 10px;
            height: 10px;
        }}
        QSpinBox[class="dateSpinBox"]::down-button, QSpinBox.dateSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 22px;
            border-left: 1px solid {t['border_subtle']};
            background: transparent;
            border-bottom-right-radius: 5px;
        }}
        QSpinBox[class="dateSpinBox"]::down-button:hover, QSpinBox.dateSpinBox::down-button:hover {{
            background-color: {t['bg_card_hover']};
        }}
        QSpinBox[class="dateSpinBox"]::down-arrow, QSpinBox.dateSpinBox::down-arrow {{
            image: url({chevron_down_path});
            width: 10px;
            height: 10px;
        }}
        QDateEdit[class="dateEdit"] QCalendarWidget QWidget,
        QDateEdit.dateEdit QCalendarWidget QWidget {{
            background-color: {t['bg_surface']};
            color: {t['text_primary']};
        }}
        QLabel[class="dateHeadline"], QLabel.dateHeadline {{
            font-size: 22px;
            font-weight: 700;
            color: {t['text_primary']};
        }}
        QLabel[class="dateSubheadline"], QLabel.dateSubheadline {{
            font-size: 12px;
            color: {t['text_secondary']};
        }}
        QRadioButton, QRadioButton[class="dateRadio"], QRadioButton.dateRadio {{
            font-size: 13px;
            color: {t['text_primary']};
            spacing: 8px;
        }}
        QRadioButton::indicator, QRadioButton[class="dateRadio"]::indicator, QRadioButton.dateRadio::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 7px;
            border: 1px solid {t['border_subtle']};
            background: {t['bg_card']};
        }}
        QRadioButton::indicator:hover, QRadioButton[class="dateRadio"]::indicator:hover {{
            border-color: {t['accent_primary']};
        }}
        QRadioButton::indicator:checked, QRadioButton[class="dateRadio"]::indicator:checked {{
            background: {t['accent_primary']};
            border: 3px solid {t['bg_base']};
        }}

        /* ─── GRAPHING MODE VIEW ──────────────────────────────────── */
        QFrame#GraphingView {{
            background-color: transparent;
            border: none;
        }}
        QFrame#EquationDeck {{
            background-color: {t['bg_surface']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
        }}
        QFrame#KGFCard {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
        }}
        QSplitter#GraphSplitter::handle {{
            background-color: {t['border_subtle']};
            height: 2px;
        }}
        QSplitter#GraphSplitter::handle:hover {{
            background-color: {t['accent_primary']};
        }}
        QSlider::groove:horizontal {{
            border: none;
            height: 4px;
            background: {t['border_subtle']};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {t['accent_primary']};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {t['text_primary']};
            border: 1px solid {t['border_subtle']};
            width: 14px;
            height: 14px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {t['accent_primary']};
        }}

        /* ─── HISTORY DRAWER ──────────────────────────────────────── */
        QFrame#HistoryDrawer {{
            background-color: {t['bg_surface']};
            border-left: 1px solid {t['border_subtle']};
        }}
        QLabel.historyTitle, QLabel[class="historyTitle"] {{
            font-weight: bold;
            font-size: 11px;
            letter-spacing: 0.8px;
            color: {t['text_secondary']};
        }}
        QPushButton#HistoryCloseBtn {{
            background: transparent;
            color: {t['text_secondary']};
            border: none;
            font-size: 14px;
            border-radius: 4px;
        }}
        QPushButton#HistoryCloseBtn:hover {{
            background-color: {t['bg_card_hover']};
            color: {t['text_primary']};
        }}
        QLineEdit#HistorySearch {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
            padding: 6px 10px;
            color: {t['text_primary']};
            font-size: 12px;
        }}
        QLineEdit#HistorySearch:focus {{
            border-color: {t['accent_primary']};
        }}
        QScrollArea#HistoryScroll, QWidget#HistoryScrollContainer {{
            background: transparent;
            border: none;
        }}
        QLabel.historySessionHeader, QLabel[class="historySessionHeader"] {{
            font-size: 11px;
            font-weight: 600;
            color: {t['accent_primary']};
            padding: 8px 0 2px 2px;
            letter-spacing: 0.5px;
        }}
        QFrame.historyCard, QFrame[class="historyCard"] {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border_subtle']};
            border-radius: 6px;
            padding: 6px 8px;
        }}
        QFrame.historyCard:hover, QFrame[class="historyCard"]:hover {{
            background-color: {t['bg_card_hover']};
            border-color: {t['accent_primary']};
        }}
        QLabel.historyModePill, QLabel[class="historyModePill"] {{
            background-color: {t['bg_surface']};
            border: 1px solid {t['border_subtle']};
            border-radius: 3px;
            padding: 1px 5px;
            font-size: 9px;
            font-weight: bold;
            color: {t['text_secondary']};
        }}
        QLabel.historyTime, QLabel[class="historyTime"] {{
            font-size: 10px;
            color: {t['text_secondary']};
        }}
        QLabel.historyExpr, QLabel[class="historyExpr"] {{
            font-size: 11px;
            color: {t['text_secondary']};
        }}
        QLabel.historyRes, QLabel[class="historyRes"] {{
            font-size: 15px;
            font-weight: bold;
            color: {t['text_primary']};
        }}
        QLabel.historyEmpty, QLabel[class="historyEmpty"] {{
            color: {t['text_secondary']};
            font-size: 12px;
            padding: 20px 0;
        }}
        QPushButton.historyActionBtn, QPushButton[class="historyActionBtn"] {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border_subtle']};
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 500;
            color: {t['text_primary']};
        }}
        QPushButton.historyActionBtn:hover, QPushButton[class="historyActionBtn"]:hover {{
            background-color: {t['bg_card_hover']};
        }}
        QPushButton.historyActionBtn:disabled, QPushButton[class="historyActionBtn"]:disabled {{
            opacity: 0.35;
            color: {t['text_secondary']};
            background-color: transparent;
            border-color: {t['border_subtle']};
        }}
        QPushButton.historyClearBtn, QPushButton[class="historyClearBtn"] {{
            background-color: transparent;
            border: 1px solid {t['action_danger']};
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 11px;
            font-weight: 600;
            color: {t['action_danger']};
        }}
        QPushButton.historyClearBtn:hover, QPushButton[class="historyClearBtn"]:hover {{
            background-color: {t['action_danger']};
            color: #FFFFFF;
        }}
        QPushButton.historyClearBtn:disabled, QPushButton[class="historyClearBtn"]:disabled {{
            opacity: 0.35;
            color: {t['text_secondary']};
            border-color: {t['border_subtle']};
            background-color: transparent;
        }}
        """
