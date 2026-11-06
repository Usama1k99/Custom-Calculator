# Agent & Pair Programming Guidelines

Key constraints:
1. Push and commit only when explicitly instructed by the user; bump version before pushing.
2. Emoji usage is not allowed anywhere in the UI buttons, menus, dialogs, etc.
3. End users do not have Python or Git installed: software updates download pre-built release binaries from GitHub.
4. Pinned expression preview must remain visible after pressing `=` or Enter.
5. Automatically add non-core project code files and folders to .gitignore.
6. After each new core feature, consider and handle all edge cases (misinputs, empty/illogical inputs, math errors).
7. Always use clean-looking vector SVGs for UI buttons instead of special characters, letters, or unicode approximations.
8. All SVG icons throughout the app must be dynamically tinted (using currentColor or get_themed_icon) to react to theme changes (light/white in dark themes, dark in light themes). Never hardcode static black/dark icons on dark backgrounds.
