# Changelog

All notable changes to Scaffold are documented here.

## [v2.5.7] — 2026-03-30

### Changed

- **Delete Tool** rebuilt as a button on the tool picker instead of a File menu action — simpler, more discoverable, and handles deletion entirely within ToolPicker
- **Preset deletion** hardened: uses `unlink()` instead of `unlink(missing_ok=True)` and uses early-return pattern for clearer control flow
- Removed right-click context menu and File menu "Delete Tool..." action
- Delete button disabled by default, enables only when a valid tool is selected
- Version bump 2.5.6 → 2.5.7

### Fixed

- **Delete Tool** file menu action was permanently greyed out — replaced with picker button that tracks selection state
- **Preset delete** control flow clarified with early-return pattern

---

## [v2.5.6] — 2026-03-30

### Fixed

- **Preset delete dialog** now includes a git restore tip (`git checkout -- presets/{tool}/{file}`) matching the tool schema delete dialog
- **Delete Tool tests** now exercise the real `_delete_tool()` code path with mocked dialogs instead of bypassing it with direct `unlink()` calls

### Added
- **Test 30l** — verifies preset delete dialog includes git restore tip (3 assertions)
- **Test 30m** — verifies Delete Tool menu enable/disable across picker ↔ form transitions (3 assertions)

### Changed
- Version bump 2.5.5 → 2.5.6
- scaffold.py line count: 3,368 → 3,760
- Test assertion total: 576 → 659 across 5 suites

---

## [v2.5.5] — 2026-03-30

### Added

#### Process Timeout

Auto-kill processes that run too long. Useful for fire-and-forget execution of tools like `nmap` or `hashcat` where the user may walk away.

- **Timeout spinbox** in the action bar next to the Run/Stop button. Label: "Timeout (s):", range 0–99999, default 0 (no timeout). Fixed width 80px.
- **Single-shot QTimer** (`_timeout_timer`) starts when Run is clicked and timeout > 0. If the timer fires before the process finishes, the process is killed with a warning message: "Process timed out after N seconds" in `COLOR_WARN`.
- **Timer cancellation** — timer is stopped when the process finishes normally, when the user clicks Stop, or when a new tool is loaded.
- **Per-tool persistence** — timeout value saved to QSettings as `timeout/{tool_name}` and restored when the tool is loaded. Each tool remembers its own timeout independently.
- **`_timed_out` flag** — distinguishes timeout kills from manual stops. Status bar shows "Timed out (Ns)" instead of "Process stopped".
- **`blockSignals`** used during timeout restore to prevent spurious QSettings writes.
- **`datetime`** module (stdlib) was added in v2.5.4 and is reused here — no new dependencies.

### Changed
- Version bump 2.5.4 → 2.5.5
- scaffold.py line count: 3,324 → 3,368

### Tested
- **Section 29** — Process Timeout (12 assertions): timeout spinbox exists and defaults to 0, range 0–99999, value persisted to QSettings, value restored on tool reload, timeout timer exists and is single-shot, `_timed_out` attribute exists, timer not active when no process running, different tools get independent timeout values

#### Full suite results
- **All 4 test suites pass: 576/576 assertions, 0 failures**
  - Functional: 406/406 (+12 Section 29)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)

---

## [v2.5.4] — 2026-03-30

### Added

#### Output Export (Save Output...)

Save command output to a text file for later review or sharing.

- **"Save Output..." button** added to the action bar, next to "Clear Output".
- **`QFileDialog.getSaveFileName`** opens a native save dialog with a suggested filename: `{tool_name}_output_{YYYYMMDD_HHMMSS}.txt`, defaulting to the user's home directory.
- **Plain text export** via `QPlainTextEdit.toPlainText()` — strips all formatting. Includes the command echo line (`$ command`) if present.
- **UTF-8 encoding** for saved files.
- **Empty output guard** — if the output panel is empty, shows "No output to save" in the status bar instead of opening the dialog.
- **Status bar confirmation** — shows the saved file path on success, or an error message on failure.
- **`MainWindow._save_output(path=None)`** — accepts an optional `path` argument for testability (skips the dialog). Normalizes the `bool` passed by `QPushButton.clicked` to `None` via `isinstance` check.
- **`datetime`** module added to imports (stdlib, no new dependencies).

### Changed
- Version bump 2.5.3 → 2.5.4
- scaffold.py line count: 3,291 → 3,324

### Tested
- **Section 28** — Output Export (11 assertions): Save Output button exists, saved file contains command echo line and output text and exit line, UTF-8 encoding preserves snowman/heart/accented characters, empty output creates no file and shows status bar message, status bar confirms save path on success

#### Full suite results
- **All 4 test suites pass: 564/564 assertions, 0 failures**
  - Functional: 394/394 (+11 Section 28)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)

---

## [v2.5.3] — 2026-03-30

### Added

#### Output Search (Ctrl+Shift+F)

Search within the output panel to find text in command output. Separate from the form field search (Ctrl+F).

- **Search bar:** A `QLineEdit` + match count label appears above the output panel when Ctrl+Shift+F is pressed. Initially hidden. Placeholder: "Search output... (Ctrl+Shift+F)".
- **Highlighting:** Uses `QPlainTextEdit.extraSelections` to highlight all matches — yellow (`#fff176`) for non-current matches, orange (`#ff9800`) for the current match. Highlights are cleared when the search bar is closed.
- **Navigation:** Enter jumps to next match, Shift+Enter to previous. Wrap-around at both ends. Each jump scrolls the output panel to the current match via `ensureCursorVisible()`.
- **Match count:** Label next to search bar shows "X of Y" (e.g., "2 of 5") or "0 matches" when nothing is found.
- **Case-insensitive:** Uses `QTextDocument.find()` without `FindCaseSensitively` flag — "ERROR" matches "error", "Error", etc.
- **Escape handling:** Escape closes the output search bar only when it has focus — does not steal Escape from the Stop button or the field search bar. Priority: output search → field search → stop process.
- **`MainWindow.eventFilter()`** — new override to intercept Enter/Shift+Enter/Escape on the output search bar.
- **`MainWindow._close_output_search()`** — hides bar, clears matches, clears extraSelections.
- **`MainWindow._on_output_search_changed()`** — recomputes all matches when search text changes.
- **`MainWindow._apply_output_search_highlights()`** — builds extraSelections list with current-match and other-match formatting.
- **`MainWindow._output_search_next()` / `_output_search_prev()`** — cycle through matches with wrap-around.
- **`QTextCursor`** added to `PySide6.QtGui` import line.

### Changed
- Version bump 2.5.2 → 2.5.3
- scaffold.py line count: 3,144 → 3,291

