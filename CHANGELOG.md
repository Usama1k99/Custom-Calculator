# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-11-06 (Alpha Build)

### Added
* Native Windows Acrylic / Mica blur behind effect (`src/ui/window_effects.py`, `src/ui/theme_manager.py`, `src/ui/main_window.py`, `src/ui/theme_dialog.py`):
  * DWM composition integration (`DwmExtendFrameIntoClientArea`, `DWMWA_SYSTEMBACKDROP_TYPE = 38` Acrylic / Mica, `ACCENT_ENABLE_ACRYLICBLURBEHIND`).
  * Acrylic window frame extension without forcing `WS_EX_LAYERED`, preserving Windows 11 Snap Layouts.
  * Dynamically reactive semi-transparent window base styling (`rgba(..., 0.82)`) with user toggle in Theme Settings.
* Complete Interactive Graphing Mode (`src/core/graph_engine.py`, `src/ui/graph_canvas.py`, `src/ui/graphing_view.py`):
  * Natural mathematical notation parser with implicit multiplication (`2x`, `3sin(x)`, `(x+1)(x-1)`, `5pi`).
  * High-performance antialiased Cartesian coordinate canvas with dynamic zoom-adaptive intervals.
  * Smooth mouse drag panning & wheel zooming centered on cursor.
  * Asymptote and discontinuity protection (e.g. `tan(x)`, `1/x`) preventing spurious vertical lines.
  * Multi-function equation deck supporting up to 6 simultaneous curves with distinct color palettes (`CURVE_PALETTE`).
  * Dynamic parameter detection and interactive live sliders (e.g. $m, b, a$).
  * Key Graph Features (KGF) analyzer: roots ($x$-intercepts via bisection search), $y$-intercepts, and local extrema (minima/maxima).
  * Interactive curve tracing with real-time coordinate HUD tooltip.
  * Dedicated function writing keypad with Trigonometry, Inequalities, and Functions flyout popovers.
* Full Windows Calculator Scientific Mode with Floating Popover Drawers (`src/ui/keypad_widget.py`, `src/core/engine.py`):
  * Ribbon bar with DEG / RAD / GRAD cycling button and Fixed-to-Exponential (`F-E`) notation toggle.
  * Trigonometry flyout panel (4x2): `sin`, `cos`, `tan`, `sec`, `csc`, `cot` with `2ⁿᵈ` inverse toggle and `hyp` hyperbolic toggle.
  * Function flyout panel (3x2): `|x|` (abs), `⌊x⌋` (floor), `⌈x⌉` (ceil), `rand` (0-1 random), `→dms` (degrees to DMS), and `→deg` (DMS to degrees).
  * 5x7 main keypad grid with `2ⁿᵈ` function alternate: `x²` <-> `x³`, `²√x` <-> `³√x`, `10ˣ` <-> `2ˣ`, `log` <-> `log₂`, `ln` <-> `eˣ`.
* Windows Calculator Date Calculation Mode (`src/core/date_engine.py`, `src/ui/date_calc_view.py`):
  * "Difference between dates": calculates years, months, weeks, days, total days, business/working days (Monday-Friday).
  * "Add or subtract days": adds/subtracts years, months, and days with month-end day clamping and leap-year (Feb 29) handling.
  * Interactive `QDateEdit` with themed calendar popups in `dd-MM-yyyy` format with industry-standard min/max bounds (1753-9999).
* Complete suite of 19 vector SVG line-art icons for sidebar navigation modes and converters (`src/ui/mode_icons.py`, `assets/icons/modes/`).
* High-resolution multi-size Windows icon (`assets/icons/app_icon.ico`) with 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, and 256x256 pixel layers generated from `assets/icons/app_icon.svg`.
* Dynamic SVG icon tinting engine (`get_themed_icon` in `src/ui/mode_icons.py`) providing theme-reactive vector rendering across all dark and light themes.
* Windows Calculator-style navigation sidebar drawer (`src/ui/sidebar_drawer.py`) supporting Calculator modes and 12 Unit Converters with Windows 11 Fluent scrollbar.
* Comprehensive In-App Diagnostics & Crash Reporter (`src/core/crash_reporter.py`, `src/ui/crash_dialog.py`):
  * Global `sys.excepthook` and `threading.excepthook` capture with formatted stack traces and system diagnostics.
  * User-friendly crash dialog with copy-to-clipboard and one-click GitHub Issue reporting.
* Software Update & Version Picker Management (`src/core/updater.py`, `src/ui/theme_dialog.py`, `src/ui/update_dialog.py`):
  * Automatic GitHub release checks and build browser.
  * Smart filtering excluding non-executable commits (such as initial license commits).
* Strict Input Sanitization & Leading Zero Management across Standard, Scientific, and Programmer modes (`src/ui/display_widget.py`).
* 141 automated unit, math engine, UI interaction, and edge-case tests.

### Fixed
* Primary display `QLineEdit` initialized at small 10pt size; now immediately scales to 44px on instantiation.
* Primary display `QLineEdit` theme color styling corrected with proper `QLineEdit#PrimaryValueDisplay` QSS selector.
* Backspace icon theme reactivity: icon dynamically rendered in white in dark themes and dark rose/gray in light themes.
* Sidebar menu items hover and active highlighting fixed across all 6 themes using high-contrast theme tokens.
* Modern Windows 11 Fluent scrollbar added to sidebar drawer navigation.

---

## [0.1.0] - 2026-11-05

### Added
* Initial project license (MIT) on GitHub.

