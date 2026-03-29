# Changelog

All notable changes to Scaffold are documented here.

## [v1.4.0] — 2026-03-28

### Improved
- **Code review — Part 5: Final cleanup**
  - Added `--help` / `-h` flag with usage summary listing all available CLI modes
  - Expanded module-level docstring with usage examples and dependency note
  - Linted with `ruff check` — all checks pass (E402 suppressed for intentional deferred PySide6 imports, E741 fixed by renaming `l` → `le` in browse lambdas)
  - Updated README line-count badge to 2,441
  - Verified internal structure follows: constants → helpers → data layer → widget classes → main window → entry point
- **Code review — Part 4: Functional test**
  - Fixed `UnicodeEncodeError` in `--prompt` on Windows terminals using cp1252 (PROMPT.txt contains U+2192 arrow character)
  - Added comprehensive automated functional test suite (`test_functional.py`, 101 assertions) covering: launch/navigation, all 9 widget types, tooltips, required fields, defaults, mutual exclusivity, dependencies, extra flags, command preview, process execution, stop, dark mode, presets, session persistence, subcommands, editable dropdowns, file/directory widgets, output batching, and file size guard
- **Code review — Part 3: Performance**
  - Output panel now buffers `readyRead` data and flushes every 100ms via `QTimer`, preventing UI stalls on high-volume output
  - Output panel capped at 10,000 lines (`setMaximumBlockCount`) — older lines are automatically discarded to bound memory usage
  - Tool schema loader rejects files over 1 MB with a clear error, preventing accidental hangs from oversized or malicious JSON files
  - Verified: signal connections are not duplicated on subcommand switch (visibility toggle, not rebuild)
  - Verified: live preview has no signal loops (`build_command` does not emit signals)
  - Verified: `ToolForm` cleanup via `deleteLater()` on tool switch — no memory leaks
  - Verified: `shutil.which()` per-tool during picker scan is fast with 20+ schemas
- **Code review — Part 1: Cleanup and consistency**
  - Organized imports: moved `tempfile` to stdlib section, consolidated PySide6 imports (`QPoint`, `QPolygon`) at top level
  - Extracted magic numbers into named constants: `SPINBOX_RANGE`, `REPEAT_SPIN_MAX`, `REPEAT_SPIN_WIDTH`, `TEXT_WIDGET_HEIGHT`, `MULTI_ENUM_HEIGHT`, `DEFAULT_WINDOW_WIDTH`, `DEFAULT_WINDOW_HEIGHT`
  - Extracted theme-independent output/status colors into named constants: `COLOR_OK`, `COLOR_ERR`, `COLOR_WARN`, `COLOR_CMD`, `COLOR_DIM`, `OUTPUT_BG`, `OUTPUT_FG`, `LIGHT_WARNING_BG`, `LIGHT_WARNING_FG`, `LIGHT_WARNING_BORDER`
  - Converted `apply_theme` QSS stylesheet from `%` dict formatting to f-strings
  - Renamed signal handlers for clarity: `_read_stdout` → `_on_stdout_ready`, `_read_stderr` → `_on_stderr_ready`
  - Removed misleading phase-number comments from section banners
  - Simplified `reset_to_defaults` by collapsing redundant `elif`/`else` branches
  - Simplified `_is_field_active` with tuple-form `isinstance`
  - Simplified `_on_run_stop` empty-list check to idiomatic `if not cmd:`
  - Removed unused local variable in `_apply_widget_theme`
  - Removed trivial inline comments in `_build_shortcuts`
  - Removed stale comment referencing removed `radio` field type
  - Added docstrings to `MainWindow`, `ToolForm`, `ToolPicker`, and 40+ methods
  - Added Python 3.10+ type hints (`str | None` style) to all key function signatures
- **Code review — Part 2: Error handling audit**
  - `load_tool`: added separate `PermissionError` handler before generic `OSError`
  - `_on_save_preset`: wrapped `write_text()` in try/except `OSError` with user-facing error dialog
  - `_on_delete_preset`: wrapped `unlink()` in try/except `OSError` with user-facing error dialog
  - `_tools_dir` / `_presets_dir`: added guard against file-at-directory-path before `mkdir()`
  - `print_prompt`: wrapped `read_text()` in try/except `OSError` with stderr fallback
  - Audited all QProcess error paths — confirmed Run button and command preview reset correctly in all cases
  - Audited all empty-state edge cases — confirmed all already handled