### Tested
- **Section 27** — Output Search (25 assertions): search bar initially hidden, Ctrl+Shift+F shows it, search bar exists on MainWindow, 3 matches for "error" found, count label shows "1 of 3", current match index starts at 0, Enter advances through matches with correct count labels, Enter wraps around to first match, Shift+Enter wraps to last match, 3 extraSelections applied, current match has orange background while others have yellow, Escape hides bar and clears highlights and count label, 0-match search shows "0 matches" without crash, case-insensitive "ERROR" matches 3 times, clearing search text clears highlights and count label

#### Full suite results
- **All 4 test suites pass: 553/553 assertions, 0 failures**
  - Functional: 383/383 (+25 Section 27)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)

---

## [v2.5.2] — 2026-03-30

### Fixed

#### Output Panel Drag Handle Off-Screen Bug

The output panel resize handle allowed dragging the panel taller than the visible window area. The oversized height was saved to QSettings, so the problem persisted across restarts and could only be fixed by fullscreening the window.

- **Root cause:** `DragHandle.mouseMoveEvent` clamped height to a static `OUTPUT_MAX_HEIGHT` (800px) which can exceed available space on smaller windows.
- **`DragHandle._effective_max_height()`** — new method that returns `min(OUTPUT_MAX_HEIGHT, window.height() // 2)`, dynamically capping the drag limit to half the actual window height.
- **`DragHandle.mouseMoveEvent()`** — now uses `_effective_max_height()` instead of the static `OUTPUT_MAX_HEIGHT`.
- **`MainWindow._clamp_output_height()`** — new method that checks if the output panel exceeds the effective max and shrinks it, updating QSettings.
- **`MainWindow.resizeEvent()`** — new override that calls `_clamp_output_height()` when the window shrinks.
- **`MainWindow.showEvent()`** — new override that calls `_clamp_output_height()` on first display, clamping any oversized height restored from QSettings.
- `OUTPUT_MIN_HEIGHT` and `OUTPUT_MAX_HEIGHT` constants are unchanged; the effective maximum is now `min(OUTPUT_MAX_HEIGHT, window_height // 2)`.

### Changed
- Version bump 2.5.1 → 2.5.2
- scaffold.py line count: 3,116 → 3,144

### Tested
- **Section 26** — Output Panel Height Clamping (8 assertions): direct clamping reduces height to half window, OUTPUT_MIN_HEIGHT floor respected, effective max calculation correct, resizeEvent and showEvent overrides exist, QSettings updated on clamp, height within limits left unchanged

#### Full suite results
- **All 4 test suites pass: 528/528 assertions, 0 failures**
  - Functional: 358/358 (+8 Section 26)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)

---

## [v2.5.1] — 2026-03-30

### Added

#### Syntax-Colored Command Preview

The command preview panel now displays syntax-colored output. Each token type is rendered in a distinct color for instant visual parsing of the assembled command.

- **Color constants:** Two new dicts `LIGHT_PREVIEW` and `DARK_PREVIEW` define per-token-type colors for light and dark modes. Token types: `binary` (bold blue), `flag` (amber/orange), `value` (default text), `subcommand` (bold blue), `extra` (dimmed gray, italic).
  - Light mode: binary `#0550ae`, flag `#953800`, value `#24292f`, subcommand `#0550ae`, extra `#656d76`
  - Dark mode: binary `#89b4fa`, flag `#fab387`, value `#cdd6f4`, subcommand `#89b4fa`, extra `#a6adc8`
- **Preview widget replaced:** `QPlainTextEdit` → `QTextEdit` for rich text support. `QTextEdit` is a built-in PySide6 widget that accepts HTML-like markup for inline styling — no web engine, no external dependencies, no HTML files. `toPlainText()` still works identically for all existing code paths.
- **`_quote_token(token)`** — helper function that wraps tokens containing spaces or shell metacharacters in single quotes for display, matching the quoting behavior of `_format_display()`.
- **`_colored_preview_html(cmd, extra_count)`** — walks the command token list and wraps each token in a `<span>` with the appropriate color from the active theme's palette. Handles:
  - Binary name (index 0): bold + binary color
  - Flags (`-` prefix): flag color, with `--flag=value` split into flag-colored flag part and value-colored value part
  - Flag values (token after a flag): value color
  - Extra flags (last `extra_count` tokens): italic + dimmed extra color
  - All tokens are HTML-escaped via `html.escape()` to prevent injection
- **`_update_preview()`** now calls `_colored_preview_html()` and sets the result via `self.preview.setHtml()` instead of `setPlainText()`.
- **Theme toggle re-colors:** Switching dark/light mode triggers `_update_preview()`, which regenerates HTML with the new color palette. No stale colors.
- **Copy Command unchanged:** `_copy_command()` still copies plain text via `_format_display()` — no HTML in clipboard.
- **Dark mode stylesheet:** Updated selector from `QPlainTextEdit` to `QTextEdit` for the preview panel background color.
- **No new dependencies:** `html` module (stdlib) imported locally inside `_colored_preview_html()`. `QTextEdit` is part of PySide6.QtWidgets (already imported).

### Changed
- Version bump 2.5.0 → 2.5.1
- scaffold.py line count: 3,023 → 3,116
- Preview widget type: `QPlainTextEdit` → `QTextEdit` (rich text capable, same API for plain text extraction)
- `QTextEdit` added to PySide6.QtWidgets import line
- Dark mode stylesheet selector updated from `QPlainTextEdit` to `QTextEdit`

### Tested
- **Section 25** — Colored Command Preview (26 assertions): preview widget is `QTextEdit` (not `QPlainTextEdit`), plain text extraction contains binary name, HTML output contains `color:` styles and `<span>` tags, binary is bold (`font-weight:bold/600/700`), setting a flag value produces correctly colored HTML with flag color from `LIGHT_PREVIEW`/`DARK_PREVIEW`, Copy Command produces plain text with no HTML tags, dark mode toggle updates preview to use `DARK_PREVIEW` colors, light mode toggle restores `LIGHT_PREVIEW` colors, reset-to-defaults shows just binary name still with color and bold styling, direct `_colored_preview_html()` contract tests (token count, span count), extra flags rendered italic, equals separator `--flag=value` splits correctly with flag color on flag part

#### Full suite results
- **All 4 test suites pass: 520/520 assertions, 0 failures**
  - Functional: 350/350 (+26 Section 25)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)
- All 9 tool schemas validate with zero errors
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new external dependencies

---

## [v2.5.0] — 2026-03-30

### Added

#### Collapsible Argument Groups — `display_group` field

