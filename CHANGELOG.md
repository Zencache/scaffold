# Changelog

All notable changes to Scaffold are documented here.

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
