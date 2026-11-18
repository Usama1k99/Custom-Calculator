# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.0] - 2026-11-18 (Official Release)

### Changed
* Window Transparency Range Capped at 0-25% & Blur Discontinuation (`src/ui/theme_dialog.py`, `src/ui/main_window.py`, `src/ui/theme_manager.py`, `src/core/config.py`, `src/ui/toggle_switch.py`):
  * Capped the window transparency slider range to strictly 0-25%, preventing over-transparent illegibility and scaling backend transparency down to subtle, crisp levels (alpha 0.85 at maximum 25%).
  * Updated default `window_transparency` configuration value to 15%.
  * Ensured the Navigation Menu Sidebar strictly remains 100% solid and opaque (`tokens['bg_surface']`, alpha 255) regardless of transparency setting.
  * Renamed UI settings from "Window Blur" to "Window Transparency", introducing `TransparencyToggle` with clean vector SVG icons (transparency layers when ON, solid square when OFF). Zero emojis.
  * Completely discontinued and purged all DWM blur code and files (`src/ui/window_effects.py`).
* ConfigManager Backward-Compatible Schema Migration Engine (`src/core/config.py`):
  * Introduced automatic schema migration engine (`CURRENT_SCHEMA_VERSION = 2`).
  * Automatically detects older unversioned/v1 user configurations upon upgrade, migrates legacy `blur_enabled`/`blur_effect` to `transparency_enabled`, rescales older transparency values to the 0-25 cap, cleans up obsolete blur keys, and saves sanitized configuration to disk without losing any user themes or preferences.
  * Added fallback aliases in `ConfigManager.get()` for seamless backward compatibility.