New optional argument field `display_group` (string or null) enables visual grouping of related arguments into collapsible sections. Arguments sharing the same `display_group` value are rendered inside a `QGroupBox` with that value as the title. The group box is collapsible: clicking its header toggles visibility of the contained fields.

- **Schema field:** `"display_group": null` added to `ARG_DEFAULTS` as the 16th argument field. Accepts a string (group name) or null (ungrouped — renders flat as before).
- **Normalization:** `normalize_tool()` automatically fills missing `display_group` keys with null via the existing `ARG_DEFAULTS` loop. All existing schemas remain valid with no changes.
- **Validation:** `_validate_args()` accepts `display_group` as an optional string-or-null field. Non-string, non-null values produce a validation error.
- **Form rendering:** `_add_args()` partitions arguments by `display_group` value. Ungrouped arguments render directly in the form layout. Grouped arguments are collected into a `QGroupBox` per unique `display_group` name, with a `QFormLayout` inside. The group box title is clickable (pointer cursor) and toggles content visibility via `_toggle_display_group()`.
- **Collapse state:** Tracked via `_dg_collapsed` property on each `QGroupBox`. Default: expanded (False). State does not persist across sessions.
- **Subcommand support:** Display groups work identically within subcommand argument sections.
- **No impact on existing behavior:** Command assembly (`build_command()`), preset serialization/deserialization (`serialize_values()` / `apply_values()` / `reset_to_defaults()`), mutual exclusivity groups, dependencies, and all existing widget types are completely unchanged.
- **New `ToolForm` attributes:**
  - `self.display_groups` — dict keyed by scope → `{display_group_name: QGroupBox}`
  - `_add_single_arg()` — extracted from `_add_args` loop body for reuse by both ungrouped and grouped code paths
  - `_toggle_display_group(box)` — toggles collapsed state and content visibility of a display group QGroupBox
- **PROMPT.txt updated:** Field count 15 → 16, `display_group` documented in the argument object spec, added to all example arguments, checklist updated.

#### Field Search / Jump — Ctrl+F

Always-visible `QLineEdit` search bar positioned below the tool name, description, and separator. Users can type to search or press Ctrl+F to focus it. Searches field names and flag names across all visible fields (global args + current subcommand).

- **Search bar widget:** `QLineEdit` with placeholder text `"Find field...  (Ctrl+F)"`, always visible at the top of the form area (below tool header, above elevation/subcommand controls). Paired with a `QLabel` "No matches" indicator that appears when a query has zero results.
- **Search behavior:** Case-insensitive substring matching against both the argument `name` (human-readable label) and `flag` (CLI flag string). As the user types, the first matching field's label receives a yellow highlight (`background-color: #fff176`) and the `QScrollArea` scrolls to make it visible via `ensureWidgetVisible()`.
- **Match cycling:** Enter key jumps to the next match (`_search_next`), Shift+Enter jumps to the previous match (`_search_prev`). Index wraps around at both ends.
- **Display group integration:** If a match is found inside a collapsed `display_group` section, the section is automatically expanded before scrolling.
- **Scope filtering:** Only searches fields in visible scopes — global args (`__global__`) and the currently selected subcommand. Hidden subcommand sections are excluded.
- **Keyboard shortcuts:** Ctrl+F focuses the search bar and selects all text. Escape clears the search text, removes all highlights, and defocuses the bar. Enter/Shift+Enter handled via `eventFilter` installed on the search bar.
- **Implementation:** `open_search()` focuses the bar, `close_search()` clears text/highlights/state and defocuses. `_on_search_text_changed()` rebuilds the match list on every keystroke. `_highlight_and_scroll()` applies the highlight stylesheet and scrolls. `_clear_search_highlights()` resets all highlighted labels.
- **No impact on existing behavior:** No schema changes, no command assembly changes, no preset changes. Ctrl+F does not conflict with any existing shortcut (Ctrl+Enter, Escape, Ctrl+S, Ctrl+L, Ctrl+O, Ctrl+R, Ctrl+D, Ctrl+B, Ctrl+Q).

### Changed
- Version bump to 2.5.0
- scaffold.py line count: 2,823 → 3,023
- Argument field count: 15 → 16 (`display_group` added)
- PROMPT.txt: argument object field count 15 → 16, example arguments updated with `display_group: null`, checklist updated
- `QScrollArea` in `ToolForm._build_ui()` stored as `self._scroll` (was local variable `scroll`) to support `ensureWidgetVisible()` in field search
- `_shortcut_stop()` in `MainWindow` now checks if the search bar is active and clears it before attempting to stop a running process

### Tested
- **Section 23** — Collapsible Argument Groups (24 assertions): QGroupBox creation with correct title, field containment (3 grouped fields inside box, 2 ungrouped fields outside), `_dg_content` property existence, initial expanded state, collapse toggle, expand toggle, `build_command()` output unchanged with grouped fields, preset serialization/deserialization round-trip, `display_groups` dict populated correctly, subcommand schema with display groups
- **Section 24** — Field Search / Jump (29 assertions): search bar always visible with correct placeholder text, open_search focuses bar, partial name match highlights correct label with `background-color` style, close_search clears text/highlights/state while bar remains visible, flag name search (`--top-ports`) finds exact match, no-match query shows "No matches" label without crash, clearing text hides "No matches" label, Enter cycles to next match (index advances, previous highlight cleared, new highlight applied), Shift+Enter cycles backward, Escape clears search state, single-match wrap-around

#### Test schemas added
- `tests/test_display_groups.json` — 5 arguments: 3 with `display_group: "Network"` (string, integer, enum types), 2 with `display_group: null` (boolean, file types)
- `tests/test_display_groups_subcmd.json` — subcommand schema with `display_group: "Scan Options"` on 2 of 3 subcommand arguments, plus 1 ungrouped global argument

#### Full suite results
- **All 4 test suites pass: 494/494 assertions, 0 failures**
  - Functional: 324/324 (+24 Section 23, +29 Section 24)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)
- All 9 tool schemas validate with zero errors
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new external dependencies

---

## [v2.4.0] — 2026-03-30

### Added

#### Collapsible Argument Groups — `display_group` field

New optional argument field `display_group` (string or null) enables visual grouping of related arguments into collapsible sections. Arguments sharing the same `display_group` value are rendered inside a `QGroupBox` with that value as the title. The group box is collapsible: clicking its header toggles visibility of the contained fields.

