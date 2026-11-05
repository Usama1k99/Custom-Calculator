# Custom-Calculator (ApexCalc)

A sleek, lightweight, distraction-free desktop calculator built with native Python. Engineered for high performance with cold startup under 150 milliseconds, minimal memory consumption (<40 MB RAM), session-wise persistent history, dual-tier sticky expression display, and native hardware Numpad support.

---

## Key Features

* **Dual-Tier Sticky Expression Display:**
  * While typing, displays a real-time ghost preview of the calculation.
  * After pressing `=` or Numpad `Enter`, the exact formula remains pinned in the upper ribbon (`Expression =`), ensuring you never lose the computational context.
  * Automatic `Ans` chaining when entering subsequent arithmetic operators.
* **Persistent Session-Wise Calculation History:**
  * Relational storage using Python's built-in `sqlite3` (`data/history.db`).
  * Grouped into collapsible sessions: Active (live), Today, Yesterday, and Historical Archive.
  * Click any historical expression to reload it into the active editor, or click a result to inject it.
  * Fully searchable by mathematical expression, result value, or mode.
* **First-Class Hardware Numpad Ergonomics:**
  * Native `QKeyEvent` key-filtering for all physical Numpad keys (`0-9`, `+`, `−`, `×`, `÷`, `.`, `Enter`).
  * Seamless behavior regardless of whether `NumLock` is toggled ON or OFF.
  * Synchronized visual keypress depression animation (65ms tactile response).
* **Six Curated Minimalist Themes + IDE Color Picker:**
  * **Dark Modes:** Monokai Pro, Obsidian OLED, Charcoal Graphite.
  * **Light Modes:** Soft Rose Pink, Snow Minimalist, Warm Parchment.
  * **Theme Customizer GUI:** Integrated color picker popover allowing real-time editing of background, surface, key, and accent colors with live UI preview.
* **Full Windows Calculator Modes & Converters:**
  * **Standard, Scientific, and Programmer** modes with full bitwise logic (`AND`, `OR`, `XOR`, `NOT`, `<<`, `>>`, `mod`).
  * **Interactive Graphing Mode:** Multi-function equation deck (up to 6 curves), antialiased Cartesian grid, zoom-adaptive axes, cursor-centered panning/zooming, parameter sliders ($m, b, a$), asymptote protection, real-time curve tracing HUD tooltip, and Key Graph Features (roots, $y$-intercepts, local extrema).
  * **Date Calculation Mode:** Calculate exact differences between two dates (years, months, weeks, days, business days) or add/subtract time with leap year and month-end clamping.
  * **12 Unit Converters:** Length, Weight, Temperature, Currency, Energy, Speed, Time, Power, Data, Pressure, Angle, Area.
* **Native Windows 11 Acrylic Blur / Glass Effect:**
  * Uses Windows Desktop Window Manager (`DWMWA_SYSTEMBACKDROP_TYPE = 38`) to render native frosted acrylic blur behind the calculator window.
  * Preserves Windows 11 Snap Layouts and frameless edge-resizing without layering artifacts.
  * Configurable with a toggle in Theme Settings and automatically tuned for dark and light palettes.
* **Arbitrary Precision Numerical Engine:**
  * Powered by Python's standard `decimal.Decimal` (36+ decimal digits default).
  * Immune to standard IEEE-754 binary floating-point anomalies (such as `0.1 + 0.2`).
* **Zero-Dependency Release Auto-Updater:**
  * Checks for new GitHub Releases on launch against `Usama1k99/Custom-Calculator`.
  * Downloads pre-built standalone binaries directly without requiring Python or Git on the client machine.

---

## Project Governance & Build Rules

1. **Explicit Permission Required for Commits & Pushes:** Push and commit only when explicitly instructed by the user; bump version before pushing.
2. **Mandatory Post-Push Executable Build:** Build standalone exe using PyInstaller after each commit and push.
3. **Strict No-Emoji Policy:** Emoji usage is strictly prohibited anywhere in UI buttons, menus, dialogs, titles, or tooltips.
4. **Zero-Dependency End-User Upgrades:** End users do not have Python or Git installed; software updates download pre-built release binaries from GitHub.
5. **Pinned Expression Preview:** Pinned expression preview must remain visible after pressing `=` or `Enter`.
6. **Automatic Gitignore Management:** Automatically add non-core project code files and folders to `.gitignore`.
7. **Rigorous Edge Case Handling:** After each new core feature, consider and handle all edge cases (misinputs, empty/illogical inputs, math errors).

---

## Technology Stack

* **Language:** Python 3.12+
* **GUI Engine:** PyQt6
* **Window Blur / Glass Effects:** Windows 11 Desktop Window Manager (DWM) Acrylic via ctypes
* **Styling:** Qt Style Sheets (QSS) with SVG chevrons and vector icons
* **Numerical Core:** Python standard library `decimal`, `ast`, and `math`
* **Local Persistence:** Python standard library `sqlite3`
* **Compilation / Packaging:** PyInstaller

---

## Directory Structure

```
Custom-Calculator/
├── assets/
│   └── icons/                 # Minimal SVG icons and application icon options
├── planning/                  # Architectural specs and design plans (gitignored)
│   ├── CORE_APP_AND_FEATURES.md
│   ├── UI_DESIGN_AND_THEMES.md
│   └── versions_and_exe_build.md
├── src/
│   ├── core/                  # Math engine, lexer, parser, state machine
│   ├── database/              # SQLite session history manager
│   ├── ui/                    # Windows, widgets, themes, color picker
│   └── version.py             # Version tracking and commit hash registry
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── main.py                    # Application entry point
├── README.md
└── requirements.txt
```

---

## Development Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone git@github.com:Usama1k99/Custom-Calculator.git
cd Custom-Calculator

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python main.py
```

---

## Compiling Standalone Executable (Windows)

```bash
pyinstaller --noconfirm --clean --windowed --onefile --name "CustomCalculator" --icon "assets/icons/app_icon.ico" main.py
```

The resulting standalone executable will be generated in `dist/CustomCalculator.exe`.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