## [v1.3.1] — 2026-03-28

### Improved
- Added right padding between form fields and scrollbar for cleaner layout

## [v1.3.0] — 2026-03-28

### Added
- **Elevated execution (sudo/admin) support** — run commands with elevated privileges from within Scaffold
- New `elevated` schema field: `null`, `"never"`, `"optional"`, or `"always"`
- Platform-specific elevation: `gsudo` on Windows, `pkexec` on Linux, `pkexec` on macOS
- Elevation checkbox in tool form with contextual notes for optional vs always
- "Running as administrator" status bar indicator when app is already elevated
- Elevation state included in preset save/load
- Graceful handling of missing elevation tools, cancelled password dialogs (exit 126/127), and binary-not-found errors
- Custom arrow icons for dropdown and spinbox controls in dark mode
- Updated `PROMPT.txt` with `elevated` field and decision rule
- All example tool schemas updated with `elevated` field (nmap: optional, others: null)

### Security
- Full command injection audit passed — QProcess uses list-based execution, no shell invocation anywhere
- Malicious schema values (defaults, flags, binary) treated as literal strings, never interpreted

## [v1.2.3] — 2026-03-28

### Improved
- Added prerequisites section to Getting Started (Python version, pip, CLI tool installation, JSON schema)
- Added platform compatibility note (tested on Windows, should work on macOS/Linux)

## [v1.2.2] — 2026-03-28

### Added
- **Dark mode** with system detection and manual toggle (View > Theme menu, Ctrl+D shortcut)
- Three theme options: Light, Dark, and System Default — persisted across sessions
- Catppuccin Mocha-inspired dark color palette with full widget coverage
- Getting started instructions at the top of README

### Improved
- Comprehensive dark mode styling for all widgets (dropdowns, checkboxes, spinboxes, tables, scrollbars, buttons, menus, tooltips, group boxes)
- README disclaimer now notes limitations with large/complex CLI tools

## [v1.2.1] — 2026-03-28

### Improved
- Command preview bar now uses a scrollable widget with a horizontal scrollbar for long commands

## [v1.2.0] — 2026-03-28

### Added
- **Examples field** for string arguments — editable dropdown (QComboBox) showing common values as suggestions while still allowing custom input
- Updated `PROMPT.txt` to include examples field (15 fields per argument)
- Updated all example tool schemas (nmap, ping, git, curl) with expanded argument coverage and examples support
- LLM context window note added to schema generation docs in README

## [v1.1.0] — 2026-03-28

### Added
- **Binary availability check** in tool picker — green checkmark for installed tools, red X for missing ones
- Tools sorted by availability (available first, unavailable second, invalid last)
- 4-column tool picker table (status, tool, description, path)

## [v1.0.1] — 2026-03-28

### Added
- ffmpeg example schema (later removed as incomplete)

## [v1.0] — 2026-03-28

### Added
- Initial release of Scaffold
- Single-file PySide6 application (`scaffold.py`)
- 9 widget types: boolean, string, text, integer, float, enum, multi_enum, file, directory
- Live command preview with copy-to-clipboard
- Process execution with colored stdout/stderr output
- Preset save/load/delete/reset with JSON persistence
- Subcommand support (e.g., git clone, git commit)
- Mutual exclusivity groups (radio-button behavior for conflicting flags)
- Dependency chains (fields activate when parent is set)
- Regex validation for string fields
- Repeatable boolean flags with count spinner
- Separator modes: space, equals, none
- Session persistence (window size/position, last opened tool)
- Drag-and-drop schema loading
- Keyboard shortcuts (Ctrl+Enter, Escape, Ctrl+S, Ctrl+L, etc.)
- CLI validation mode (`--validate`)
- LLM prompt for schema generation (`--prompt` / `PROMPT.txt`)
- Example schemas: nmap, ping, git, curl
- README with full documentation and schema reference
- MIT license