* Test Suite Consolidation & Optimization (`tests/`):
  * Eliminated obsolete, long-running challenger and stress test scripts (`test_adversarial_maximized_modes.py`, `test_adversarial_window_geometry.py`, `test_challenger_*`) that repeatedly looped `time.sleep` and `QTest.qWait` cycles.
  * Consolidated core geometry, Aero Snap, NCHITTEST codes, multi-monitor clamping, and emoji enforcement into [`tests/test_window_geometry.py`](file:///d:/PartA/Usama/Programming/Calculator/tests/test_window_geometry.py).
  * Reduced full test suite execution time from over 40 minutes down to ~50 seconds across all 14 core test modules.
* Project Repository Cleanup:
  * Purged untracked and redundant workspace artifacts, including `.agents/`, `build/`, `dist/`, `tools/`, screenshots (`screenshots_m3/`, `screenshots_m4/`, `visual_proof/`, root `.png` files), and stale `__pycache__` directories.

### Added
* Offline Internet Handling (`src/core/updater.py`, `src/ui/main_window.py`, `src/ui/theme_dialog.py`):
  * Integrated proactive internet connectivity detection (`is_connected_to_internet`).
  * Suppressed automatic update checks on application startup when offline.
  * In the Version Settings panel, automatically disabled update check and version switching buttons when offline, displaying a clean "Not connected to internet." notice without emojis.

### Fixed
* Toggle Switch Responsiveness & Instant Theme Application (`src/ui/toggle_switch.py`, `src/ui/theme_dialog.py`, `src/ui/history_drawer.py`, `src/ui/main_window.py`):
  - Upgraded both `ThemeModeToggle` and `TransparencyToggle` easing curves from slow-accelerating `InOutCubic` to immediate-peak-velocity `OutQuad` (110ms), eliminating toggle startup hesitation.
  - Discovered and eliminated the root cause of the ~900ms stylesheet reapplication freeze: SQLite history was generating 14,000+ QWidgets in `HistoryDrawer`, causing Qt's C++ styling engine to traverse the massive widget tree on every theme change.
  - Capped rendered calculation cards in `HistoryDrawer` to 50 items (with an on-demand "Load more" button for older items) and purged hidden cards when the drawer closes. This slashed total window styling time from **890ms to 31ms** (a 96.5% performance improvement).
  - Toggles and sliders are treated distinctly: toggles apply themes immediately (<31ms) with zero perceptible delay as the knob glides smoothly, while the transparency slider keeps mouse scrubbing completely lag-free (updating percentage labels in memory and applying the theme upon `sliderReleased` or 40ms debounce).
  - Fixed `NameError: name 'QPropertyAnimation' is not defined` in `src/ui/theme_dialog.py`.
* Minimalist Transparency Vector SVGs (`src/ui/toggle_switch.py`):
  - Replaced noisy dashed lines and prohibition-style diagonal slashes with clean, minimal vector artwork:
    - **ON**: Two overlapping minimalist rounded window panes (`rx=2.5`, `stroke-width=1.8`) representing layering and transparency.
    - **OFF**: Single solid rounded window pane (`rx=2.5`, `stroke-width=1.8`, 35% solid fill) representing an opaque surface.
* Transparency Slider Lag & Smooth Scrubbing (`src/ui/theme_dialog.py`):
  * Decoupled transparency slider movement from stylesheet re-parsing and full-tree SVG re-rendering during active mouse dragging.
  * Live dragging updates only the in-memory percentage label with zero frame drops, and applies the theme stylesheet cleanly only after dragging ends (`sliderReleased` or debounced navigation) for buttery-smooth movement.
* Test Runner Blocking Modal Dialogs (`src/ui/main_window.py`):
  * Guarded `_start_version_check()` against running in `unittest` or `pytest` execution environments, preventing background worker threads from launching modal update dialogs (`dlg.exec()`) that stalled test runs.
* PyInstaller Self-Replacement Child DLL & Working Directory Fix (`src/core/updater.py`):
  * Stripped `_MEIPASS2` and `_MEIPASS` environment variables from both the Python `subprocess.Popen` caller environment and the child PowerShell execution environment prior to relaunching the replaced executable. This prevents PyInstaller onefile bootloader from falsely assuming child process status and failing with `Failed to load Python DLL ... python312.dll: The specified module could not be found`.
  * Applied literal PowerShell here-strings (`@'...'@`) for target and destination executable paths to eliminate quote and backslash parsing anomalies.
  * Explicitly passed `-WorkingDirectory` matching the target executable's directory to `Start-Process`, preventing "invalid or wrong path" errors upon relaunch.
* Self-Update Detached Process Replacement (`src/core/updater.py`):
  * Replaced the broken `timeout /t 1` command in the update batch script with `ping 127.0.0.1 -n 2 >nul`, preventing Windows CMD from terminating immediately with `ERROR: Input redirection is not supported` when executed in non-interactive/detached shells without stdin.
  * Added a robust 30-attempt retry loop with 1-second delays to wait for Windows to release file locks on the running executable before replacing it, followed by automatic relaunch and cleanup.
* Pure Greyscale Application Icon (`assets/icons/app_icon.svg`, `assets/icons/app_icon.ico`):
  * Normalized all gradient stops, borders, and fills in `app_icon.svg` to 100% pure neutral greyscale (`R == G == B`).
  * Regenerated the multi-resolution Windows executable icon (`app_icon.ico`) with 16, 20, 24, 32, 40, 48, 64, 128, and 256 pixel frames, eliminating rasterization color fringes and blue-tinted zinc artifacts.
* Legacy Branding Purge:
  * Completely removed all references to "Apex Calculator", "ApexCalc", and `.apexcalculator` across the repository (`README.md`, `main.py`, `src/core/crash_reporter.py`, `src/core/currency_engine.py`, `src/ui/crash_dialog.py`, `src/ui/date_calc_view.py`, `src/ui/theme_dialog.py`, `tests/test_crash_reporter.py`).
  * Updated crash report directories to `%LOCALAPPDATA%/CustomCalculator/CrashReports` and `%APPDATA%/CustomCalculator/CrashReports`.

## [0.6.0] - 2026-11-11 (Official Release)

### Fixed
* Window Maximization & Aero Snap Layout (`src/ui/main_window.py`, `src/ui/theme_manager.py`, `src/ui/native_window.py`):
  * Adopted the proven Enveil architectural pattern for frameless windows on Windows 11: removed `WA_TranslucentBackground` from the top-level window and styled `QMainWindow` with solid `{bg_window}` palette background to prevent DirectComposition visual swapchain freeze on maximize.
  * Replaced broken DirectComposition/DWM composition backdrop overrides with clean OS-level window opacity (`setWindowOpacity`), eliminating transparent void borders, frozen top-left thumbnails, and click-through artifacts across all calculator and graphing modes.
  * Clamped `params.rgrc[0] = mi.rcWork` in `WM_NCCALCSIZE` to ensure zero border spillover across multi-monitor setups.
* Multi-Monitor Boundary Clamping (`src/ui/native_window.py`):
  * Configured explicit 64-bit ctypes `c_void_p` parameter and return types for `HMONITOR` and `HWND` to prevent pointer truncation in multi-monitor coordinate lookups.
  * Replaced window-handle queries with `MonitorFromRect` on proposed coordinates in `WM_NCCALCSIZE`, properly handling negative virtual coordinates on secondary displays and clamping strictly to `mi.rcWork` with zero monitor leakage.
* Dynamic Resizing State Integrity (`src/ui/main_window.py`):
  * Guarded `_toggle_history`, mode switching, and always-on-top against calling `self.resize()` while maximized.
  * Used in-place Win32 `SetWindowPlacement` to update `rcNormalPosition` when the history drawer is closed while maximized, ensuring subsequent restore returns cleanly to the 380px compact width.
  * Replaced window recreation in `_toggle_always_on_top` with in-place Win32 `SetWindowPos` Z-order toggling.
  * Guarded `resizeEvent` and `closeEvent` against writing maximized dimensions into `config.json`.
* Vector SVG Window Controls (`src/ui/title_bar.py`, `src/ui/mode_icons.py`):
  * Replaced Unicode font glyphs with clean, dynamically tinted vector SVGs (`WindowMinimize`, `WindowMaximize`, `WindowRestore`, `WindowClose`) that automatically adapt to light and dark theme palettes.
* Sign Inversion & Ghost Preview Synchronization (`src/core/state.py`, `src/ui/display_widget.py`):
  * Fixed `+/-` (negate) button behavior so operands in binary calculations wrap into clean `negate(...)` representations.
  * Standalone negative decimals (e.g. `-0.95`) suppress phantom positive ghost previews (`= 0.95`).
  * Pressing `=` preserves negative numbers without inverting signs.
* Unary Operator Chaining (`src/core/state.py`):
  * Sequential unary operations (`1/x`, `sqr`, `sqrt`) now chain cleanly in the ribbon representation (e.g. `10 -> 1/(10) -> sqr(1/(10)) -> √(sqr(1/(10)))`).
* Graphing Mode Function Input Crash (`src/ui/graphing_view.py`):
  * Replaced lambda monkey-patch on `mousePressEvent` with `FunctionInputLineEdit` subclass emitting custom Qt signals, eliminating `TypeError: invalid argument to sipBadCatcherResult()`.

### Added
* Release Status Marking System (`src/core/updater.py`, `src/ui/update_dialog.py`):
  * Added version status labeling (`deprecated`, `not_recommended`, `functional`). Deprecated builds update immediately without prompts; Not Recommended builds warn the user with highlighted alerts; Functional builds offer standard update notifications.
* Greyscale Application Logo & Multi-Resolution ICO (`assets/icons/app_icon.svg`, `assets/icons/app_icon.ico`):
  * Redesigned calculator logo into clean greyscale with transparent empty areas, vertical rectangular proportions, and lighter outer border.
* Adversarial Multi-Monitor & Geometry Test Suites (`tests/`):
  * Added automated test suites (`test_challenger_m4_adversarial.py`, `test_challenger_m4_empirical_stress.py`, `test_adversarial_window_geometry.py`) validating layout integrity across all 18 calculator and converter modes (259 tests passing).

---

## [0.3.0] - 2026-11-07 (Official Release)

### Added
* Automated GitHub Releases Publishing (`.github/workflows/release.yml`, `scripts/publish_release.py`):
  * Automated GitHub Actions release pipeline configured to trigger exclusively on major/minor version pushes (`v*.*.0`), compiling `CustomCalculator.exe` and publishing directly to GitHub Releases with zero manual steps.
  * Added `scripts/publish_release.py` for direct authenticated API uploads using personal access tokens.
* Direct In-App Executable Self-Update Engine (`src/core/updater.py`, `src/ui/update_dialog.py`, `src/ui/theme_dialog.py`):
  * Replaced all fallback browser redirects with direct executable auto-updates: clicking "Update to Latest" or "Switch to Version" downloads the `.exe` directly inside the app with real-time percentage progress.
  * Enhanced Windows process replacement (`apply_update_and_restart`): uses PID-targeted process monitoring (`tasklist /fi "PID eq %PID%"`) to cleanly wait for process exit, unlock file handles, replace the binary, and relaunch the updated calculator.
  * Robust binary download fallback (`BinaryDownloadWorker`): resolves tag-specific release downloads and automatically falls back to canonical latest release endpoints.

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