- **Schema field:** `"display_group": null` added to `ARG_DEFAULTS` as the 16th argument field. Accepts a string (group name) or null (ungrouped — renders flat as before).
- **Normalization:** `normalize_tool()` automatically fills missing `display_group` keys with null via the existing `ARG_DEFAULTS` loop. All existing schemas remain valid with no changes.
- **Validation:** `_validate_args()` accepts `display_group` as an optional string-or-null field. Non-string, non-null values produce a validation error.
- **Form rendering:** `_add_args()` partitions arguments by `display_group` value. Ungrouped arguments render directly in the form layout. Grouped arguments are collected into a `QGroupBox` per unique `display_group` name, with a `QFormLayout` inside. The group box title is clickable (pointer cursor) and toggles content visibility via `_toggle_display_group()`.
- **Collapse state:** Tracked via `_dg_collapsed` property on each `QGroupBox`. Default: expanded (False). State does not persist across sessions.
- **Subcommand support:** Display groups work identically within subcommand argument sections.
- **No impact on existing behavior:** Command assembly (`build_command()`), preset serialization/deserialization (`serialize_values()` / `apply_values()` / `reset_to_defaults()`), mutual exclusivity groups, dependencies, and all existing widget types are completely unchanged.
- **New `ToolForm` attributes:**
  - `self.display_groups` — dict keyed by scope → `{display_group_name: QGroupBox}`
  - `_add_single_arg()` — extracted from `_add_args` loop body for reuse by both ungrouped and grouped code paths
  - `_toggle_display_group(box)` — toggles collapsed state and content visibility of a display group QGroupBox
- **PROMPT.txt updated:** Field count 15 → 16, `display_group` documented in the argument object spec, added to all example arguments, checklist updated.

### Changed
- Version bump to 2.4.0
- scaffold.py line count: 2,823 → 2,885
- Argument field count: 15 → 16 (`display_group` added)
- PROMPT.txt: argument object field count 15 → 16, example arguments updated with `display_group: null`

### Tested
- **Section 23** — Collapsible Argument Groups (24 assertions): QGroupBox creation with correct title, field containment (3 grouped fields inside box, 2 ungrouped fields outside), `_dg_content` property existence, initial expanded state, collapse toggle hides content, expand toggle restores content, `build_command()` output unchanged with grouped fields, preset serialization includes grouped field keys with correct values, `reset_to_defaults()` clears grouped fields, `apply_values()` restores grouped fields, `display_groups` dict populated with correct scope/name/QGroupBox references, subcommand schema creates separate display group QGroupBox with correct field containment

#### Test schemas added
- `tests/test_display_groups.json` — 5 arguments: 3 with `display_group: "Network"` (string, integer, enum types), 2 with `display_group: null` (boolean, file types)
- `tests/test_display_groups_subcmd.json` — subcommand schema with `display_group: "Scan Options"` on 2 of 3 subcommand arguments, plus 1 ungrouped global argument

#### Full suite results
- **All 4 test suites pass: 465/465 assertions, 0 failures**
  - Functional: 295/295 (+24 new in Section 23)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)
- All 9 tool schemas validate with zero errors
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new external dependencies

---

## [v2.3.1] — 2026-03-30

### Added

#### Tool Picker Search/Filter
- Search bar at the top of the tool picker with placeholder "Filter tools..."
- Filters by tool name, description, and path columns (case-insensitive)
- Clear button restores all rows; auto-focuses on picker display

#### Keyboard Navigation
- Enter/Return key opens the selected tool from the picker
- Tab order: search bar → table for natural keyboard flow
- Numpad Enter also supported

#### Enhanced Tooltips
- Tooltips now show flag, short_flag, type, separator mode, description, and validation regex
- Applied to both field labels and widgets
- Boolean fields hide separator; positional fields show placeholder name

#### Status Bar Improvements
- On tool load: shows field count and required count — `Loaded {tool} — {N} fields ({M} required)`
- During execution: elapsed timer ticks every second — `Running... (Ns)`
- On completion: elapsed time in exit message — `Exit 0 (N.1fs)` or `Process stopped (N.1fs)`

#### Exhaustive Preset Round-Trip Tests
- Section 18: all 9 widget types, edge cases (integer 0, float 0.0, empty multi_enum, paths with spaces), subcommand presets

### Changed
- Version bump to 2.3.1
- `time` added to stdlib imports (no new external dependencies)
- scaffold.py line count: 2,739 → 2,823
- Test files and test schemas now tracked in git (removed `test_*.py` from .gitignore)

### Tested
- **Section 19** — Search/Filter (11 assertions): bar existence, placeholder, name/description/case filtering, clear restore, no-match
- **Section 20** — Keyboard Navigation (6 assertions): Enter opens tool, no-selection safety, tab order, numpad Enter
- **Section 21** — Tooltip Flag Reference (11 assertions): flag, short_flag, type, validation, separator, positional, widget/label match
- **Section 22** — Status Bar Improvements (12 assertions): field counts, required counts, subcommand totals, timer attributes

#### Full suite results
- **All 4 test suites pass: 441/441 assertions, 0 failures**
  - Functional: 271/271 (+98 new)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new external dependencies

---

## [v2.3.0] — 2026-03-29

### External Code Review Inputs

Suggestions from multiple external code reviews (ChatGPT, GitHub Copilot) were triaged and distilled into six implementation phases. Each phase was completed in order, with the full test suite run after every change. Phases were ordered by risk: pure tests and validation first, data changes second, small code changes third.

**Implemented from ChatGPT review:**
- Validate `depends_on` references at schema load time, not during UI updates (Phase A)
- Runtime dependency audit in the GUI as defense-in-depth (Phase F)

**Implemented from combined review suggestions (ChatGPT + Copilot):**
- Comprehensive command assembly property tests (Phase B)
- Widget creation fallback for malformed arguments (Phase C)
- Preset schema versioning with hash-based mismatch detection (Phase E)
- Flagship schema polish with beginner-friendly descriptions and presets (Phase D)

**Declined or deferred:** Command preview coloring (too large for a minor release — requires replacing the preview widget, touching the theme system, and rewriting multiple existing tests).

---

### Added

#### Phase A — Dependency Validation at Schema Load Time

`validate_tool()` now checks that every `depends_on` reference points to an existing flag within the same scope (top-level arguments or within a single subcommand). Previously, a broken `depends_on` reference (e.g., `depends_on: "--nonexistent"`) was silently ignored at load time and only failed at runtime when the GUI tried to wire up the dependency.

- New `_check_dependencies()` validation helper, called for both top-level and per-subcommand argument lists — same pattern as `_check_duplicate_flags` and `_check_groups`
- Error message format: `{scope}: argument "{name}" depends on "{dep}" which does not exist in this scope`
- New test schemas: `tests/invalid_bad_dependency.json` (catches broken dep, exits 1) and `tests/valid_good_dependency.json` (passes validation)

