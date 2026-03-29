# Changelog

All notable changes to Scaffold are documented here.

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
