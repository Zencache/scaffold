# Changelog

All notable changes to Scaffold are documented here.

## [v2.8.0] — 2026-04-07

Cascade chaining, LLM-powered preset generation, license change, and a broad hardening pass across validation, security, output handling, and UI consistency.

### Added

- **Cascade panel** — a new right-side dock panel (`Ctrl+G`) for chaining multiple tool runs into sequential workflows. Each cascade holds up to 20 numbered slots, each assignable to a tool and optional preset. Per-step delays (0–3600 s), loop mode (repeat the full chain indefinitely), and stop-on-error mode (halt on non-zero exit). Cascades use the same QProcess execution pipeline as regular runs — no shortcuts, same security model (`CascadeSidebar`).
- **Cascade file management** — save, load, import, export, and delete named cascade files. Cascade state (slots, loop mode, stop-on-error, variables, name) persists across sessions via QSettings (`_on_save_cascade_file`, `CascadeListDialog`, `_on_import_cascade`, `_on_export_cascade`).
- **Cascade variables** — define named variables with a type hint (`string`, `file`, `directory`, `integer`, `float`) and an apply-to scope (all steps or specific slot indices). Before each chain run, a dialog prompts for values; those values are injected into form fields across steps at run time (`CascadeVariableDialog`, `CascadeVariableDefinitionDialog`).
- **Example cascade files** — `cascades/nmap_recon_chain.json` (ping sweep → full port scan → stealth recon), `cascades/curl_api_chain.json` (health check → GET → POST), `cascades/aircrack_capture_chain.json` (interface scan → capture → key analysis).
- **LLM-powered preset generation** — new `--preset-prompt` CLI flag prints the contents of `PRESET_PROMPT.txt` to stdout. Workflow: paste the prompt alongside a tool schema into an LLM, describe the preset you want, paste the returned JSON into `presets/<tool>/` (`print_preset_prompt`).
- **Password masking in command preview and output** — password-type field values are replaced with `********` in the command preview widget, the run line printed to the output panel, and in history entries (`_mask_passwords_for_display`).
- **Preset save overwrite warning** — saving a preset whose filename already exists now asks for confirmation and pre-fills the description field from the existing preset (`_on_save_preset`).
- **Preset picker filter bar** — a live text filter at the top of the preset picker dialog with Enter/Shift+Enter cycling through matches (`PresetPicker`).
- **Tool picker keyboard navigation** — Enter in the tool picker filter bar now selects the next matching row; Shift+Enter goes to the previous (`ToolPicker`).
- **Field search matches descriptions** — `Ctrl+F` field search now matches against the argument's `description` text in addition to name and flag (`ToolForm._on_search`).
- **50 MB output buffer cap** — when buffered output exceeds 50 MB, oldest entries are dropped and a truncation notice is prepended to the buffer (`_append_to_buffer`, `OUTPUT_BUFFER_MAX_BYTES`).
- **Extra flags validation** — unmatched quotes in the Extra Flags box now disable the Run button and show an error status, instead of silently falling back to `text.split()` (`extra_flags_valid`, `_update_preview`).
- **Docker tool schemas** — `tools/docker_test/docker.json`, `tools/docker_test/docker-buildx.json`, `tools/docker_test/docker-compose.json`.
- **Cascade file drag rejection** — dragging a `.json` file with `_format: scaffold_cascade` onto the app now shows a clear dialog instead of silently failing (`_load_tool_path_from_data`).

### Changed

- **License changed from MIT to PolyForm Noncommercial 1.0.0** — free for personal and noncommercial use; commercial use requires a separate license.
- **Ping schema elevation** — `tools/ping.json` now declares `elevated: "optional"` instead of `null`.
- **Tooltip HTML escaping** — all user-supplied strings (flag, short_flag, description, validation, arg name, binary name, preset description) are now passed through `html.escape()` before injection into tooltip HTML, preventing rendering glitches from `<`, `>`, `&` in field content (`_build_tooltip`, `_add_form_row`).
- **Light-theme tooltip colors forced** — switching to light mode now explicitly sets tooltip background/foreground colors, preventing unreadable tooltips on Linux mixed-theme desktops (`apply_theme`).
- **Command preview: negative numbers** — tokens like `-1` or `-3.5` are now colored as values rather than flags in the preview (`_colored_preview_html`).
- **PowerShell and CMD copy formatting hardened** — both formatters now use a safe-character whitelist and strip literal newlines before quoting. PS escaping uses `''` (correct PS syntax); CMD escaping uses `""` (`_format_powershell`, `_format_cmd`).
- **Label decorations update on theme change** — `dangerous` (red warning prefix) and `deprecated` (strikethrough + amber suffix) labels now rebuild correctly when toggling themes (`ToolForm.update_theme`).
- **Process teardown centralized** — a dedicated `_teardown_process` method disconnects all signals before killing the process, preventing orphaned QProcess callbacks into destroyed UI state (`_teardown_process`).
- **Force kill uses `os.kill` instead of `os.killpg`** — avoids `ProcessLookupError` on macOS/Linux when the process group has already exited (`_on_force_kill`).
- **Arrow icon temp directory cleaned up on exit** — `atexit.register` deletes the temp `scaffold_arrows_*` directory when the process exits (`_cleanup_arrow_dir`).
- **Dependency changes emit `command_changed`** — toggling a parent field now updates the command preview for dependent child fields (`_on_dependency_changed`).

### Fixed

- **Duplicate flag values within a scope not detected** — `--validate` now catches two arguments sharing the same `--flag` or `-x` short flag value (`_check_duplicate_flag_values`).
- **Non-string `flag` field crashes validator** — if `flag` is an integer or other non-string type in JSON, a clear error is now reported instead of a crash (`_validate_args`).
- **Flag leading/trailing whitespace bypasses duplicate detection** — flags with whitespace are now rejected by the validator; `normalize_tool` strips them silently (`_validate_args`, `normalize_tool`).
- **Subcommand names with control characters or shell metacharacters accepted** — subcommand names containing `\n`, `\r`, `\t`, or shell metacharacters now fail validation (`validate_tool`).
- **`schema_hash` crashes on non-string flags or non-dict subcommands** — added `isinstance` guards (`schema_hash`).
- **`validate_tool` crashes on non-dict input** — now returns a clear error if passed a JSON array or other non-dict type (`validate_tool`).
- **Non-numeric preset values crash integer/float fields** — `_set_field_value` now wraps `int()`/`float()` in try/except, silently skipping invalid values instead of crashing (`_set_field_value`).
- **Extra flags tooltip truncated on some platforms** — wrapped tooltip text in `<p>` tags for consistent rendering (`extra_flags_edit`).
- **Clearing output did not flush pending buffer** — `_clear_output` now also clears `_output_buffer`, preventing buffered text from reappearing on the next flush cycle (`_clear_output`).
- **Stdout/stderr handlers crash when process is None** — both handlers now guard against `self.process is None` during cascade step transitions (`_on_stdout_ready`, `_on_stderr_ready`).
- **Recovery dialog shown during cascade chain loading** — suppressed when a cascade chain is loading the next step (`_check_for_recovery`).
- **Spinbox button misalignment in dark mode** — up/down buttons now use explicit `subcontrol-origin: border` with correct positions (`apply_theme`).
- **Warning bar missing rounded corners** — added `border-radius: 4px` to the warning bar in both themes (`_set_warning_bar_style`).