#### Phase C — Widget Creation Fallback

`_build_widget()` is now wrapped in a try/except. If an unexpected argument configuration causes an exception during widget construction, the form no longer crashes — instead, a plain `QLineEdit` fallback is returned with a tooltip explaining the rendering failure. The error is logged to stderr for debugging.

- New `_build_widget_inner()` contains the original dispatch logic; `_build_widget()` is now the try/except wrapper
- Fallback widget marked with `_is_fallback = True` attribute so `get_field_value`, `_raw_field_value`, and `_set_field_value` treat it as a plain string regardless of the declared type
- One bad field does not break the rest of the form — fields before and after render normally
- This is defense-in-depth: `validate_tool()` still catches invalid types at load time; this catches edge cases that pass validation but fail rendering

#### Phase E — Preset Schema Versioning

Presets now include a `_schema_hash` field — an 8-character MD5 hash of the tool's argument flags at the time the preset was saved. When loading a preset against a schema that has changed (arguments added or removed), the status bar shows a non-blocking warning: *"Note: This preset was saved with a different schema version. Some fields may not have loaded."*

- New `schema_hash(data)` helper computes the hash from sorted flag names across all scopes (global + subcommands)
- `serialize_values()` now includes `_schema_hash` in every saved preset
- `_on_load_preset()` compares the saved hash to the current schema's hash; shows warning on mismatch
- **Backwards compatible** — old presets without `_schema_hash` load normally with no warning
- Existing behavior unchanged: missing fields get defaults, extra fields are silently skipped

#### Phase F — Runtime Dependency Audit (GUI)

Defense-in-depth layer for dependency wiring. After `_apply_dependencies()` fails to find a parent widget for a `depends_on` reference, it now logs a warning to stderr and leaves the dependent field enabled (fail-open) instead of silently skipping it.

- `_apply_dependencies()` now prints a warning to stderr when a parent widget is missing: `Warning: dependency wiring failed for "{name}" -- parent "{flag}" not found in form. Field left enabled (fail-open).`
- This is a startup-time check (runs once when the form is built), not a per-interaction check
- Complements Phase A's load-time validation — Phase A catches bad references in the schema, Phase F catches anything that slips through to the GUI

### Improved

#### Phase D — Flagship Schema Polish (nmap)

No code changes to scaffold.py. Purely data work on the nmap schema and presets.

- **Description rewrites** — all 111 argument descriptions in `tools/nmap.json` rewritten in plain English that a non-expert can understand. Key flags include beginner-friendly explanations of scan types, timing, port specification, OS detection, scripting, and output formats
- **Examples fields** — populated on key string fields:
  - `--script`: `["vuln", "safe", "default", "discovery", "auth", "brute", "http-title"]`
  - `-p`: `["80", "443", "1-1000", "1-65535", "22,80,443,8080"]`
  - `TARGET`: `["192.168.1.1", "192.168.1.0/24", "10.0.0.0/8", "scanme.nmap.org"]`
- **Three ready-to-use presets** in `presets/nmap/`:
  - `quick_ping_sweep.json` — discover live hosts: `-sn`, target `192.168.1.0/24`
  - `full_port_scan.json` — thorough scan: `-sS -p 1-65535 -sV -T4`, target `192.168.1.1`
  - `stealth_recon.json` — slow careful scan: `-sS -T2 -O --script=safe -oN results.txt`, target `192.168.1.1`

### Changed
- Version bump to 2.3.0
- `hashlib` added to stdlib imports (no new external dependencies)
- scaffold.py line count: 2,661 -> 2,739

### Tested

#### Phase B — Command Assembly Property Tests

New Section 14 in `test_functional.py` — 25 assertions testing `build_command()` directly with programmatically constructed tool dicts:

- **Separator tests** (6): `space` produces two list elements, `equals` produces one joined element, `none` concatenates flag+value, each with empty value excludes the flag entirely
- **Positional tests** (5): positionals appear at end, two positionals maintain schema order, spaces preserved as single element, positionals always after all flagged args
- **Repeatable tests** (3): unchecked excluded, count 1 produces one flag, count 3 produces three separate flags
- **Edge cases** (11): all empty produces just `[binary]`, shell metacharacters (`$`, `&`, `;`, `|`, backticks) pass through as literal strings, integer 0 included in command, extra flags appended at end with correct ordering, empty extra flags append nothing, unclosed quote in extra flags falls back without crash

#### New test sections (Phases C, E, F)

- **Section 15 — Widget Creation Fallback** (7 assertions): form renders despite bad field, broken enum falls back to QLineEdit with fallback tooltip, stderr warning logged, good fields before and after render correctly
- **Section 16 — Preset Schema Versioning** (11 assertions): hash is deterministic and 8 chars, serialize_values includes hash, matching hash produces no warning, adding/removing arguments changes hash, old presets without hash load normally (backwards compat), mismatch detection works
- **Section 17 — Runtime Dependency Audit** (9 assertions): valid deps produce no warnings with correct enable/disable behavior, broken deps (bypassing validator) produce stderr warning with fail-open behavior, adjacent fields unaffected

#### Full suite results

- **All 4 test suites pass: 343/343 assertions, 0 failures**
  - Functional: 173/173 (+52 new: 25 Phase B, 7 Phase C, 11 Phase E, 9 Phase F)
  - Examples: 52/52 (unchanged)
  - Manual Verification: 61/61 (unchanged)
  - Smoke: 57/57 (unchanged)
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new external dependencies

---

## [v2.2.0] — 2026-03-29

### Release

Public release of Scaffold. All changes from v2.1.0 and v2.1.1 are included.

### Changed
- Version bump to 2.2.0
- README disclaimer updated: assertion count corrected from 157 to 291

### Tested
- **Full pre-release audit passed** — all recent fixes verified (spinbox 0 vs unset, extra flags validation, coverage field, CLI entry points), visual/theme review, core pipeline, presets, final scan
- **All 4 test suites pass: 291/291 assertions, 0 failures**
  - Functional: 121/121
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
- No debug prints, no TODO/FIXME/HACK, no `shell=True`, no new dependencies

---

## [v2.1.1] — 2026-03-29

### External Code Review — MiniMax M2.7

The full Scaffold codebase (scaffold.py, PROMPT.txt, README.md, all 9 tool schemas, and both test suites) was submitted to **MiniMax M2.7** for an independent code review. The model evaluated the project across six categories — bugs, code quality, prompt design, documentation, feature requests, and testing gaps — and produced 27 discrete findings.

