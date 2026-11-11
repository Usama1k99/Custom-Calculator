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
DWMWA_MICA_EFFECT = 1029
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic blur
DWMSBT_TABBEDWINDOW = 4     # Mica Alt

WCA_ACCENT_POLICY = 19
ACCENT_DISABLED = 0
ACCENT_ENABLE_GRADIENT = 1
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


def _hex_to_abgr(hex_str: Optional[str], alpha: int = 0x66) -> int:
    """Converts a hex color like '#272822' to a 32-bit integer in ABGR format."""
    if hex_str:
        clean = hex_str.strip().lstrip("#")
        if len(clean) == 6:
            try:
                r = int(clean[0:2], 16)
                g = int(clean[2:4], 16)
                b = int(clean[4:6], 16)
                return (alpha << 24) | (b << 16) | (g << 8) | r
            except Exception:
                pass
    return (alpha << 24) | 0x202020


def apply_window_blur(
    hwnd: int,
    dark_mode: bool = True,
    acrylic: bool = True,
    tint_hex: Optional[str] = None,
    blur_intensity: str = "medium",
    is_maximized: bool = False
) -> bool:
    """
    Applies native hardware glass blur effect across Windows 11 & Windows 10.
    1. Extends DWM frame across client area so backdrop is visible beneath translucent Qt canvas.
    2. Windows 11 22H2+ (Build >= 22621): Sets DWMWA_SYSTEMBACKDROP_TYPE (Acrylic / Mica).
    3. Windows 11 21H2 (Build 22000..22620): Sets DWMWA_MICA_EFFECT fallback.
    4. Windows 10 & 11: Applies AccentPolicy (ACCENT_ENABLE_ACRYLICBLURBEHIND) via SetWindowCompositionAttribute
       so real-time translucent frosted glass renders across client area.
    blur_intensity can be 'subtle', 'medium' (default, slightly reduced blurriness), or 'strong'.
    """
    if sys.platform != "win32":
        return False

    success = False
    try:
        ver = sys.getwindowsversion()
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32

        # ─── 1. EXTEND DWM FRAME INTO ENTIRE CLIENT AREA ──────────────
        margins = MARGINS(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(c_void_p(hwnd), byref(margins))

        # ─── 2. WINDOWS 11 DWM BACKDROP ───────────────────────────────
        backdrop_applied = False
        if ver.build >= 22000:
            dark_flag = c_int(1 if dark_mode else 0)
            dwm.DwmSetWindowAttribute(
                c_void_p(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(dark_flag), sizeof(dark_flag)
            )

            if ver.build >= 22621:
                # Windows 11 22H2+: DWMSBT_TRANSIENTWINDOW (3) for Acrylic, DWMSBT_MAINWINDOW (2) for Mica
                if blur_intensity == "subtle":
                    primary_type = DWMSBT_TABBEDWINDOW
                    fallback_type = DWMSBT_MAINWINDOW
                elif blur_intensity == "strong":
                    primary_type = DWMSBT_TRANSIENTWINDOW
                    fallback_type = DWMSBT_TABBEDWINDOW
                else:  # medium
                    primary_type = DWMSBT_TRANSIENTWINDOW
                    fallback_type = DWMSBT_MAINWINDOW

                backdrop = c_int(primary_type)
                res = dwm.DwmSetWindowAttribute(
                    c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE,
                    byref(backdrop), sizeof(backdrop)
                )
                if res != 0:
                    backdrop = c_int(fallback_type)
                    res = dwm.DwmSetWindowAttribute(
                        c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE,
                        byref(backdrop), sizeof(backdrop)
                    )
                if res == 0:
                    backdrop_applied = True
                    success = True
            elif ver.build >= 22000:
                # Windows 11 21H2 Mica fallback
                true_val = c_int(1)
                res = dwm.DwmSetWindowAttribute(
                    c_void_p(hwnd), DWMWA_MICA_EFFECT,
                    byref(true_val), sizeof(true_val)
                )
                if res == 0:
                    success = True

        # ─── 3. WINDOWS 10 & 11 ACCENT POLICY ACRYLIC BLUR ───────────
        # On Windows 11 Build >= 22621 where DWMWA_SYSTEMBACKDROP_TYPE succeeds, do NOT call legacy
        # SetWindowCompositionAttribute(ACCENT_ENABLE_ACRYLICBLURBEHIND), which attaches an un-scalable
        # DirectComposition visual layer that freezes/clips the client viewport upon maximization.
        # Only call it on Windows 10 (Build 17134..22000) or if backdrop failed.
        if ver.build >= 17134 and (not backdrop_applied or ver.build < 22621):
            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            # Decreased blurriness/tint: things behind window are ever so slightly more visible
            if blur_intensity == "strong":
                alpha = 0x66 if dark_mode else 0x77
            else:  # balanced medium with decreased blurriness
                alpha = 0x2A if dark_mode else 0x36

            # When maximized, omit drop shadow & borders to prevent bleeding onto secondary monitors
            if is_maximized:
                accent.AccentFlags = 0
            else:
                accent.AccentFlags = 0x20 | 0x40 | 0x80 | 0x100  # Standard drop shadow & border

            # Compute ABGR tint color
            if tint_hex:
                accent.GradientColor = _hex_to_abgr(tint_hex, alpha=alpha)
            else:
                accent.GradientColor = (alpha << 24) | (0x202020 if dark_mode else 0xF5F5F5)

            data = WINCOMPATTRDATA()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            data.SizeOfData = sizeof(accent)

            res = user32.SetWindowCompositionAttribute(c_void_p(hwnd), byref(data))
            if res:
                success = True

        # ─── 4. FORCE DWM IMMEDIATE FRAME RECOMPOSITION ───────────────
        # Forces DWM to immediately redraw composition buffer and sample desktop
        # backdrop without requiring a window move or minimize/maximize cycle.
        if user32.IsWindow(c_void_p(hwnd)):
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(
                c_void_p(hwnd),
                c_void_p(0), 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
            )
            RDW_INVALIDATE = 0x0001
            RDW_UPDATENOW = 0x0100
            RDW_ALLCHILDREN = 0x0080
            RDW_FRAME = 0x0400
            user32.RedrawWindow(
                c_void_p(hwnd),
                c_void_p(0),
                c_void_p(0),
                RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN | RDW_FRAME
            )

    except Exception:
        pass

    return success


def remove_window_blur(hwnd: int) -> bool:
    """Disables the DWM blur backdrop, reverting to solid window rendering."""
    if sys.platform != "win32":
        return False

    try:
        ver = sys.getwindowsversion()
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32

        if ver.build >= 22621:
            none_type = c_int(DWMSBT_NONE)
            dwm.DwmSetWindowAttribute(
                c_void_p(hwnd), DWMWA_SYSTEMBACKDROP_TYPE,
                byref(none_type), sizeof(none_type)
            )
        elif ver.build >= 22000:
            false_val = c_int(0)
            dwm.DwmSetWindowAttribute(
                c_void_p(hwnd), DWMWA_MICA_EFFECT,
                byref(false_val), sizeof(false_val)
            )

        if ver.build >= 17134:
            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_DISABLED
            data = WINCOMPATTRDATA()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
            data.SizeOfData = sizeof(accent)
            user32.SetWindowCompositionAttribute(c_void_p(hwnd), byref(data))

        # Force DWM to immediately update frame to opaque solid
        if user32.IsWindow(c_void_p(hwnd)):
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(
                c_void_p(hwnd),
                c_void_p(0), 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
            )
            RDW_INVALIDATE = 0x0001
            RDW_UPDATENOW = 0x0100
            RDW_ALLCHILDREN = 0x0080
            RDW_FRAME = 0x0400
            user32.RedrawWindow(
                c_void_p(hwnd),
                c_void_p(0),
                c_void_p(0),
                RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN | RDW_FRAME
            )

        return True
    except Exception:
        pass

    return False


def refresh_window_frame(hwnd: int) -> bool:
    """
    Refreshes DWM frame extension, triggers WM_NCCALCSIZE via SetWindowPos SWP_FRAMECHANGED,
    and forces immediate window frame recomposition across the entire client viewport.
    """
    if sys.platform != "win32":
        return False
    try:
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32
        if not user32.IsWindow(c_void_p(hwnd)):
            return False

        # 1. Re-extend frame into client area
        margins = MARGINS(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(c_void_p(hwnd), byref(margins))

        # 2. Trigger frame change
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(
            c_void_p(hwnd),
            c_void_p(0), 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        )

        # 3. Force window and children redraw
        RDW_INVALIDATE = 0x0001
        RDW_UPDATENOW = 0x0100
        RDW_ALLCHILDREN = 0x0080
        RDW_FRAME = 0x0400
        user32.RedrawWindow(
            c_void_p(hwnd),
            c_void_p(0),
            c_void_p(0),
            RDW_INVALIDATE | RDW_UPDATENOW | RDW_ALLCHILDREN | RDW_FRAME
        )
        return True
    except Exception:
        return False