#### Full suite results

- **All 6 test suites pass: 1,799/1,799 assertions, 0 failures**
  - Functional: 1,437/1,437
  - Security: 158/158
  - Smoke: 68/68
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.7.8] — 2026-04-04

Collapsible folder groups in the tool picker and run button sizing fix.

### Added

- **Collapsible folder groups** — tools in subfolders now appear at the top of the tool picker in collapsible groups. Click the folder header to expand or collapse its tools. Arrow indicators show the current state.

### Changed

- **Folder sort order** — subfolder groups are now pinned above root-level tools in the tool picker, sorted alphabetically.
- **Ansible schemas moved to subfolder** — the four ansible tool schemas now live in `tools/ansible/` to demonstrate the subfolder grouping feature.

### Fixed

- **Run button overlapping Clear Output** — the minimum width calculation now measures with a bold font to match the stylesheet, preventing the button text from clipping into adjacent buttons.

## [v2.7.7] — 2026-04-04

Dark mode clipping fixes and output toolbar spacing improvements.

### Fixed

- **Checkable group box title clipped in dark mode** — the checkbox and label text were rendered 1px above the widget boundary, cutting off the top row of pixels. Added top padding to the title sub-control to push it fully inside the visible area.
- **Run button text clipped when showing "Stopping..."** — the minimum width calculation now accounts for button padding, so the full label is always visible.
- **Timeout controls crowding into action buttons** — replaced the collapsible stretch with an expanding spacer that enforces a minimum 16px gap between the output buttons and the timeout controls.
- **Save Output button label** — removed the trailing ellipsis for consistency with the other action buttons.
- **Dark mode spinbox height** — reduced internal padding so spinboxes more closely match their native light mode height.

## [v2.7.6] — 2026-04-04

Copy format dropdown, output search bar auto-visibility, and tooltip spacing polish.

### Added

- **Copy format dropdown** — the Copy button now has a dropdown menu letting you choose between Bash, PowerShell, CMD, and Generic output formats. Your selection is remembered across sessions. The button label updates to show the active format (e.g., "Copy (Bash)").
- **Output search bar auto-visibility** — the search bar above the output panel now appears automatically when output is present and hides when the output is cleared, so it's always available when you need it.

### Changed

- **Tooltip spacing improved** — added a blank line between the flag/type header (e.g., `--branch -b (string)`) and the description text in field tooltips, making the two sections visually distinct.
- **Output action buttons use smaller font** — the Clear, Copy Output, and Save Output buttons now use 8pt text to reduce visual weight in the output toolbar.
- **Minimum window width increased** — raised from 500px to 530px to prevent the copy button dropdown from clipping.

### Tests

- Updated Section 27m to match new search bar visibility behavior (bar stays visible when output has content).
- Added Section 59 (23 assertions) covering copy format dropdown mechanics, QSettings persistence, button label updates, menu structure, and output search bar visibility lifecycle.
- Updated Section 5a minimum width assertion to match new 530px minimum.

#### Full suite results

- **All 6 test suites pass: 1,194/1,194 assertions, 0 failures**
  - Functional: 864/864
  - Security: 131/131
  - Smoke: 63/63
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.7.5] — 2026-04-04

Dark mode visual consistency, display group UX improvements, subcommand preview fix, and password serialization security hardening.

### Security

- **Password fields excluded from all serialization** — `serialize_values()` now skips fields with `type: "password"`, preventing secrets from being written to presets, crash recovery files, or command history. *(Suggested by Dan — thank you!)*
- **Recovery file permissions hardened** — `_autosave_form()` now calls `os.chmod(path, 0o600)` after writing recovery files, restricting access to the file owner on Linux/macOS. Wrapped in try/except for Windows compatibility.

### Fixed

- **Subcommand tokens swallowed in command preview** — `_colored_preview_html()` greedy flag-value lookahead was consuming subcommand tokens (e.g., `deploy` after `--flag`), making them invisible in the preview. Added a guard to skip pending subcommand parts.
- **Dark mode visual inconsistency** — added `border-radius: 3px` to all 9 QSS selectors that set `border` (QMenu, QCheckBox::indicator, QComboBox, QComboBox dropdown, QSpinBox/QDoubleSpinBox, QLineEdit, QListWidget, QPushButton, QPlainTextEdit, QToolTip). Added padding compensation to prevent height shrinkage: `3px` for QLineEdit, `3px 4px` for QComboBox, `1px 2px` for spinboxes, `4px 0` for QCheckBox, `1px` for QPlainTextEdit.
- **QGroupBox title position in dark mode** — added `subcontrol-origin: margin`, `padding: 0 4px`, `left: 8px` to `QGroupBox::title`, and `border-radius: 4px`, `margin-top: 14px`, `padding-top: 4px` to `QGroupBox` so titles render identically in both themes.
- **Display group collapse indicator missing** — group box titles now show ▾ (expanded) and ▸ (collapsed) indicators that update on toggle.
- **Display group clicks not reaching nested widgets** — replaced `mousePressEvent` lambda override with `installEventFilter()` pattern, which correctly dispatches events to child widgets inside collapsed/expanded groups.

### Changed

- **Gobuster schema restructured** — moved 12 global flags into all 7 subcommands to match gobuster v3.8.2's urfave/cli requirement that flags follow the subcommand token.

### Tests