Each finding was triaged into one of four categories before implementation:
- **FIX NOW** — real bug or issue that affects users
- **FIX IF QUICK** — good improvement, worth doing if under ~10 lines changed
- **LATER** — good idea but not a v2.1.1 concern
- **SKIP** — over-engineering, already handled, or not applicable

**Triage result:** 3 fixed (BUG 1, BUG 3, P1), 7 deferred, 14 skipped, 3 new test sections added.

---

### Fixed

#### BUG 1 — Spinbox value 0 silently dropped from command (HIGH)

Integer and float fields with no schema default used 0 as both the "empty/unset" sentinel and as a valid user value. This caused flags like `-m 0` (hashcat MD5 mode), `--max-retries 0`, or `--rate 0.0` to be silently omitted from the assembled command. The bug affected five code paths:

- **`_build_widget`** — for integer/float fields without a default, the spinbox range now starts at -1 (integer) or -1.0 (float) instead of 0. The Qt `specialValueText(" ")` is set at this new minimum, making the spinbox appear blank when unset. Value 0 is now one step above the sentinel and is treated as a real user input.
- **`_is_field_active`** — previously returned `w.value() != 0`, which broke dependency chains (a child field depending on a spinbox parent would stay disabled when the parent was set to 0). Now checks `w.specialValueText() and w.value() == w.minimum()` — only the sentinel state is inactive. Spinboxes with defaults (no special value text) are always considered active.
- **`get_field_value`** — previously returned `None` when `arg["default"] is None and w.value() == 0`. Now returns `None` only when `w.specialValueText() and w.value() == w.minimum()`. This means 0 is included in the command, and the sentinel -1 is not.
- **`_raw_field_value`** — same fix as `get_field_value` (this method is used for preset serialization and ignores the widget's enabled state).
- **`_set_field_value`** — reset now sets the widget to `w.minimum()` (the sentinel) instead of hardcoded 0, so "Reset to Defaults" correctly returns the field to the unset state.

Boundary behavior after the fix:
| Widget state | `get_field_value` | In command? | Dependency children |
|---|---|---|---|
| Unset (sentinel, -1) | `None` | No | Disabled |
| Set to 0 | `0` | Yes (`-m 0`) | Enabled |
| Set to 5 | `5` | Yes (`-m 5`) | Enabled |
| Has default, set to 0 | `0` | Yes | Enabled |
| Has default, set to -5 | `-5` | Yes | Enabled |

#### BUG 3 — No visual feedback on invalid Additional Flags input (MEDIUM)

The Additional Flags free-text field uses `shlex.split()` to tokenize user input. When the input contains unclosed quotes (e.g., `--flag "unclosed`), `shlex.split()` raises `ValueError` and the code silently falls back to naive `text.split()`. The user had no indication that their input was malformed.

Added `_validate_extra_flags()` method to `ToolForm`, connected to the `textChanged` signal of the extra flags editor. On every keystroke:
- If the field is empty: clear any error styling
- If `shlex.split()` succeeds: clear any error styling
- If `shlex.split()` raises `ValueError`: apply a red border via `_invalid_style()`

The border color is theme-aware — uses `#f38ba8` (Catppuccin error pink) in dark mode and `red` in light mode, matching the existing validation border style used by regex-validated string fields.

The fallback to `text.split()` is preserved — the command still runs with naively-split tokens if the user clicks Run with invalid quotes. The red border serves as a warning, not a blocker.

#### P1 — PROMPT.txt Rule 8 completeness directive (MEDIUM)

Rule 8 originally read: *"Include ALL documented flags. For tools with 100+ flags, focus on the 30-50 most common."* This contradicted itself within one sentence and also conflicted with Rule 9 (*"Only include flags from the provided documentation. Do not invent flags."*).

Updated Rule 8 to: *"Include ALL documented flags, regardless of how many there are. If output is truncated, the user will re-prompt to continue."*

This aligns with the project's goal of complete CLI coverage — if an LLM truncates output mid-JSON on a very large tool, `scaffold.py --validate` catches the broken output and the user can ask the LLM to continue where it left off.

#### PROMPT.txt Checklist item 8 — duplicate flag scoping (LOW)

The no-duplicates checklist rule previously read: *"No duplicate entries for the same flag."* This was ambiguous — it could be read as a global constraint, causing LLMs to deduplicate flags like `--verbose` that legitimately appear in multiple subcommands. Updated to: *"No duplicate flags within the same scope (top-level arguments or a single subcommand). The same flag MAY appear in multiple subcommands."*

This matches how Scaffold's `_check_duplicate_flags()` validator already works — it validates per-scope, not globally.

#### PROMPT.txt Coverage self-check section (NEW)

Added a new `=== COVERAGE SELF-CHECK ===` section after the checklist. Instructs the LLM to count arguments in its output, compare to the source documentation, and include a top-level `_coverage` field with value `"full"` or `"partial: [list of omitted flags]"`. This provides a machine-readable way to verify completeness and catches silent truncation.

The `_coverage` field is silently accepted by `validate_tool()` — no code changes needed. Schemas without it (pre-update) continue to pass validation.

---

### Regenerated Schemas

Three tool schemas were regenerated using the updated PROMPT.txt with full-coverage and self-check directives. The old schemas were generated under the previous Rule 8 which capped output at "30-50 most common" flags. The new schemas include all documented flags.

| Schema | Before | After | `_coverage` |
|--------|--------|-------|-------------|
| **nmap.json** | 34 args | 111 args | `full` |
| **curl.json** | 50 args | 271 args | `partial` (3 meta flags skipped: --help, --manual, --version) |
| **hashcat.json** | 46 args | 136 args | `full` |

Schemas not regenerated (already comprehensive): gobuster (103 args), ffmpegv2 (123 args), openclaw (213 args), nikto (48 args), ping (19 args), git (76 args across 4 subcommands — regeneration deferred to a future release that adds more subcommands).

All 9 schemas pass `scaffold.py --validate` with zero errors.

---

### Tested

Four test suites now cover the codebase. **Total: 291 assertions, 0 failures.**

#### Functional test suite — 121/121 pass (+16 new vs v2.1.0)

New Section 12 — **Spinbox Value 0 (BUG 1 regression)**:
- Integer with no default: initially returns `None`, not in command
- Integer with no default set to 0: returns `0`, flag appears as `-m 0` in command
- Integer with no default set to 5: returns `5`
- Float with no default: initially returns `None`
- Float with no default set to 0.0: returns `0.0`, flag appears in command
- Integer with default set to 0: returns `0` (no sentinel interference)
- `_is_field_active` returns `False` at sentinel, `True` at 0

New Section 13 — **Extra Flags Validation (BUG 3 regression)**:
- Valid input: no error border
- Unclosed quote: red error border appears
- Cleared field: error border removed

Note: functional test count increased from 118 to 121 because the regenerated nmap schema (111 args) adds additional tool picker rows, each of which is individually asserted.

#### Examples feature test suite — 52/52 pass (unchanged)

No changes to the examples feature. All existing tests continue to pass — schema normalization, validation rules, editable dropdowns, command assembly, preset round-trips, dependency interaction with examples fields, and validation on examples fields.

#### Manual verification test suite — 61/61 pass (NEW)

`test_manual_verification.py` — exercises edge cases that functional tests don't cover: visual behavior, command execution pipeline, preset persistence across sessions, elevation wrapping, dark mode styling, and boundary conditions.

**Test A — Spinbox Value 0 (10 test groups, 38 assertions):**
- A1: Zero appears in command preview (`-m 0` visible in preview text)
- A2: Zero and unset produce genuinely different commands (CRITICAL — the two states must never collapse into the same output)
- A3: Zero survives full preset round-trip: set to 0 -> serialize -> reset to defaults (confirms unset) -> load preset (confirms 0 restored) -> close app -> reopen -> load preset from disk (confirms 0 persists across sessions)
- A4: Zero persists through elevation wrapping (`gsudo echo -m 0` or `pkexec echo -m 0`)
- A5: Float 0.0 — same unset/zero distinction as integer, `--rate 0.0` in command and preview
- A6: Sentinel boundary — confirms -1 is unset, 0 is valid, integers with defaults have no sentinel (full range including negatives), dependency children enable at 0 and disable at sentinel

**Test B — Extra Flags Validation (8 test groups, 23 assertions):**
- B1: Valid input baseline — no border, flags in command and preview
- B2: Unclosed single quote — red border appears, closing quote clears it, flags parse correctly after fix
- B3: Unclosed double quote — same behavior as B2
- B4: Run with unclosed quote — command builds without crash, fallback split produces tokens, red border stays visible
- B5: Red border clears when field is emptied
- B6: Red border clears immediately when input becomes valid (closing a quote)
- B7: Dark mode — error border uses theme color `#f38ba8`, not hardcoded `red`; clears correctly in dark mode
- B8: Corrupted preset (manually edited `_extra_flags` with unclosed quote) — loads without crash, red border fires, rest of preset applies normally

#### Smoke test suite — 57/57 pass (NEW)

`test_smoke.py` — pre-deploy sanity check covering the full user workflow:
- Section 1 — Launch and load: tool picker renders all 9 tools, form loads with all fields, light/dark mode toggle, widget styling in both themes
- Section 2 — Form and preview: checkbox, dropdown, text input, positional field all respond to input; live preview updates; copy command works
- Section 3 — Run a command: process starts, output streams, command echo visible, exit code colored, run button state transitions
- Section 4 — Preset round-trip: save -> reset (fields clear) -> load (fields restore) -> command preview matches
- Section 5 — Window behavior: small/large resize, geometry persists across sessions, theme preference persists

---

### Deferred (LATER)

Items from the MiniMax M2.7 review that are valid improvements but not v2.1.1 scope:

- **BUG 5 — Tool picker search/filter** — with many tools, the table is hard to navigate. Add a QLineEdit filter bar. Good for v2.2.
- **R2 — README troubleshooting section** — consolidate scattered platform notes (PySide6 install, xcb-cursor0, validation errors) into one section.
- **P3 — Stdin/stdout sentinel guidance in PROMPT.txt** — tools like `ffmpeg -o -` use `-` as a special value. Niche but worth a one-line note.
- **T2 — Exhaustive preset round-trip tests** — current preset tests don't cover every widget type. Medium effort.
- **F1-F5 — Feature requests** — environment variable expansion, command history, dry-run mode, schema wizard, keyboard navigation in tool picker. All good ideas, all out of scope for a bugfix release.

### Skipped

Items from the MiniMax M2.7 review that were evaluated and intentionally not implemented:

- **BUG 2** (repeat count on unchecked boolean) — design decision: unchecked = inactive = not saved. The repeat count is a sub-property of an inactive flag.
- **BUG 4** (tool picker re-scans on back navigation) — scan performance was verified in v1.4.0 Part 3 review with 20+ schemas. Not worth caching complexity.
- **BUG 6** (Qt < 6.8 scrollbar degradation) — already handled with `try/except AttributeError` and documented in code comments and changelog.
- **CQ 1** (DARK_COLORS as dataclass) — works fine as a dict. No typo-related bugs have occurred.
- **CQ 2** (_apply_widget_theme hasattr checks) — works, not buggy, refactoring would add complexity for no functional gain.
- **CQ 3** (extract sub-methods from long methods) — constraint: don't refactor working code just to make it "cleaner."
- **CQ 4** (__slots__ on widget subclasses) — negligible memory impact for a desktop app with a handful of widget instances.
- **CQ 5** (normalize isinstance checks) — cosmetic inconsistency, no behavioral impact.
- **P2** (flag alias guidance) — already covered by Rule 10 ("Short + long forms = ONE entry") and the argument object spec ("Use the LONG form when available").
- **P4** (elevated field description too brief) — the field spec already has concrete descriptions; Rule 6 adds examples (`nmap SYN scan`, `iptables`).
- **P5** (version-gated flags) — already covered by Rule 11 ("If docs mention version requirements, note them").
- **R1** (disclaimer mentions OpenClaw by name) — OpenClaw is a shipped example schema, not a third-party reference. The concrete example is more useful than a generic statement.
- **R3** (no comparison with similar tools) — marketing concern, not a code issue.
- **R4** (screenshots load slowly from GitHub) — cosmetic concern about image hosting.

## [v2.1.0] — 2026-03-29

### Added
- **OpenClaw tool schema** (`tools/openclaw.json`) — AI agent platform with 10+ subcommands including gateway, channels, models, browser automation, and node management
- **Gateway `--restart` flag** — added missing `--restart` boolean to the openclaw gateway subcommand
- **Linux install troubleshooting** — README note covering `--break-system-packages` workaround and `libxcb-cursor0` dependency for Ubuntu/Debian users
- **Crypto donation addresses** — updated Support section with BTC, LTC, ETH, BCH, and SOL addresses

### Fixed
- **Dark mode scrollbars now match light mode exactly** — replaced custom QSS scrollbar styling with `QStyleHints.setColorScheme(Qt.ColorScheme.Dark)`, which tells the Windows platform plugin to render scrollbars using the native dark-mode renderer. This preserves all native behavior — smooth animations, expand-on-hover, arrow buttons appearing — with dark colors, because the exact same native renderer draws both modes. Previous QSS and QProxyStyle approaches could not replicate native behavior because QSS bypasses the native renderer entirely and the Windows theme API ignores QPalette for scrollbar painting. Gracefully falls back on Qt < 6.8.

### Improved
- **Side-by-side screenshots** in README — nmap and hashcat examples displayed at 48% width
- **README updates** — line-count badge updated to 2,646; assertion count updated to 157; openclaw added to example schemas table

### Tested
- **Functional test suite**: 105/105 assertions pass
- **Examples feature test suite**: 52/52 assertions pass
- **Scrollbar visual parity**: dark mode scrollbars confirmed identical to light mode (size, animation, hover expansion, arrow buttons) on Windows 11 with PySide6 6.11.0

## [v2.0.1] — 2026-03-29

### Fixed
- **README assertion count** — second mention in "About This Project" section still said 661; corrected to 156

## [v2.0.0] — 2026-03-29

### Added
- **`__version__` constant** (`2.0.0`) and `--version` / `-V` CLI flag for bug reports and preset compatibility
- **Shebang line** (`#!/usr/bin/env python3`) for direct execution on Unix (`./scaffold.py`)
- **Minimum Python version** documented in module docstring (`3.10`)
- **Resizable output panel** — drag handle between command controls and output panel
  - Custom `DragHandle` widget with two-line grip indicator and vertical resize cursor
  - Drag up to shrink, drag down to grow (80px–800px range)
  - Panel height persisted across sessions via QSettings
- **Command options border** — form area wrapped in a rounded `QFrame` with a subtle border to visually distinguish it from the preview and output sections below
- **Separator line** between tool header and command options for cleaner visual hierarchy
- **UI polish** — section labels, separator lines, and colored action button
  - Centered, uppercase "Command Preview" and "Output" section labels with theme-aware styling
  - Subtle horizontal separator lines before each section for visual clarity
  - Run button styled green; switches to red when in "Stop" state
  - All new elements update correctly on light/dark theme toggle
- New example tool schemas: `nikto.json`, `gobuster.json`, `hashcat.json`, `ffmpegv2.json`
  - nikto: demonstrates string+examples for code-concatenation flags (-Tuning, -Display, -evasion)
  - gobuster: demonstrates full subcommand architecture (7 modes with scoped flags)
  - hashcat: demonstrates examples-vs-enum distinction (-m as string vs -a as enum)
  - ffmpegv2: demonstrates large schema with 123 arguments across encoding, filtering, and I/O
- New screenshot: `hashcat example.png`
- Validation feedback tip in README — paste errors back into LLM to self-correct

### Improved
- **Tighter vertical spacing** — reduced padding on section labels, status bar, action bar, and command preview to reclaim screen space for tools with many arguments
- **Higher contrast light theme** — borders for form frame, separators, and drag handle darkened from `#d0d0d0`/`#aaaaaa` to `#999999`/`#888888` for better visibility
- **`--help` output** now includes version number and `--version` flag; replaced em dash with ASCII dash to avoid encoding issues on Windows cp1252 terminals
- **Updated nmap screenshot** — reflects new UI (form border, section labels, drag handle, colored Run button); optimized from 445 KB to 114 KB
- **README updates** — line-count badge updated to 2,634; assertion count corrected to 156; nikto, gobuster, hashcat added to example schemas table
- **PROMPT.txt rewrite** — 5-stage review, test, iterate, harden, slim
  - Added complete example JSON (5 arguments demonstrating all key patterns)
  - Added type hallucination guard table with wrong→correct name mappings
  - Added JSON formatting rules (no comments, no trailing commas, null not "")
  - Added completeness + accuracy rules (don't truncate, don't invent flags)
  - Added no-duplicates rule (short+long forms = one entry, aliases merged)
  - Strengthened positional placement rule (MUST be last in array)
  - Clarified flag vs short_flag convention (long form in flag, short in short_flag)
  - Expanded separator detection guidance (look for "=" in docs)
  - Added unclear/incomplete docs handling ("inferred — verify" annotation, version notes)
  - Added examples-vs-enum "why" explanation to prevent silent misclassification
  - Collapsed self-check into compact 9-item checklist
  - Compressed prompt to ~1,039 words while preserving all rules

### Fixed
- **QPushButton stylesheet parse error** — added missing whitespace between QSS rule blocks in Run/Stop button styling (both dark and light mode)
- **`nmap.json` `-sC` mislabeled as `short_flag` of `--script`** — `-sC` is a distinct flag (`--script=default`), not the short form of `--script`. Split into separate "Default Scripts" boolean entry

### Tested
- **Full pre-release audit** (9 sections): first impressions, dependencies, cross-platform, security, error handling, UI polish, file deliverables, CLI interface, final sanity
- **Security audit passed** — no `shell=True`, no `eval()`/`exec()`, binary passed as single string to `QProcess.setProgram()`, extra flags use `shlex.split()`, JSON loaded with `json.loads()` in try/except, no secrets in QSettings
- **Cross-platform audit passed** — all paths use `pathlib.Path`, elevation gated by `sys.platform`, `shutil.which()` for binary detection, `QSettings("Scaffold", "Scaffold")`
- **CLI entry points verified** — `--help`, `--version`, `--validate`, `--prompt`, direct path, missing file, invalid file all produce clean output with correct exit codes and no tracebacks
- **Functional test suite**: 104/104 assertions pass (tool picker, all 9 widget types, tooltips, required fields, defaults, mutual exclusivity, dependencies, extra flags, command preview, process execution, stop, dark mode, presets, session persistence, subcommands, editable dropdowns, file/directory widgets, output batching, file size guard)
- **Examples feature test suite**: 52/52 assertions pass (schema normalization, validation rules, editable dropdowns, command assembly)
- **Schema conformance check**: all 8 bundled tool schemas (nmap, ping, git, curl, nikto, gobuster, hashcat, ffmpegv2) pass PROMPT.txt 15-field spec with all top-level keys present; original 4 schemas audited against new prompt conventions (flag/short_flag, no duplicates, positionals last, boolean separators)
- Prompt validated against 6 CLI tools across 3 complexity levels (ping, nmap, curl, nikto, gobuster, hashcat)
- All generated schemas pass `scaffold.py --validate` with zero structural errors
- Cross-model testing: Opus 4.6 (zero failures) and Haiku 4.5 (structural pass, semantic improvements from guardrails)
- `--prompt` output verified on Windows (cp1252 encoding handled correctly)

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
