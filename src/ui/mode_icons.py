"""
Mode & Converter Vector Icons for Windows Calculator Navigation.
Provides exact SVG line-art icons and theme-reactive QIcon generation.
"""

from pathlib import Path
from typing import Dict
from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

MODE_SVGS: Dict[str, str] = {
    "Standard": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="3" width="16" height="18" rx="2" />
  <line x1="7" y1="7" x2="17" y2="7" />
  <circle cx="8" cy="11" r="1" fill="currentColor"/>
  <circle cx="12" cy="11" r="1" fill="currentColor"/>
  <circle cx="16" cy="11" r="1" fill="currentColor"/>
  <circle cx="8" cy="15" r="1" fill="currentColor"/>
  <circle cx="12" cy="15" r="1" fill="currentColor"/>
  <circle cx="16" cy="15" r="1" fill="currentColor"/>
</svg>""",

    "Scientific": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9 3h6M10 3v5l-5 9.5A2 2 0 0 0 6.7 21h10.6a2 2 0 0 0 1.7-3.5L14 8V3"/>
  <line x1="7.5" y1="16" x2="16.5" y2="16"/>
</svg>""",

    "Graphing": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <line x1="3" y1="20" x2="21" y2="20"/>
  <line x1="4" y1="3" x2="4" y2="21"/>
  <path d="M4 16l5-6 4 3 6-8"/>
</svg>""",

    "Programmer": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="7 8 3 12 7 16"/>
  <polyline points="17 8 21 12 17 16"/>
  <line x1="14" y1="4" x2="10" y2="20"/>
</svg>""",

    "Date Calculation": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="4" width="18" height="17" rx="2"/>
  <line x1="16" y1="2" x2="16" y2="6"/>
  <line x1="8" y1="2" x2="8" y2="6"/>
  <line x1="3" y1="10" x2="21" y2="10"/>
  <rect x="7" y="13" width="2" height="2" fill="currentColor"/>
  <rect x="11" y="13" width="2" height="2" fill="currentColor"/>
  <rect x="15" y="13" width="2" height="2" fill="currentColor"/>
</svg>""",

    "Currency": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="9" cy="12" r="6"/>
  <circle cx="15" cy="12" r="6"/>
</svg>""",

    "Volume": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 2l9 5v10l-9 5-9-5V7l9-5z"/>
  <path d="M12 12l9-5M12 12v10M12 12L3 7"/>
</svg>""",

    "Length": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="7" y="2" width="10" height="20" rx="1.5"/>
  <line x1="7" y1="6" x2="12" y2="6"/>
  <line x1="7" y1="10" x2="10" y2="10"/>
  <line x1="7" y1="14" x2="12" y2="14"/>
  <line x1="7" y1="18" x2="10" y2="18"/>
</svg>""",

    "Weight and Mass": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M8 8a4 4 0 0 1 8 0"/>
  <path d="M6 10h12l2 11H4l2-11z"/>
</svg>""",

    "Temperature": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
  <circle cx="11.5" cy="17.5" r="2" fill="currentColor"/>
</svg>""",

    "Energy": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 2c.6 2.4 2.2 4.4 4.2 6.4 2 2 3.1 4.1 3.1 6.6a7.3 7.3 0 1 1-14.6 0c0-3.1 2.1-6.1 4.3-8.5 0 2.5 1.5 4.5 3 4.5s2.2-3 2-9z"/>
  <path d="M12 18.5a2.5 2.5 0 0 0 2.5-2.5c0-1.6-1.1-2.8-2.5-4.5-1.4 1.7-2.5 2.9-2.5 4.5a2.5 2.5 0 0 0 2.5 2.5z"/>
</svg>""",

    "Area": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2"/>
  <line x1="3" y1="9" x2="21" y2="9"/>
  <line x1="3" y1="15" x2="21" y2="15"/>
  <line x1="9" y1="3" x2="9" y2="21"/>
  <line x1="15" y1="3" x2="15" y2="21"/>
</svg>""",

    "Speed": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 4a8 8 0 1 0 8 8"/>
  <line x1="12" y1="12" x2="17" y2="7"/>
  <circle cx="12" cy="12" r="2" fill="currentColor"/>
</svg>""",

    "Time": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="9"/>
  <polyline points="12 7 12 12 15 14"/>
</svg>""",

    "Power": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
</svg>""",

    "Data": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="3" width="16" height="18" rx="2"/>
  <circle cx="12" cy="10" r="4"/>
  <circle cx="12" cy="10" r="1.5" fill="currentColor"/>
  <line x1="8" y1="18" x2="16" y2="18"/>
</svg>""",

    "Pressure": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 14a8 8 0 1 1 16 0"/>
  <line x1="12" y1="14" x2="16" y2="9"/>
  <circle cx="12" cy="14" r="1.5" fill="currentColor"/>
</svg>""",

    "Angle": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 6 4 20 18 20"/>
  <path d="M4 14a6 6 0 0 1 6 6"/>
</svg>""",

    "Settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
</svg>""",

    "Backspace": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 4H8l-6 8 6 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/>
  <line x1="18" y1="9" x2="12" y2="15"/>
  <line x1="12" y1="9" x2="18" y2="15"/>
</svg>""",

    "Trigonometry": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="4,20 20,20 20,4"/>
  <polyline points="15,20 15,15 20,15"/>
</svg>""",

    "Function": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M16 4.5c-1.8 0-3.2 1.2-3.8 3.2L9.8 17.2c-.6 2-1.8 2.8-3.3 2.8"/>
  <line x1="7" y1="11" x2="16" y2="11"/>
</svg>""",

    "Hamburger": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
  <line x1="3.5" y1="6" x2="20.5" y2="6"/>
  <line x1="3.5" y1="12" x2="20.5" y2="12"/>
  <line x1="3.5" y1="18" x2="20.5" y2="18"/>
</svg>""",

    "Sun": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="4.5"/>
  <line x1="12" y1="2" x2="12" y2="4.5"/>
  <line x1="12" y1="19.5" x2="12" y2="22"/>
  <line x1="2" y1="12" x2="4.5" y2="12"/>
  <line x1="19.5" y1="12" x2="22" y2="12"/>
  <line x1="4.93" y1="4.93" x2="6.7" y2="6.7"/>
  <line x1="17.3" y1="17.3" x2="19.07" y2="19.07"/>
  <line x1="4.93" y1="19.07" x2="6.7" y2="17.3"/>
  <line x1="17.3" y1="6.7" x2="19.07" y2="4.93"/>
</svg>""",

    "Moon": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
</svg>""",

    "ChevronDown": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 8 10 12 14 8"/>
</svg>""",

    "ChevronUp": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 12 10 8 14 12"/>
</svg>""",

    "Close": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="18" y1="6" x2="6" y2="18"/>
  <line x1="6" y1="6" x2="18" y2="18"/>
</svg>""",

    "Eye": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>""",

    "EyeOff": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
  <line x1="1" y1="1" x2="23" y2="23"/>
</svg>""",

    "Trash": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/>
  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
</svg>"""
}


def get_themed_icon(icon_name: str, color_hex: str, size: int = 18) -> QIcon:
    """
    Renders an SVG vector icon dynamically tinted to the target theme color.
    """
    svg_raw = MODE_SVGS.get(icon_name)
    if not svg_raw:
        # Check Backspace or fallback
        svg_raw = MODE_SVGS.get("Backspace", "")

    # Substitute currentColor with the actual hex color
    colored_svg = svg_raw.replace("currentColor", color_hex)
    byte_arr = QByteArray(colored_svg.encode("utf-8"))

    renderer = QSvgRenderer(byte_arr)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def dump_all_svgs_to_disk(target_dir: str = "assets/icons/modes"):
    """
    Writes all mode SVGs to disk for asset persistence and packaging.
    """
    p = Path(target_dir)
    p.mkdir(parents=True, exist_ok=True)
    for name, content in MODE_SVGS.items():
        fn = name.lower().replace(" ", "_") + ".svg"
        (p / fn).write_text(content, encoding="utf-8")