- Updated Section 23 display group lookups to use `property("_dg_name")` instead of `title()` (title now includes ▾/▸ prefix).
- Updated Section 38f: password fields now verified as *excluded* from serialization (was *included*). Added 38f2 (mixed form serialization) and 38f3 (apply_values with missing password key).
- Added Section 46y (recovery file excludes password fields) and 46z (recovery file permissions on Linux).

#### Full suite results

- **All 6 test suites pass: 1,171/1,171 assertions, 0 failures**
  - Functional: 841/841
  - Security: 131/131
  - Smoke: 63/63
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.7.4] — 2026-04-03

Security audit, dedicated security test suite, deep audit bugfixes, and button clipping fix. The full updated codebase — after code audits by MiniMax M2.7, GitHub Copilot, and ChatGPT — was distilled back into Claude 4.6 Opus Extended Thinking, which found all of the bugs fixed in this release.

### Added

- **Security audit test suite (`test_security.py`)** — 131 focused security assertions across 8 sections: static analysis for forbidden patterns, shell metacharacter passthrough verification for all widget types, binary validation hardening, preset injection resistance, extra flags injection resistance, preset name path traversal, recovery file safety, and QProcess contract verification.

### Fixed

- **Recovery file crash on non-dict JSON** — `_check_for_recovery()` now validates that parsed recovery data is a dict before calling `.get()`, preventing an `AttributeError` when the file contains valid JSON that isn't a dict (e.g., a list).
- **Button text clipping during process execution** — the Run button now has a font-metrics-based minimum width calculated from its widest state ("Stopping..."), preventing layout reflow when cycling through Run/Stop/Stopping. All action bar and preview bar buttons use `QSizePolicy.Minimum` so they never shrink below their text content.
- **`_SHELL_METACHAR` recreated on every call** — moved from a local `set()` inside `validate_tool()` to a module-level `frozenset` constant.
- **Null bytes pass binary validation** — added `\x00` to `_SHELL_METACHAR` and a dedicated "contains null bytes" error message.
- **Recovery file collisions on shared systems** — added a per-user identifier to recovery filenames.
- **Underscore-prefixed flags collide with preset metadata** — `_validate_args()` now rejects flags starting with `_`.

### Security

The security model (no shell, no eval/exec, no network, typed constraints) was audited by a penetration tester and validated across multiple LLM-assisted review stages — including multi-model code review, targeted fuzzing of the command builder, and the new automated security test suite.

#### Full suite results

- **All 6 test suites pass: 1,167/1,167 assertions, 0 failures**
  - Functional: 837/837
  - Security: 131/131
  - Smoke: 63/63
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.7.3] — 2026-04-03

UI spacing polish and reset-confirmation fix. Security model audited using multi-LLM code review, manual code review, and assessment by a trained penetration tester.

### Changed

- **Command preview section grouped into a single layout** — the "Command Preview" label, preview bar, and status label are now wrapped in a dedicated `QVBoxLayout` with 5px internal spacing and zero margins, tightening all gaps in the preview area.
- **Preview label padding zeroed** — `preview_label` top/bottom padding overridden to 0px (scoped to preview only, not output label). Theme toggle re-applies the override to prevent resets.
- **Button spacing in preview bar** — added 12px vertical spacing between "Reset to Defaults" and "Copy Command" buttons to prevent accidental mis-clicks.

### Fixed

- **Reset confirmation used a permanent hidden widget** — replaced the dedicated `reset_status` QLabel (which consumed 16px of dead space even when empty) with a deferred `QTimer.singleShot(0)` call to `_show_status`, reusing the existing status label. The deferred write survives the `_update_preview` signal cascade triggered by `reset_to_defaults()`.

#### Full suite results

- **All 5 test suites pass: 1,036/1,036 assertions, 0 failures**
  - Functional: 837/837
  - Smoke: 63/63
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.7.2] — 2026-04-02

Bugfixes and UI improvements informed by a full deep code audit and hands-on user testing with a MiniMax M2.7 OpenClaw agent.

### Changed

- **"Reset to Defaults" moved to command preview area** — relocated from the Presets menu to a dedicated button stacked vertically above "Copy Command" in the preview bar. Disabled when no tool is loaded.


### Fixed

- **Drag-drop case sensitivity** — `dragEnterEvent` and `dropEvent` now use case-insensitive matching for `.json` extensions. Files named `tool.JSON` or `tool.Json` are no longer silently rejected.
- **Missing `_format` on bundled schemas** — added `"_format": "scaffold_schema"` as the first key in `git.json`, `nmap.json`, `ping.json`, and `curl.json`. These four schemas were missing the marker that identifies them as Scaffold schemas.
- **Reset status message not auto-clearing** — replaced `statusBar().showMessage()` with a dedicated `reset_status` label that auto-clears after 3 seconds via `QTimer.singleShot`.
- **Minimum window width increased to 500px** — raised from 420px to accommodate the new button layout.

### Added

- **aircrack-ng tool schema (testing)** — added `tools/aircrack-ng.json`. Mostly untested and may not cover every flag or edge case — contributions and bug reports welcome.


#### Full suite results

- **All 5 test suites pass: 1,036/1,036 assertions, 0 failures**
  - Functional: 837/837
  - Smoke: 63/63
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.7.1] — 2026-04-02

Hardening pass — four targeted fixes distilled from a full deep code audit with Copilot. Started with a comprehensive audit, iterated on the findings, and narrowed down to these surgical improvements.

### Fixed

- **BOM stripping in `load_tool`** — strip a leading UTF-8 BOM (`\ufeff`) before JSON parsing. Windows editors (especially Notepad) insert this character, which caused a cryptic `JSONDecodeError`.
- **QApplication guard in `_make_arrow_icons`** — return early with an empty string if no `QApplication` instance exists, preventing a crash when the function is called before the app is created (e.g., during test imports).
- **`normalize_tool` deep copy** — the function now returns a deep copy of the normalized data, so callers get an independent snapshot and won't see unexpected mutations through shared references. All internal and test call sites updated to use the return value; `ToolForm.__init__` now normalizes its own input defensively.
- **Flag stripping in `_check_duplicate_flags`** — trailing whitespace in hand-edited schema flag values (e.g., `"--port "` vs `"--port"`) no longer bypasses duplicate detection.

#### Full suite results

- **All 5 test suites pass: 1,034/1,034 assertions, 0 failures**
  - Functional: 836/836
  - Smoke: 62/62
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.7.0] — 2026-04-02

### Changed


