# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.2] - 2026-11-07 (Pre-Release)

### Fixed
* Fixed Software Update Manager and Live Version Detection (`src/core/updater.py`, `src/ui/theme_dialog.py`):
  * Resolved the root cause where updates and past builds failed to show up: GitHub Releases was empty (`0 releases`) because no GitHub Release objects existed.
  * Implemented a dual-tier live fetching engine: falls back to and merges the GitHub Commits API so builds and versions are pulled live in real-time even before formal releases are drafted.
  * Added semver comparison (`parse_semver`) so newer remote versions or differing build commits are correctly detected as available updates.
  * Excluded license/initial commits from the version picker per specification.
  * Added background worker (`BuildsFetchWorker`) in `ThemeDialog` to auto-fetch builds on open without UI stutter.
  * Provided seamless fallback action: displays "View vX.Y.Z on GitHub" when commit builds lack standalone `.exe` attachments, opening directly in the default browser.
* Fixed Missing Dropdown Arrow / Chevron in QSS (`src/ui/mode_icons.py`, `src/ui/theme_dialog.py`, `src/ui/theme_manager.py`, `src/ui/graph_options_popover.py`):
  * Replaced process-cwd-relative stylesheet URLs (`image: url(...)`) with dynamically tinted absolute forward-slash POSIX paths (`get_themed_svg_path`).
  * Resolves cleanly across any working directory, desktop shortcut launch, and PyInstaller frozen executable environment.
  * Down-arrow chevrons dynamically adapt to active theme colors (light in dark mode, dark in light mode) in compliance with Rule 9.
* Fixed Update Notification Integration (`src/ui/update_dialog.py`, `src/ui/main_window.py`):
  * "Browse Builds..." in update notification dialog now directly navigates to the Settings modal's "Updates & Versions" tab.
  * Startup version check cleanly detects updates and prompts the user.

---

## [0.2.1] - 2026-11-07 (Pre-Release)

### Fixed
* Fixed operator trailing preview bug across Standard, Scientific, and Programmer modes:
  * Entering an operator after a number (e.g. `60 +`) no longer synthesizes duplicate operands or shows bogus live previews (`= 120`).
  * Incomplete drafting expressions ending with any operator (`+`, `-`, `*`, `/`, `×`, `÷`, `−`, `%`, `^`, `mod`, `AND`, `OR`, `XOR`, `NOT`, `<<`, `>>`), unclosed parenthesis, or trailing comma cleanly suppress live ghost previews.
  * Ribbon text formatting fixed so trailing operator is not concatenated with 0 (`60 +` instead of `60 + 0`).
  * Primary display retains current operand value until the next digit is typed, matching Windows Calculator ergonomics.
  * Enhanced backspace to remove trailing operator and restore preceding operand when active token is empty.
* Fixed Qt Style Sheets warning: removed unsupported `caret-color` property that logged warnings on application startup.
* Fixed Windows Taskbar icon: registered explicit `AppUserModelID` via `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID` and prioritized multi-resolution `.ico` via `sys._MEIPASS`.

### Added
* Settings modal footer: added subtle current version indicator (`v0.2.1 (pre-release)`) adhering to active theme palette.

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

