"""
Windows Acrylic Blur & Mica Effect Integrator.
Enables native Desktop Window Manager (DWM) frosted glass blur effects on Windows 10 and 11.
Zero external dependencies; uses standard ctypes.
"""

import ctypes
from ctypes import c_int, byref, sizeof, c_void_p, Structure
import sys
from typing import Optional


class MARGINS(Structure):
    _fields_ = [
        ("cxLeftWidth", c_int),
        ("cxRightWidth", c_int),
        ("cyTopHeight", c_int),
        ("cyBottomHeight", c_int),
    ]


class ACCENT_POLICY(Structure):
    _fields_ = [
        ("AccentState", c_int),
        ("AccentFlags", c_int),
        ("GradientColor", c_int),
        ("AnimationId", c_int)
    ]


class WINCOMPATTRDATA(Structure):
    _fields_ = [
        ("Attribute", c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t)
    ]


# Win32 Constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic blur
DWMSBT_TABBEDWINDOW = 4     # Mica Alt

WCA_ACCENT_POLICY = 19
ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


def apply_window_blur(hwnd: int, dark_mode: bool = True, acrylic: bool = False) -> bool:
    """
    Applies native hardware glass blur effect (Windows 11 Mica/Acrylic or Windows 10 Acrylic).
    Extends DWM frame across client area so blur is visible beneath semi-transparent Qt background.
    """
    if sys.platform != "win32":
        return False

    try:
        ver = sys.getwindowsversion()
        dwm = ctypes.windll.dwmapi

        # ─── 1. EXTEND DWM FRAME INTO ENTIRE CLIENT AREA ──────────────
        margins = MARGINS(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(c_void_p(hwnd), byref(margins))

        # ─── 2. WINDOWS 11 (Build >= 22000) ──────────────────────────
        if ver.build >= 22000:
            # Dark / Light mode preference
            dark_flag = c_int(1 if dark_mode else 0)
            dwm.DwmSetWindowAttribute(c_void_p(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE, byref(dark_flag), sizeof(dark_flag))

            # Backdrop Type: 2 = Mica (default Windows 11 style), 3 = Acrylic blur
            # If acrylic is requested, try Acrylic (3) first; fallback to Mica (2)
            primary_type = DWMSBT_TRANSIENTWINDOW if acrylic else DWMSBT_MAINWINDOW
            fallback_type = DWMSBT_MAINWINDOW if acrylic else DWMSBT_TRANSIENTWINDOW

            backdrop = c_int(primary_type)
            res = dwm.DwmSetWindowAttribute(c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE, byref(backdrop), sizeof(backdrop))
            if res != 0:
                backdrop = c_int(fallback_type)
                res = dwm.DwmSetWindowAttribute(c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE, byref(backdrop), sizeof(backdrop))
            return res == 0

        # ─── 3. WINDOWS 10 (Build >= 17134) ──────────────────────────
        elif ver.build >= 17134:
            user32 = ctypes.windll.user32
            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.AccentFlags = 0x20 | 0x40 | 0x80 | 0x100

            # ABGR format gradient color tint
            accent.GradientColor = 0x99202020 if dark_mode else 0x99F5F5F5

            data = WINCOMPATTRDATA()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            data.SizeOfData = sizeof(accent)

            user32.SetWindowCompositionAttribute(c_void_p(hwnd), byref(data))
            return True

    except Exception:
        pass

    return False


def remove_window_blur(hwnd: int) -> bool:
    """Disables the DWM blur backdrop, reverting to solid window rendering."""
    if sys.platform != "win32":
        return False

    try:
        ver = sys.getwindowsversion()
        dwm = ctypes.windll.dwmapi

        if ver.build >= 22000:
            none_type = c_int(DWMSBT_NONE)
            dwm.DwmSetWindowAttribute(c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE, byref(none_type), sizeof(none_type))
            return True
        elif ver.build >= 17134:
            user32 = ctypes.windll.user32
            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_DISABLED
            data = WINCOMPATTRDATA()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            data.SizeOfData = sizeof(accent)
            user32.SetWindowCompositionAttribute(c_void_p(hwnd), byref(data))
            return True
    except Exception:
        pass

    return False