- **Moved "Command History..." from Presets menu to View menu** — history is now under View > Command History (Ctrl+H), separated from preset management. The action is explicitly enabled/disabled based on whether a tool is loaded.
- **Renamed Cancel/Close buttons to "Back" in PresetPicker** — the dismiss button in the preset picker dialog now reads "Back" in all modes (load, edit, delete) for consistency with the tool picker.

### Added

- **Back button on tool picker** — the tool picker's button bar now has a Back button that returns to the previously loaded tool form. Disabled on first launch when no tool has been loaded; enabled when navigating to the picker from a loaded form.
- **Resizable table columns** — the tool picker, preset picker, and command history dialog columns can be manually resized by dragging column headers. The last column automatically fills remaining space with a 50px minimum.
- **Description tooltips** — hovering over tool descriptions in the picker or preset descriptions in the preset dialog shows the full text in a tooltip, helpful when descriptions are truncated by column width.

### Fixed

- **Recovery file reappears after declining and closing** — closing the app now stops all timers before clearing the recovery file, preventing the autosave timer from recreating the file during shutdown.
- **Phantom recovery prompts on tools with default values** — unchanged forms are no longer saved. The autosave system compares the current form state against a baseline captured at tool load, and only writes when actual changes exist.
- **Stale recovery files accumulating in temp directory** — expired or corrupted recovery files are automatically cleaned up on startup.
- **Up to 30 seconds of work lost on crash** — replaced the 30-second periodic autosave timer with a 2-second debounced single-shot timer. Every field change restarts a 2-second countdown; at most 2 seconds of work is lost on a crash.
- **Extra flags toggle ignored by command preview** — unchecking the Additional Flags group now removes extra flags from the command preview as expected.
- **Repeatable boolean audit** — fixed non-repeatable flags incorrectly marked `repeatable: true`: `tools/curl.json` `--verbose` (`-v`) and `tools/git.json` `--verbose` (`-v`). Both are single-toggle flags, not stackable like nmap's `-v -v -v`.
- **Test suite recovery file leaks** — all three test files that create `MainWindow` instances now include a cleanup helper that removes stale recovery files at startup and after final cleanup.

#### Full suite results

- **All 5 test suites pass: 1,026/1,026 assertions, 0 failures**
  - Functional: 832/832
  - Smoke: 58/58
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.6.9] — 2026-04-01

### Added

- **Copy As shell formats** — right-click the command preview area to copy the command formatted for Bash (`shlex.join`), PowerShell (single-quote quoting, `&` prefix for spaced binaries), or Windows CMD (double-quote quoting with special character handling). The existing Copy Command button and Ctrl+C shortcut remain unchanged.
- **Ansible tool schemas (testing)** — added 4 new schemas in `tools/Ansible/`: `ansible`, `ansible-playbook`, `ansible-vault`, and `ansible-galaxy`. These are mostly untested and may not cover every flag or edge case — contributions and bug reports welcome.

#### Full suite results

- **All 5 test suites pass: 960/960 assertions, 0 failures**
  - Functional: 766/766
  - Smoke: 58/58
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.6.8] — 2026-04-01

### Added

- **Portable mode** — if `portable.txt` or `scaffold.ini` exists next to `scaffold.py`, all settings are stored in a local `scaffold.ini` (INI format) instead of the system registry/plist. This lets users run Scaffold from a USB drive with fully isolated configuration. No UI changes; portable mode is detected automatically at startup from file existence.
- **Portable mode documentation** — `--help` output now mentions portable mode; README includes a new "Portable Mode" section with setup instructions.

### Fixed

- **Reduced minimum window width** — minimum width lowered from 640px to 420px, allowing narrower window arrangements on small monitors or side-by-side layouts.

#### Full suite results

- **All 5 test suites pass: 936/936 assertions, 0 failures**
  - Functional: 742/742
  - Smoke: 58/58
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.6.7] — 2026-04-01

### Added

- **Command history (Ctrl+H)** — after each command execution, Scaffold automatically records what was run. Press Ctrl+H (or Presets > Command History...) to browse recent commands for the current tool. Double-click or select "Restore" to reload the form state from any past run.
  - Stores up to 50 entries per tool in QSettings (display string, exit code, timestamp, form state)
  - Form state captured at run start, not finish — safe even if user changes the form while running
  - History dialog shows exit code (color-coded green/red), command, timestamp, and relative age
  - "Clear History" button with confirmation prompt
  - Per-tool isolation: each tool's history is independent
  - Graceful handling of corrupted QSettings data

### Fixed

- **Ambiguous Ctrl+H shortcut** — the history shortcut was registered as both a `QShortcut` and a menu action shortcut, causing Qt to log "Ambiguous shortcut overload" and ignore the keypress. Removed the duplicate `QShortcut`; the menu action handles it alone.

#### Full suite results

- **All 5 test suites pass: 924/924 assertions, 0 failures**
  - Functional: 730/730
  - Smoke: 58/58
  - Examples: 52/52
  - Manual verification: 61/61
  - Preset validation: 23/23

## [v2.6.6] — 2026-04-01

### Added

- **Form auto-save & crash recovery** — form state is automatically saved to a temporary recovery file every 30 seconds. If the app crashes or is force-closed, the next launch offers to restore the unsaved work via a recovery prompt. Recovery files expire after 24 hours and are cleared on normal close.
  - Auto-save timer starts when a tool is loaded, stops when returning to the picker
  - Recovery files stored in the system temp directory, keyed by tool name
  - Expired, mismatched, or corrupted recovery files are silently cleaned up
  - Empty/default forms are not saved (no unnecessary recovery prompts)
  - Immediate auto-save on first field change (no 30-second gap before first save)
- **Multi-word subcommand names** — subcommand names like `"role install"`, `"compose up"`, or `"compute instances create"` are now split into separate command tokens during assembly. Single-word subcommands are unaffected. Enables schemas for tools like `ansible-galaxy`, `docker compose`, `aws s3`, and `gcloud compute`.
  - Preview colorizer matches each subcommand word in sequence
  - Validation rejects empty names, leading/trailing whitespace, double spaces, and duplicates
  - New test schema: `tests/test_multiword_subcmd.json` (3 subcommands, global + scoped flags)
  - Updated `PROMPT.txt`, `schema.md`, and `README.md`

### Fixed

