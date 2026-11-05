"""
Native Win32 Frameless Window Integration for Windows 10 and 11.
Provides:
- Native all-edge and corner resizing (HTLEFT, HTRIGHT, HTTOP, HTBOTTOM, corners)
- Aero Snap (dragging title bar to screen edges to snap)
- Windows 11 Snap Layouts flyout on hovering maximize button (HTMAXBUTTON)
- Windows 11 rounded corners (DWMWA_WINDOW_CORNER_PREFERENCE = 33)
- Retains native window animations, minimize/restore, and taskbar integration
"""

import sys
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QAbstractNativeEventFilter, QPoint, Qt
from PyQt6.QtWidgets import QApplication, QWidget

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

    WM_ACTIVATE = 0x0006
    WM_KILLFOCUS = 0x0008
    WM_NCCALCSIZE = 0x0083
    WM_NCHITTEST = 0x0084
    WM_NCMOUSEMOVE = 0x00A0
    WM_NCLBUTTONDOWN = 0x00A1
    WM_NCLBUTTONUP = 0x00A2
    WM_NCLBUTTONDBLCLK = 0x00A3
    WM_CAPTURECHANGED = 0x0215
    WM_NCMOUSELEAVE = 0x02A2

    TME_LEAVE = 0x00000002
    TME_NONCLIENT = 0x00000010

    HTCLIENT = 1
    HTCAPTION = 2
    HTMINBUTTON = 8
    HTMAXBUTTON = 9
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17

    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_SYSMENU = 0x00080000

    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    MONITOR_DEFAULTTONEAREST = 2

    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [
            ("rgrc", RECT * 3),
            ("lppos", ctypes.c_void_p),
        ]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint),
            ("wParam", ctypes.c_size_t),
            ("lParam", ctypes.c_ssize_t),
            ("time", ctypes.c_ulong),
            ("pt", ctypes.c_long * 2),
        ]

    class TRACKMOUSEEVENT(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("hwndTrack", wintypes.HWND),
            ("dwHoverTime", wintypes.DWORD),
        ]

    class WinNativeEventFilter(QAbstractNativeEventFilter):
        """Native Windows event filter for frameless Aero Snap and Snap Layouts integration."""

        def __init__(self, window):
            super().__init__()
            self.win = window
            self.hwnd = None

        def set_hwnd(self, hwnd: int):
            self.hwnd = hwnd

        def _track_leave(self):
            if self.hwnd:
                tme = TRACKMOUSEEVENT()
                tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
                tme.dwFlags = TME_LEAVE | TME_NONCLIENT
                tme.hwndTrack = self.hwnd
                tme.dwHoverTime = 0
                user32.TrackMouseEvent(ctypes.byref(tme))

        def nativeEventFilter(self, eventType, message):
            if eventType == b"windows_generic_MSG" and self.hwnd and self.win:
                msg = MSG.from_address(int(message))
                if (msg.hwnd or 0) == self.hwnd:
                    if msg.message == WM_NCCALCSIZE:
                        if msg.wParam:
                            if user32.IsZoomed(ctypes.c_void_p(self.hwnd)):
                                monitor = user32.MonitorFromWindow(ctypes.c_void_p(self.hwnd), MONITOR_DEFAULTTONEAREST)
                                if monitor:
                                    mi = MONITORINFO()
                                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                                    if user32.GetMonitorInfoW(monitor, ctypes.byref(mi)):
                                        params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                                        params.rgrc[0] = mi.rcWork
                            return True, 0
                    elif msg.message == WM_NCHITTEST:
                        x = ctypes.c_short(msg.lParam & 0xFFFF).value
                        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                        res = self.win._handle_nchittest(x, y)
                        if res == HTMAXBUTTON:
                            if not getattr(self.win, "_btn_maximize_hovered", False):
                                self.win._btn_maximize_hovered = True
                                self.win._set_btn_maximize_hover(True)
                                self._track_leave()
                        else:
                            if getattr(self.win, "_btn_maximize_hovered", False):
                                self.win._btn_maximize_hovered = False
                                self.win._set_btn_maximize_hover(False)
                        if res is not None:
                            return True, res
                    elif msg.message == WM_NCMOUSEMOVE:
                        if msg.wParam == HTMAXBUTTON:
                            if not getattr(self.win, "_btn_maximize_hovered", False):
                                self.win._btn_maximize_hovered = True
                                self.win._set_btn_maximize_hover(True)
                                self._track_leave()
                        else:
                            if getattr(self.win, "_btn_maximize_hovered", False):
                                self.win._btn_maximize_hovered = False
                                self.win._set_btn_maximize_hover(False)
                    elif msg.message == WM_NCMOUSELEAVE:
                        self.win._btn_maximize_hovered = False
                        self.win._btn_maximize_pressed = False
                        self.win._set_btn_maximize_hover(False)
                        self.win._set_btn_maximize_pressed(False)
                    elif msg.message in (WM_KILLFOCUS, WM_CAPTURECHANGED, WM_ACTIVATE):
                        if getattr(self.win, "_btn_maximize_pressed", False) or getattr(self.win, "_btn_maximize_hovered", False):
                            self.win._btn_maximize_hovered = False
                            self.win._btn_maximize_pressed = False
                            self.win._set_btn_maximize_hover(False)
                            self.win._set_btn_maximize_pressed(False)
                    elif msg.message == WM_NCLBUTTONDOWN and msg.wParam == HTMAXBUTTON:
                        self.win._btn_maximize_pressed = True
                        self.win._set_btn_maximize_pressed(True)
                        return True, 0
                    elif msg.message == WM_NCLBUTTONUP:
                        was_pressed = getattr(self.win, "_btn_maximize_pressed", False)
                        self.win._btn_maximize_pressed = False
                        self.win._set_btn_maximize_pressed(False)
                        if was_pressed and msg.wParam == HTMAXBUTTON:
                            self.win._toggle_maximize()
                            return True, 0
                    elif msg.message == WM_NCLBUTTONDBLCLK and msg.wParam == HTCAPTION:
                        self.win._toggle_maximize()
                        return True, 0
            return False, 0


def is_windows_11() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return sys.getwindowsversion().build >= 22000
    except Exception:
        return False


def apply_native_window_frame(window: QWidget) -> None:
    """Enables Win32 native resizing borders, Aero Snap, and Windows 11 rounded corners."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())

        # Enable standard resizing frame, caption, minimize & maximize boxes
        style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE)
        user32.SetWindowLongW(
            ctypes.c_void_p(hwnd),
            GWL_STYLE,
            style | WS_THICKFRAME | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU
        )

        # Windows 11 rounded corners
        if is_windows_11():
            val = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(val), ctypes.sizeof(val)
            )

        # Install native Win32 event filter
        if not getattr(window, "_disable_win32_filter_for_testing", False):
            if not hasattr(window, "_native_event_filter") or window._native_event_filter is None:
                window._native_event_filter = WinNativeEventFilter(window)
                window._native_event_filter.set_hwnd(hwnd)
                app = QApplication.instance()
                if app:
                    app.installNativeEventFilter(window._native_event_filter)

        # Trigger WM_NCCALCSIZE
        user32.SetWindowPos(ctypes.c_void_p(hwnd), 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
    except Exception:
        pass


def apply_dialog_rounded_corners(dialog: QWidget) -> None:
    """Applies Windows 11 rounded corners to modal dialogs."""
    if sys.platform != "win32":
        return
    try:
        if is_windows_11():
            hwnd = int(dialog.winId())
            val = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(val), ctypes.sizeof(val)
            )
    except Exception:
        pass