- **Repeat spinner clipping** — the "x" count spinner on repeatable boolean fields (e.g. nmap's Verbose `-v`) was too narrow, clipping the number text. Increased `REPEAT_SPIN_WIDTH` from 60px to 75px. Audit: the timeout spinbox (80px) and subcommand combo (600px max) are adequate; no other spinboxes are affected.
- **Required field status disappears after 3 seconds** — the red "Required: ..." message below the command preview was using `_show_status()`, which starts a 3-second auto-clear timer. Required field messages now set the label directly and stop the timer, persisting until the user fills in the missing fields. Transient messages (copy confirmations, etc.) still auto-clear normally.
- **Test suites hang on stale recovery files** — auto-save recovery files left behind by crashed sessions caused a blocking `QMessageBox.question()` dialog on the next test run. Added global `QMessageBox.question` auto-decline patches to all 3 test files.

#### Full suite results

- **All 5 test suites pass: 891/891 assertions, 0 failures**
  - Functional: 697/697
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 58/58
  - Preset Validation: 23/23
- All 10 tool schemas validate with zero errors

---

## [v2.6.5] — 2026-03-31

### Added

- **Format markers (`_format`)** — tool schemas and presets now include a `_format` metadata key (`"scaffold_schema"` and `"scaffold_preset"` respectively) to prevent cross-loading. Three-tier enforcement:
  - Correct `_format` → loads silently
  - Missing `_format` on tool schemas → warning dialog with "Load Anyway" / "Cancel" (presets with missing `_format` load silently for backwards compatibility)
  - Wrong `_format` → hard reject with clear error message explaining what the file appears to be
- **Example schema (`tools/example.json`)** — bundled reference schema demonstrating every Scaffold feature (all 10 widget types, subcommands, display groups, dependencies, mutual exclusivity, min/max, deprecated, dangerous, examples, validation, and more). Use it as a starting point when building schemas for your own tools.
- New presets automatically include `_format: scaffold_preset` as the first key. Existing presets without the marker continue to load fine.
- All 10 bundled tool schemas updated with `_format: scaffold_schema` as the first key.
- `PROMPT.txt` and `schema.md` updated to include `_format` in the schema specification and examples.

#### Full suite results

- **All 5 test suites pass: 825/825 assertions, 0 failures**
  - Functional: 631/631
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 58/58
  - Preset Validation: 23/23
- All 10 tool schemas validate with zero errors

---

## [v2.6.4] — 2026-03-31

### Added

- **Copy Output button** — copies the output panel's plain text to the clipboard. Placed in the action bar next to "Save Output...". Shows "No output to copy" if the panel is empty.
- **Tooltip word wrapping** — long tooltips on subcommand combo items and field descriptions now wrap instead of stretching across the screen. Tooltips use HTML rich text for automatic word wrapping.
- **Status message auto-clear** — transient status messages (copy confirmations, validation errors) now auto-clear after 3 seconds via a single-shot QTimer. Process state messages (Running, Exit) are unaffected.
- **About dialog GitHub link** — the Help > About Scaffold dialog now includes a clickable link to the GitHub repository.

#### Full suite results

- **All 5 test suites pass: 807/807 assertions, 0 failures**
  - Functional: 614/614
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23
- All 9 tool schemas validate with zero errors

---

## [v2.6.3] — 2026-03-31

### Fixed

- **Field search highlight jarring in dark mode** — highlight color now uses theme-aware selection color instead of hard-coded bright yellow.
- **Header separator stale color after theme toggle** — separator now updates when the user toggles themes.
- **Elevation note hard-coded gray** — now uses theme-aware dim text color.
- **Search no-match label hard-coded red** — now uses Catppuccin error color in dark mode.
- **Subcommand not colored in command preview** — subcommand tokens now render with a distinct bold color instead of generic value color.
- **ANSI escape codes in output panel** — CLI tools emitting ANSI escape codes (e.g. color sequences) no longer appear as raw text; they are stripped before display.
- **Documentation out of sync** — `password` type and six argument fields were missing from `schema.md`. All now documented.
- **Misleading comment** — reworded incorrect comment about `QTextDocument.find` case sensitivity.
- **Scroll position on subcommand switch** — switching subcommands now resets scroll to top.
- **Scroll area right margin** — removed unnecessary 8px right padding; `QScrollArea` handles scrollbar space internally.
- Dead code removal: removed unused methods and attributes that were defined but never called.

### Added

- **Help menu** — new "Help" menu in the menu bar with two items:
  - "About Scaffold" — app name, version, one-line description
  - "Keyboard Shortcuts" — listing of all 11 keyboard shortcuts
- **Subcommand combo box truncation** — long subcommand descriptions are truncated in the combo label with full text available in a tooltip.

#### Full suite results

- **All 5 test suites pass: 801/801 assertions, 0 failures**
  - Functional: 608/608
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23
- All 9 tool schemas validate with zero errors

---

## [v2.6.2] — 2026-03-31

### Fixed

- **Process cleanup missing for FailedToStart** — when `QProcess` emits `errorOccurred(FailedToStart)`, Qt does not emit `finished`. This left timers ticking, stale state, and process reference dangling. Added the same cleanup that normal finish performs.
- **"Stopping..." disabled button styling** — the "Stopping..." stylesheets lacked `:disabled` selectors, causing the amber styling to look washed out on some platforms. Added explicit disabled selectors for both themes.

#### Full suite results

- **All 5 test suites pass: 793/793 assertions, 0 failures**
  - Functional: 600/600
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23
- All 9 tool schemas validate with zero errors

---

## [v2.6.1] — 2026-03-31

### Fixed

- **Process kill hardening** — `QProcess.kill()` sends SIGKILL, which pkexec cannot forward to grandchild processes. Elevated commands would orphan the actual tool process when stopped. Now uses SIGTERM first (which pkexec can forward), with SIGKILL as a 2-second fallback.
- **Centralized kill logic** — all 5 process kill sites now call a single `_stop_process()` method instead of calling kill directly.
- **"QProcess: Destroyed while process is still running" warning** — process reference is now cleared on finish, preventing the warning on window close.
- **"Stopping..." button state** — after clicking Stop, the button shows "Stopping..." in amber/italic and is disabled until the process exits, preventing confusion if SIGTERM takes a moment.
- **"Stopping..." repaint on Linux** — forces Qt to repaint the button immediately before stopping the process, so the intermediate state is always visible.
- **Error handler button re-enable** — prevents the button from staying disabled if a QProcess error fires while in "Stopping..." state.

### Added

- SIGTERM-first process stop with 2-second escalation to SIGKILL
- Process group kill fallback for non-elevated non-Windows processes

#### Full suite results

- **All 5 test suites pass: 781/781 assertions, 0 failures**
  - Functional: 588/588
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23
- All 9 tool schemas validate with zero errors

---

## [v2.6.0] — 2026-03-31

### Added

#### Integer Min/Max Constraints

Optional `min` and `max` fields on integer and float argument types constrain the spinbox range in the GUI.

- **Schema fields:** `"min": null` and `"max": null`. Accept a number or null. Only valid on `integer` and `float` types — other types produce a validation error.
- **Backwards compatible:** Existing schemas without min/max normalize to null. No schema changes required.

#### Deprecated & Dangerous Flag Indicators

Two new optional argument fields provide visual indicators for flagged arguments without disabling them.

- **`deprecated`** (string or null): When set, the field label gets strikethrough and an amber "(deprecated)" suffix. The deprecation message is prepended to the tooltip. The field remains fully functional.
- **`dangerous`** (boolean, default false): When true, the field label gets a red warning symbol prefix. A caution message is prepended to the tooltip. Purely visual — no behavioral change.
- **Theme-aware colors** for both indicators.
- A field can be both deprecated and dangerous.

#### Password Input Type

New `password` widget type for flags that accept sensitive values like passwords, API keys, and tokens.

- Renders as a masked `QLineEdit` with a "Show" toggle checkbox.
- Works identically to string fields for command assembly, preset serialization, and preset loading.
- Supports `validation` regex (same as string). Using `examples` on a password type produces a validation warning.

#### Full suite results

- **All 5 test suites pass: 766/766 assertions, 0 failures**
  - Functional: 573/573
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23
- All 9 tool schemas validate with zero errors

---

## [v2.5.10] — 2026-03-31

### Added

- **Preset Picker dialog** — replaced the plain dropdown for Load/Delete Preset with a full table-based picker. 4 columns: favorite star, preset name, description, last modified date. Three modes: load, delete, edit.
- **Preset favorites** — click the star column to mark presets as favorites. Favorites sort to the top. Stored in QSettings with automatic cleanup of stale favorites.
- **Edit Description** — update a preset's description after saving via the preset picker.
- **Edit Preset mode** — "Edit Preset..." menu item opens the picker with "Edit Description..." and "Delete" buttons. Delete includes confirmation dialog with git restore tip.

### Changed

- **Presets menu restructured** — "Delete Preset..." replaced with "Edit Preset..." which opens the picker in edit mode

#### Full suite results

- **All 5 test suites pass: 710/710 assertions, 0 failures**
  - Functional: 517/517
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
  - Preset Validation: 23/23

---

## [v2.5.8] — 2026-03-31

### Added

- **Preset descriptions** — optional description field when saving presets, displayed as "name -- description" in the load/delete picker. Stored as `_description` in the preset JSON. Fully backwards-compatible with existing presets.

---

## [v2.5.7] — 2026-03-30

### Changed

- **Delete Tool** rebuilt as a button on the tool picker instead of a File menu action — simpler and more discoverable
- Delete button disabled by default, enables only when a valid tool is selected

### Fixed

- **Delete Tool** file menu action was permanently greyed out — replaced with picker button that tracks selection state

---

## [v2.5.6] — 2026-03-30

### Fixed

- **Preset delete dialog** now includes a git restore tip matching the tool schema delete dialog
- **Delete Tool tests** now exercise the real code path with mocked dialogs instead of bypassing with direct calls

---

## [v2.5.5] — 2026-03-30

### Added

#### Process Timeout

Auto-kill processes that run too long. Useful for fire-and-forget execution of tools like `nmap` or `hashcat` where the user may walk away.

- **Timeout spinbox** in the action bar next to the Run/Stop button. Label: "Timeout (s):", range 0-99999, default 0 (no timeout).
- If the timer fires before the process finishes, the process is killed with a warning message.
- Timer is stopped when the process finishes normally, when the user clicks Stop, or when a new tool is loaded.
- **Per-tool persistence** — timeout value saved to QSettings and restored when the tool is loaded. Each tool remembers its own timeout independently.
- Status bar shows "Timed out (Ns)" instead of "Process stopped" for timeout kills.

#### Full suite results

- **All 4 test suites pass: 576/576 assertions, 0 failures**
  - Functional: 406/406
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.5.4] — 2026-03-30

### Added

#### Output Export (Save Output...)

Save command output to a text file for later review or sharing.

- **"Save Output..." button** added to the action bar, next to "Clear Output".
- Native save dialog with a suggested filename: `{tool_name}_output_{YYYYMMDD_HHMMSS}.txt`, defaulting to the user's home directory.
- Plain text export — strips all formatting. Includes the command echo line if present.
- UTF-8 encoding for saved files.
- Empty output guard — shows "No output to save" in the status bar if the output panel is empty.
- Status bar confirmation on success or error.

#### Full suite results

- **All 4 test suites pass: 564/564 assertions, 0 failures**
  - Functional: 394/394
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.5.3] — 2026-03-30

### Added

#### Output Search (Ctrl+Shift+F)

Search within the output panel to find text in command output. Separate from the form field search (Ctrl+F).

- **Search bar** appears above the output panel when Ctrl+Shift+F is pressed. Initially hidden.
- **Highlighting:** All matches highlighted in yellow, current match in orange. Highlights cleared when search is closed.
- **Navigation:** Enter jumps to next match, Shift+Enter to previous. Wrap-around at both ends.
- **Match count:** Label shows "X of Y" or "0 matches".
- **Case-insensitive** search.
- **Escape handling:** Escape closes the output search bar only when it has focus — does not steal Escape from the Stop button or the field search bar.

#### Full suite results

- **All 4 test suites pass: 553/553 assertions, 0 failures**
  - Functional: 383/383
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.5.2] — 2026-03-30

### Fixed

#### Output Panel Drag Handle Off-Screen Bug

The output panel resize handle allowed dragging the panel taller than the visible window area. The oversized height was saved to QSettings, so the problem persisted across restarts.

- Drag limit now dynamically capped to half the actual window height.
- Output height is clamped on window resize and on first display, fixing any oversized height restored from settings.

#### Full suite results

- **All 4 test suites pass: 528/528 assertions, 0 failures**
  - Functional: 358/358
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.5.1] — 2026-03-30

### Added

#### Syntax-Colored Command Preview

The command preview panel now displays syntax-colored output. Each token type is rendered in a distinct color for instant visual parsing of the assembled command.

- **Token types:** binary (bold blue), flag (amber/orange), value (default text), subcommand (bold blue), extra (dimmed gray, italic).
- **Light and dark mode** palettes with Catppuccin-inspired dark colors.
- **Preview widget** uses `QTextEdit` for rich text support — still a native PySide6 widget, no web engine.
- **Copy Command** still copies plain text — no HTML in clipboard.
- **Theme toggle** re-colors the preview immediately.
- Tokens with spaces or shell metacharacters are single-quoted for display. `--flag=value` is split with flag-colored flag part and value-colored value part.

#### Full suite results

- **All 4 test suites pass: 520/520 assertions, 0 failures**
  - Functional: 350/350
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
- All 9 tool schemas validate with zero errors

---

## [v2.5.0] — 2026-03-30

### Added

#### Collapsible Argument Groups -- `display_group` field

New optional argument field `display_group` (string or null) enables visual grouping of related arguments into collapsible sections. Arguments sharing the same `display_group` value are rendered inside a `QGroupBox` with that value as the title. Clicking the header toggles visibility.

- **Schema field:** `"display_group": null`. Accepts a string (group name) or null (ungrouped -- renders flat as before).
- **Normalization:** Existing schemas remain valid with no changes; missing keys fill to null.
- **Subcommand support:** Display groups work identically within subcommand argument sections.
- **No impact on existing behavior:** Command assembly, presets, mutual exclusivity, dependencies, and all widget types are unchanged.

#### Field Search / Jump -- Ctrl+F

Always-visible search bar below the tool header. Users can type to search or press Ctrl+F to focus it. Searches field names and flag names across all visible fields.

- Case-insensitive substring matching against both argument name and flag.
- First match is highlighted and scrolled into view. Enter/Shift+Enter cycle through matches.
- Collapsed display groups are automatically expanded when a match is inside them.
- Only searches visible scopes (global args + current subcommand).
- **Shortcuts:** Ctrl+F focuses, Escape clears and defocuses.

#### Full suite results

- **All 4 test suites pass: 494/494 assertions, 0 failures**
  - Functional: 324/324
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
- All 9 tool schemas validate with zero errors

---

## [v2.4.0] — 2026-03-30

### Added

- Added `display_group` field for collapsible argument groups -- see v2.5.0 for details.

#### Full suite results

- **All 4 test suites pass: 465/465 assertions, 0 failures**
  - Functional: 295/295
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57
- All 9 tool schemas validate with zero errors

---

## [v2.3.1] — 2026-03-30

### Added

#### Tool Picker Search/Filter
- Search bar at the top of the tool picker with placeholder "Filter tools..."
- Filters by tool name, description, and path columns (case-insensitive)
- Clear button restores all rows; auto-focuses on picker display

#### Keyboard Navigation
- Enter/Return key opens the selected tool from the picker
- Tab order: search bar -> table for natural keyboard flow
- Numpad Enter also supported

#### Enhanced Tooltips
- Tooltips now show flag, short_flag, type, separator mode, description, and validation regex
- Applied to both field labels and widgets
- Boolean fields hide separator; positional fields show placeholder name

#### Status Bar Improvements
- On tool load: shows field count and required count
- During execution: elapsed timer ticks every second
- On completion: elapsed time in exit message

#### Full suite results

- **All 4 test suites pass: 441/441 assertions, 0 failures**
  - Functional: 271/271
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.3.0] — 2026-03-29

### Added

#### Dependency Validation at Schema Load Time

`validate_tool()` now checks that every `depends_on` reference points to an existing flag within the same scope. Previously, a broken reference was silently ignored at load time and only failed at runtime.

#### Widget Creation Fallback

If an unexpected argument configuration causes an exception during widget construction, the form no longer crashes -- a plain `QLineEdit` fallback is returned with a tooltip explaining the failure. One bad field does not break the rest of the form.

#### Preset Schema Versioning

Presets now include a `_schema_hash` field -- an 8-character hash of the tool's argument flags at save time. When loading a preset against a changed schema, the status bar shows a non-blocking warning. Old presets without the hash load normally.

#### Runtime Dependency Audit (GUI)

After dependency wiring fails to find a parent widget, a warning is logged to stderr and the dependent field is left enabled (fail-open) instead of silently skipped.

### Improved

#### Flagship Schema Polish (nmap)

- All 111 argument descriptions rewritten in plain English
- Examples populated on key string fields (`--script`, `-p`, `TARGET`)
- Three ready-to-use presets: `quick_ping_sweep`, `full_port_scan`, `stealth_recon`

#### Full suite results

- **All 4 test suites pass: 343/343 assertions, 0 failures**
  - Functional: 173/173
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.2.0] — 2026-03-29

Public release of Scaffold. All changes from v2.1.0 and v2.1.1 are included.

### Changed
- README disclaimer updated: assertion count corrected from 157 to 291

### Tested
- **All 4 test suites pass: 291/291 assertions, 0 failures**
  - Functional: 121/121
  - Examples: 52/52
  - Manual Verification: 61/61
  - Smoke: 57/57

---

## [v2.1.1] — 2026-03-29

### External Code Review -- MiniMax M2.7

The full codebase was submitted to MiniMax M2.7 for an independent code review. Three bugs were fixed, three new test sections added, and PROMPT.txt was improved.

### Fixed

#### Spinbox value 0 silently dropped from command

Integer and float fields with no schema default used 0 as both the "empty/unset" sentinel and as a valid user value. This caused flags like `-m 0` (hashcat MD5 mode) or `--rate 0.0` to be silently omitted from the assembled command. The fix uses -1/-1.0 as the sentinel instead, so value 0 is now correctly included in the command.

#### No visual feedback on invalid Additional Flags input

The Additional Flags free-text field uses `shlex.split()` to tokenize user input. When the input contains unclosed quotes, the code silently fell back to naive splitting. Added a red border (theme-aware) on invalid input to warn the user. The fallback to naive splitting is preserved -- the border is a warning, not a blocker.

#### PROMPT.txt improvements

- Rule 8 completeness directive rewritten: now says "Include ALL documented flags" without the contradictory cap at 30-50.
- No-duplicates checklist rule clarified: duplicates are per-scope, not global. The same flag may appear in multiple subcommands.
- New coverage self-check section added: instructs the LLM to count arguments and include a `_coverage` field.

### Regenerated Schemas

Three tool schemas were regenerated with the updated full-coverage directives:

| Schema | Before | After | `_coverage` |
|--------|--------|-------|-------------|
| **nmap.json** | 34 args | 111 args | `full` |
| **curl.json** | 50 args | 271 args | `partial` (3 meta flags skipped) |
| **hashcat.json** | 46 args | 136 args | `full` |

All 9 schemas pass `scaffold.py --validate` with zero errors.

### Tested

Four test suites now cover the codebase. **Total: 291 assertions, 0 failures.**

- Functional: 121/121 (+16 new)
- Examples: 52/52 (unchanged)
- Manual Verification: 61/61 (new suite -- spinbox 0 edge cases, extra flags validation, dark mode colors, corrupted presets)
- Smoke: 57/57 (new suite -- full user workflow: launch, load, form, preview, run, presets, window behavior)

---

## [v2.1.0] — 2026-03-29

### Added
- **OpenClaw tool schema** (`tools/openclaw.json`) -- AI agent platform with 10+ subcommands
- **Gateway `--restart` flag** -- added missing boolean to the openclaw gateway subcommand
- **Linux install troubleshooting** -- README note covering `--break-system-packages` workaround and `libxcb-cursor0` dependency
- **Crypto donation addresses** -- BTC, LTC, ETH, BCH, and SOL

### Fixed
- **Dark mode scrollbars now match light mode exactly** -- uses `QStyleHints.setColorScheme(Qt.ColorScheme.Dark)` for native dark scrollbar rendering. Gracefully falls back on Qt < 6.8.

### Improved
- Side-by-side screenshots in README
- README updates -- line-count badge, assertion count, openclaw added to schemas table

### Tested
- Functional: 105/105 pass
- Examples: 52/52 pass
- Scrollbar visual parity confirmed on Windows 11 with PySide6 6.11.0

---

## [v2.0.1] — 2026-03-29

### Fixed
- **README assertion count** -- second mention still said 661; corrected to 156

---

## [v2.0.0] — 2026-03-29

### Added
- **`__version__` constant** (`2.0.0`) and `--version` / `-V` CLI flag
- **Shebang line** for direct execution on Unix (`./scaffold.py`)
- **Resizable output panel** -- drag handle between command controls and output panel (80px-800px range, persisted via QSettings)
- **Command options border** -- form area wrapped in a rounded frame for visual distinction
- **Separator line** between tool header and command options
- **UI polish** -- centered section labels, separator lines, green Run / red Stop button styling
- New example tool schemas: `nikto.json`, `gobuster.json`, `hashcat.json`, `ffmpegv2.json`
- Validation feedback tip in README

### Improved
- Tighter vertical spacing to reclaim screen space
- Higher contrast light theme borders
- `--help` output now includes version number
- **PROMPT.txt rewrite:**
  - Added complete example JSON demonstrating all key patterns
  - Added type hallucination guard table with wrong-to-correct name mappings
  - Expanded separator detection guidance, flag/short_flag convention, and completeness rules
  - Compressed to ~1,039 words while preserving all rules

### Fixed
- **QPushButton stylesheet parse error** -- missing whitespace between QSS rule blocks
- **`nmap.json` `-sC` mislabeled** -- `-sC` is a distinct flag, not the short form of `--script`. Split into separate entry.

### Tested
- Full pre-release audit (security, cross-platform, CLI entry points, error handling, UI polish)
- Functional: 104/104 pass
- Examples: 52/52 pass
- All 8 bundled tool schemas pass validation

---

## [v1.4.0] — 2026-03-28

### Added
- **`--help` / `-h` flag** with usage summary listing all available CLI modes
- Expanded module-level docstring with usage examples

### Improved
- Linted with `ruff check` -- all checks pass
- **Output buffering** -- output panel now buffers data and flushes every 100ms, preventing UI stalls on high-volume output
- **Output line cap** -- capped at 10,000 lines to bound memory usage
- **File size guard** -- tool schema loader rejects files over 1 MB
- **Error handling audit** -- added `PermissionError` handler in loader, try/except on preset save/delete, guards against file-at-directory-path
- **Cleanup** -- extracted magic numbers into named constants, organized imports, added docstrings and type hints to all key functions, simplified several methods

### Tested
- Functional: 101/101 pass
- Verified: no signal duplication on subcommand switch, no memory leaks on tool switch, `--prompt` output on Windows cp1252

---

## [v1.3.1] — 2026-03-28

### Improved
- Added right padding between form fields and scrollbar for cleaner layout

---

## [v1.3.0] — 2026-03-28

### Added
- **Elevated execution (sudo/admin) support** -- run commands with elevated privileges from within Scaffold
- New `elevated` schema field: `null`, `"never"`, `"optional"`, or `"always"`
- Platform-specific elevation: `gsudo` on Windows, `pkexec` on Linux/macOS
- Elevation checkbox in tool form with contextual notes
- "Running as administrator" status bar indicator when app is already elevated
- Elevation state included in preset save/load
- Graceful handling of missing elevation tools and cancelled password dialogs
- Custom arrow icons for dropdown and spinbox controls in dark mode
- Updated `PROMPT.txt` with `elevated` field and decision rule
- All example tool schemas updated with `elevated` field

### Security
- Full command injection audit passed -- QProcess uses list-based execution, no shell invocation

---

## [v1.2.3] — 2026-03-28

### Improved
- Added prerequisites section to Getting Started
- Added platform compatibility note

---

## [v1.2.2] — 2026-03-28

### Added
- **Dark mode** with system detection and manual toggle (View > Theme menu, Ctrl+D shortcut)
- Three theme options: Light, Dark, and System Default -- persisted across sessions
- Catppuccin Mocha-inspired dark color palette with full widget coverage
- Getting started instructions at the top of README

---

## [v1.2.1] — 2026-03-28

### Improved
- Command preview bar now uses a scrollable widget with a horizontal scrollbar for long commands

---

## [v1.2.0] — 2026-03-28

### Added
- **Examples field** for string arguments -- editable dropdown showing common values as suggestions while still allowing custom input
- Updated `PROMPT.txt` to include examples field (15 fields per argument)
- Updated all example tool schemas with expanded argument coverage and examples support

---

## [v1.1.0] — 2026-03-28

### Added
- **Binary availability check** in tool picker -- green checkmark for installed tools, red X for missing ones
- Tools sorted by availability (available first, unavailable second, invalid last)
- 4-column tool picker table (status, tool, description, path)

---

## [v1.0.1] — 2026-03-28

### Added
- ffmpeg example schema (later removed as incomplete)

---

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
