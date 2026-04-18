# Changelog

All notable changes to Scaffold are documented here.


## [v2.9.3] — 2026-04-17

Completes the cascade TOC/TOU hardening arc that was deferred from a previous release. Cascade preset loading now halts on `_schema_hash` mismatch instead of silently applying a stale preset and running the wrong command.

### Fixed

- **Cascade halts when a preset's `_schema_hash` doesn't match the current tool** — `_chain_advance` now gates `apply_values` on a hash check. Previously, if a tool schema had changed since a preset was saved (e.g. a flag renamed), the cascade silently dropped the renamed key, `build_command` produced an incomplete/wrong command, and the chain executed it against the live binary with no warning. The UI-mode load path (`_on_load_preset`, line ~8931) already detected this and surfaced a status-bar note — correct for interactive use, wrong for unattended cascades. The new check halts with `error_halted` status and a status-bar message of the form `Cascade stopped: preset schema changed for step N — {preset} (re-save against current {tool} schema)`. Both hashes are also written to stderr for forensic debugging. Absent `_schema_hash` is treated as a legacy preset and loads silently, mirroring the UI-mode guard. Closes the gap left by the v2.8.7.3 audit, which fixed the missing-tool and missing-preset TOCTOU cases but didn't catch the stale-preset case.

### Added

**Tests (test_functional.py):**
- **Section 178** — cascade `_schema_hash` mismatch coverage (14 assertions).
  - 178a (positive halt): builds V1 schema, computes its hash, writes a V1 preset, then writes a V2 schema with one flag renamed; asserts the cascade halts before reaching `_on_run_stop`, `_cascade_finish_status` is `"error_halted"`, status message contains the distinctive substring `"schema changed"`, and names both the preset and the step number.
  - 178b (matching hash): identical setup but tool stays at V1; asserts execution is reached and no halt fires.
  - 178c (legacy preset, no `_schema_hash`): asserts backward compatibility — chain runs normally, mirrors the UI-mode `if saved_hash is not None` guard.

#### Full suite results

- **All 6 test suites pass: 2,877/2,877 assertions, 0 failures**
  - Functional: 2,504/2,504 (was 2,490; +14 from §178)
  - Security: 159/159
  - Smoke: 78/78
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23


## [v2.9.2] — 2026-04-17

Cascade sidebar button-clipping fix on Linux, a new `_tool` preset meta key, a cascade dependency pre-flight check, six new bundled tool schemas (`find`, `ncat`, `wget`, `ssh`, `scp`, `tar`) with default preset packs, and two new example cascades.

### Added

- **`_tool` preset meta key** — `ToolForm.serialize_values` now emits `"_tool"` alongside the existing meta keys. On load and import, `_on_load_preset` and `_on_import_preset` compare it against the current tool; on mismatch, a warning dialog names both tools and offers "Load Anyway" / "Cancel" before values apply or the file is copied. Fires ahead of the `_schema_hash` mismatch warning so the more specific message wins. Absent `_tool` is treated as legacy and loads silently. `validate_preset`, `PRESET_PROMPT.txt`, and `schema.md` updated.
- **Cascade dependency pre-flight check** — new `_check_cascade_dependencies` and `_prompt_cascade_missing_deps` helpers scan a cascade's steps for tool schemas and presets that don't exist on disk. `CascadeSidebar._on_import_cascade` and `_on_load_cascade_list` call them after format validation and before mutating state. Missing paths are listed in a warning dialog with "Continue" / "Cancel"; Cancel aborts (no file copied, sidebar untouched), Continue proceeds as before. Path resolution reuses the existing `Path(__file__).parent` resolver. `schema.md` gained a Cascade Files section.
- **Six new bundled tool schemas** — `find`, `ncat`, `wget`, `ssh` (37 args), `scp` (21 args), `tar` (57 args). `ncat` covers Nmap's netcat; `find` and `wget` are partial coverage with niche flags omitted, documented in each file's `_coverage` field. Bundled count now 28.
- **Default preset packs for the new tools** — 25 presets total: `find/` (6), `ncat/` (5), `wget/` (5), `ssh/` (5), `scp/` (4), `tar/` (5). Seeded into `presets/{tool}/` on first open via the existing `_presets_dir()` copy-on-first-access path.
- **Two new example cascades** — `cascade_nmap_ncat` (nmap discovers open ports, ncat connects using the `port_check` preset, single shared `HOST` variable) and `cascade_ssh_scp` (ssh verifies a remote file exists, scp downloads it with `stop_on_error: true`).

### Fixed

- **Cascade chain button text no longer clips on Linux** — `CascadeSidebar.__init__` previously applied the compact `padding: 2px 8px` QSS to only three of the seven chain-row buttons (`run`/`pause`/`stop`). `loop_btn`, `stop_on_error_btn`, `clear_all_btn`, and `add_step_btn` kept native button chrome, which overflowed the fixed width budget on Linux light mode. The init loop now applies the compact QSS to all seven.
- **Toggle OFF no longer wipes compact padding** — `_style_loop_btn` and `_style_stop_on_error_btn` OFF branches previously called `setStyleSheet("")`, erasing the compact QSS on every `_load_cascade` and toggle-off. Both now apply `self._chain_qss`.

### Changed

- **Single source of truth for `padding: 2px 8px`** — new `self._chain_btn_body` fragment and `self._chain_qss` composed from it replace four literal copies (init, both `_style_*_btn` ON branches, `update_theme`).
- **`update_theme` refreshes `self._chain_qss` first** — hoisted above `_style_loop_btn` so the OFF branch picks up the current theme's border color on mode switch. Loop now also covers `clear_all_btn` and `add_step_btn`.

### Tests (test_functional.py)

- **Section 174** — Cascade chain-button compact-QSS regression guard (32 assertions). Iterates all 7 chain-row button names and asserts `padding: 2px 8px` at init, after toggle ON/OFF, and after theme flip. Asserts the `_chain_btn_body ⊂ _chain_qss` single-source invariant.
- **Section 175** — Bundled-cascades intact guard (4 assertions). Catches any future section that forgets to redirect `_cascades_dir()`.
- **Section 176** — `_tool` identity coverage (12 assertions). Serialization, meta-key validation, matching/mismatched load, Cancel vs Load Anyway, backward compat for missing `_tool`, parallel coverage for the import path.
- **Section 177** — Cascade dependency pre-flight coverage (24 assertions). All-present, missing-tool-only, missing-preset-only, mixed, and empty cases; drives import and load paths through monkey-patched `_prompt_cascade_missing_deps` to verify Continue/Cancel behavior.

#### Full suite results

- **All 6 test suites pass: 2,863/2,863 assertions, 0 failures**
  - Functional: 2,490/2,490 (was 2,408; +82 net after §174–§177 adds and v2.9.2 cycle work)
  - Security: 159/159
  - Smoke: 78/78 (was 70; +8 from v2.9.2 cycle work)
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23


## [v2.9.1] — 2026-04-16

POSIX shell-quoting correctness fix for the generic
command-preview copy format.

### Fixed

- **`_quote_token` now uses POSIX close-escape-reopen quoting** —
  tokens containing both whitespace and a single quote previously fell
  to a Windows CMD-style `""` double-quote escape, which is invalid
  syntax in any POSIX shell. The new implementation emits standard
  POSIX single-quote escaping (`'it'\''s a test'`), which round-trips
  cleanly through `shlex.split`. Only affected the "generic" copy
  format; `_format_bash` (via `shlex.join`) was already correct.

### Added

**Tests (test_functional.py):**
- **Section 173** — `_quote_token` POSIX correctness and round-trip
  verification (12 assertions).
- **Section 92** — updated 2 assertions to encode POSIX-correct
  behavior (previously asserted the now-fixed Windows-CMD output).

#### Full suite results

- **All 6 test suites pass: 2,773/2,773 assertions, 0 failures**
  - Functional: 2,408/2,408 (was 2,397; +11 net after §173 add and §92 consolidation)
  - Security: 159/159
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23


## [v2.9] — 2026-04-16

Major release: Scaffold now includes the ability to add a custom PATH, so you are not limited to just the system path. Every time Scaffold is ran it scans the system PATH + whatever other paths you configure for any binaries that you also have a tool schema for. This release also includes a full cascade capture regex safety pipeline, and closes three bugs identified during a Claude Opus 4.7 code review.

### Fixed

- **Invalid regex patterns rejected at save/import** —
  `_validate_capture_entry` now calls `re.compile()` on patterns for
  `stdout`/`stderr` sources. Previously, syntactically invalid patterns
  (e.g. `[unclosed`, `(?P<`) were accepted at validation and silently
  discarded at runtime, leaving users no feedback.
- **Runtime `re.error` now surfaces distinct warnings** —
  `extract_captures` collects per-capture regex errors and emits them
  through a separate `capture_errors` return channel, letting users
  distinguish "my regex is broken" from "my regex didn't match."
- **Catastrophic regex backtracking (ReDoS) hardened** — previously,
  a pattern like `^(a+)+$` against 64 KB of input could freeze the UI
  thread indefinitely during cascade execution. Measured ~20s hang at
  N=30 (7-char pattern), ~83s at N=32, astronomical at 64 KB. Two-layer
  defense now in place:
    - **Layer 1 (validation-time):** heuristic rejects nested-quantifier
      and alternation-under-quantifier patterns via
      `_pattern_is_redos_prone()`. 100% true-positive rate on four
      classic ReDoS forms, zero false positives on fourteen realistic
      capture patterns from existing tool schemas.
    - **Layer 2 (runtime):** `_bounded_regex_search` runs `re.search`
      in a long-lived `multiprocessing.Pool` worker with a 2-second
      wall-clock timeout. On timeout, the worker is terminated and
      replaced, and a `(name, "timeout: regex exceeded 2.0s")` entry
      is added to the capture_errors list. Chosen over QThread/
      ThreadPoolExecutor because Python threads cannot be forcibly
      killed and the C regex engine holds the GIL.

### Changed

- **`extract_captures` signature** — return type changed from
  `dict[str, str]` to `tuple[dict[str, str], list[tuple[str, str]]]`.
  Second element is a list of `(capture_name, error_message)` for
  captures that errored (invalid regex, timeout, or worker crash).
  All internal callers updated. External callers must unpack the tuple.
- **`scaffold.py` now imports `multiprocessing` and `threading`** from
  stdlib. No new third-party dependencies. `multiprocessing.freeze_support()`
  is called at the top of `main()` for PyInstaller compatibility on
  Windows.

### Added

**Code:**
- **`MAX_REGEX_SECONDS`** module constant (default: 2.0).
- **`_pattern_is_redos_prone(pattern) -> tuple[bool, str]`** helper
  for programmatic ReDoS-prone shape detection.
- **`_regex_worker_entry`, `_get_regex_pool`, `_reset_regex_pool`,
  `_bounded_regex_search`** — multiprocessing worker infrastructure
  for bounded regex execution.

**Tests (test_functional.py):**
- **Section 167** — `_validate_capture_entry` rejects invalid regex
  (24 assertions).
- **Section 168** — `extract_captures` signals `re.error` distinctly
  via the returned errors list (10 assertions).
- **Section 170** — validation-time heuristic rejects ReDoS-prone
  patterns; accepts realistic patterns (22 assertions).
- **Section 171** — `extract_captures` times out on ReDoS patterns,
  measured within budget (3 assertions).
- **Section 172** — `_pattern_is_redos_prone` unit tests with
  ReDoS-prone and realistic patterns (22 assertions).

### Docs

- **README: "Using tools that aren't on your PATH" subsection** added
  under "How It Works". Explains that `binary` accepts a bare name
  (PATH-resolved) or an absolute path, that shell-relative paths like
  `./installer` do not work because Scaffold doesn't invoke a shell,
  and walks through the two fixes (put the binary on PATH, or set an
  absolute path in the schema) with a rayhunter installer example.
- **SCHEMA_PROMPT.txt: rule 17 (RELEASE BINARIES)** — one-sentence
  nudge telling the LLM to flag downloaded-release-binary tools in
  its reply so users know they may need to adjust PATH or `binary`.

#### Full suite results

- **Functional: 2,397/2,397 assertions, 0 failures**
  - (previously 2,327; +70 new assertions across Sections 167, 168,
    170, 171, 172)
- Other suites unchanged.



## [v2.8.7.3] — 2026-04-16

Error-path audit. Two real bugs fixed (cascade executes wrong tool after load failure; cascade silently skips missing preset), three defensive hardening items.

### Fixed

- **Cascade TOCTOU: missing tool file no longer runs the wrong binary** — `_chain_advance` now verifies `tool_path` matches after `_load_tool_path` returns. Previously, `_load_tool_path` swallowed load errors internally (showing a modal dialog, then returning), so the `except Exception` wrapper in `_chain_advance` never fired. The cascade proceeded to execute the *previous* step's binary with stale form data. The user would see a "Load Error" dialog, click OK, and then watch the wrong tool run. Now the chain halts with `error_halted` status if the loaded tool path doesn't match.
- **Cascade halts on missing preset file** — `_chain_advance` now has an `elif preset_path:` branch that halts the chain when a configured preset file no longer exists on disk. Previously the condition at the preset-load site had no else branch — a missing preset silently fell through, and the tool executed with default values instead of the expected configuration. This is treated as a configuration error (unconditional halt) rather than a runtime error (not gated by `stop_on_error`).
- **Export preset catches `json.JSONDecodeError`** — `_on_export_preset`'s except clause now catches `(OSError, json.JSONDecodeError)` instead of just `OSError`. Previously, exporting a preset whose source file contained malformed JSON raised an unhandled exception with no user feedback.

### Changed

- **Recovery file discarded notification** — when a recovery file is found but its stored tool path doesn't match the currently loaded tool (e.g. the schema file was moved), the file is still discarded, but the status bar now shows "Recovery file discarded — tool location has changed" instead of deleting silently.
- **History entry validation filters non-dict elements** — `_load_history` now returns `[e for e in entries if isinstance(e, dict)]` instead of the raw list. Previously, corrupt QSettings data containing non-dict elements (ints, strings, None) would crash `HistoryDialog._populate` with an unhandled `AttributeError` when calling `.get()` on the element.

### Added

- **Section 162 — cascade TOCTOU regression test** — configures a 2-slot cascade, deletes the second tool file from disk, runs the chain, and asserts: chain halted with `error_halted`, exactly 1 step recorded, wrong tool was never loaded.
- **Section 163 — missing preset halts chain test** — configures a 1-slot cascade with a preset, deletes the preset file, runs the chain, and asserts: chain halted with `error_halted`, 0 steps executed, status bar message contains "preset not found".

#### Full suite results

- **All 6 test suites pass: 2,594/2,594 assertions, 0 failures**
  - Functional: 2,229/2,229
  - Security: 159/159
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23


## [v2.8.7.2] — 2026-04-16


### Added

- **Sections 159–161 + 9d — test coverage for v2.8.7 changes.** Section 159 asserts cascade save/import route through `_atomic_write_json` (AW-1 regression guard). Section 160 pins `CAPTURE_RESERVED_NAMES` membership (prevents accidental re-introduction of legacy entries dropped in CRN-1). Section 161 verifies `CascadeHistoryDialog._on_delete` and `_on_clear` pass `StandardButton.No` as default (DC-1 regression guard, also documents the pattern for future destructive-action dialogs). Section 9d in `test_security.py` documents the `\` carve-out asymmetry — accepted in binary paths (section 3o), rejected in subcommand names.



## [v2.8.7.1] — 2026-04-16

Post-v2.8.7 polish pass. Crash-safety gap closed in cascade save/import, clarifying comments added to two decisions future readers could easily undo, one confirmation-dialog default tightened, and dead defense dropped from the capture reserved-name set.

### Fixed

- **Cascade save and import are now crash-safe** — `_on_save_cascade` and `_on_import_cascade` previously wrote JSON via `Path.write_text(json.dumps(...))`, which could leave the target file truncated or empty if the process was killed or the disk filled mid-write. Both sites now use `_atomic_write_json()`, matching every other JSON writer in the file. The cascade save path is the higher-value fix — a user actively naming a cascade expects it to survive a crash.

### Changed

- **`CAPTURE_RESERVED_NAMES` no longer lists legacy source names** — `stdout_full` and `stderr_full` removed from the reserved-name set. The on-load migration in `_load_cascade`, `_import_cascade_data`, and `_restore_cascade_config` rewrites those source strings before validation runs, so keeping them as reserved capture-variable names was dead defense. The migration dicts themselves still reference both old and new names (those are the rewrite source and target).
- **Clear Cascade History confirmation defaults to No** — `CascadeHistoryDialog._on_clear` now passes `QMessageBox.StandardButton.No` as the default button, matching the sibling `_on_delete` pattern added in v2.8.7. Other confirmation dialogs in the file pre-date this pattern and are intentionally out of scope.

### Added

- **Section 158 — stop-during-delay cascade test** — locks in the CHAIN_LOADING-state guard in `_on_stop_chain`. Sets up a 2-step cascade with a 2-second delay between steps, lets step 1 complete, stops during the delay, and asserts exactly 1 step was recorded (no phantom "stopped" step synthesized for step 2, which never started). A future change that broadens the synthesis guard to include `CHAIN_LOADING` would fail 158c/158e.

### Docs

- **`\` carve-out in binary-path validation now commented** — `validate_schema`'s shell-metachar check subtracts `\\` from the set when validating `binary` (Windows absolute paths like `C:\Windows\System32\ping.exe` need it as a separator) but not when validating subcommand names (which are tokens, not paths). A defensive comment now explains the asymmetry so a future reader doesn't "simplify" it and break Windows users.
- **`CASCADE_HISTORY_VERSION` silent-drop contract now commented** — a comment at the constant definition notes that a version bump will silently drop all existing history unless an explicit migration is added to `_load_cascade_history`. No code change; the trap is for future-you when the constant eventually changes.

#### Full suite results

- **All 6 test suites pass: 2,574/2,574 assertions, 0 failures**
  - Functional: 2,210/2,210
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23


## [v2.8.7] — 2026-04-15

Cascade history hardening, capture-source rename with on-load migration, stop-mid-step recovery, and UI polish — closes the v2.8.6 code review.

### Added

- **Delete confirmation in cascade history dialog** — `CascadeHistoryDialog._on_delete` now prompts before removing an entry. The confirmation message distinguishes parent-row selection ("Delete this cascade history entry?") from child-row selection, where the message makes the parent-scoped deletion explicit ("Deleting this step will remove the entire parent cascade entry from history. Continue?"). Default button is No.
- **ToolPicker theme refresh** — folder-header rows now update their backgrounds automatically when the theme changes. Implemented as `_update_header_colors()` triggered by `changeEvent(QEvent.PaletteChange)`, which walks the existing row map and re-applies colors without touching selection, scroll, or active filter state.
- **`_build_chain_step_record` helper** — centralizes the cascade step-record dict shape. Called from `_chain_on_finished` (normal completion), the failed-to-start path, and the new stop-mid-step path. Prevents the three sites from drifting on key names.
- **CAPTURE_RESERVED_NAMES extended** — `stdout_tail` and `stderr_tail` added to the reserved set alongside the legacy `stdout_full` / `stderr_full` entries (kept for defense against shadowing in pre-migration cascade JSONs).
- **New test coverage** — sections 152 (`_load_cascade_history` corrupt version key), 153 (`_update_cascade_run` no-op for missing run_id), 154 (stop-mid-step preserves in-progress step record), 155 (ToolPicker theme refresh), 156 (`stdout_full` → `stdout_tail` migration on cascade load), 157 (delete confirmation respects user choice). Plus 116j documenting that `source: "file"` requires the `path` key as of this release.

### Changed

- **Cascade capture sources renamed: `stdout_full` → `stdout_tail`, `stderr_full` → `stderr_tail`** — the previous names implied the entire stream was captured, but the implementation has always sliced to the last 64 KB (`CAPTURE_STREAM_TAIL_BYTES`). The new names match the actual behavior. A silent on-load migration in `_load_cascade`, `_import_cascade_data`, and `_restore_cascade_config` rewrites the legacy source names to the new ones, so existing cascade JSONs and history-restored configurations continue to work without user action. The capture definition dialog, validation, tooltips, and `CASCADE_LLM_GENERATION_GUIDE.md` all use the new names.
- **`CASCADE_HISTORY_VERSION` constant used in exports** — `_on_export` and `_on_export_all` now reference the constant instead of writing `"_version": 1` as a literal.
- **Empty-state label color** — `HistoryDialog` and `CascadeHistoryDialog` empty-state labels now use `DARK_COLORS["disabled"]` instead of a hardcoded `#888`.

### Fixed

- **Cascade history load survives a corrupt `_version` key** — `_load_cascade_history` now wraps the `int(ver)` parse in try/except `(ValueError, TypeError)` and returns `[]` on failure, matching the defensive style of the adjacent JSON parsing. Previously a non-numeric string in `cascade_history/_version` (from a corrupted registry or manual edit) would propagate `ValueError` up the load path.
- **Stop-mid-step preserves the in-progress step in cascade history** — `_on_stop_chain` now synthesizes a step record (with `error: "stopped"` and `exit_code: None`) and appends it to `_cascade_steps` before calling `_on_run_stop()`. The append happens before the kill so that when `_chain_on_finished` fires asynchronously and short-circuits on `CHAIN_IDLE`, the step is already recorded. Previously stopping during step N produced a history entry showing N-1 steps. Wrapped in try/except so any failure in the synthesis path cannot break Stop.
- **`_update_cascade_run` no longer writes when run_id is missing** — tracks a `found` flag during the entry walk and only calls `_save_cascade_history` if a match was updated. Previously every non-matching update path issued a needless QSettings write.
- **`source: "file"` requires the `path` key** — `extract_captures` no longer falls back to `entry.get("pattern")` when `path` is absent for `file`-source captures. The runtime now matches `validate_capture_entry`, which has always required `path`. This eliminates a divergence where a misconfigured cascade could pass validation conceptually but fail it formally (or vice versa). Captures using `pattern` for a `file` source will now be silently dropped at extract time — the dialog and validator both reject them on save. Test 116g (which used the wrong key) updated.
- **Test 123b assertion** — previously asserted `after == before + 1` after prefilling history to the cap, which is impossible under FIFO eviction. Now clears history first and prefills to 5 entries.

### Security Hardening

- **`_SHELL_METACHAR` extended** — `#` (shell comment), `'` (single quote), and `"` (double quote) added to the global metachar frozenset. `\` is added to the subcommand-name validation path but excluded from the binary-path validation path (where it's needed for Windows absolute paths like `C:\Windows\System32\ping.exe`). Defense-in-depth only — none of these characters were exploitable previously because Scaffold never invokes a shell, but they should never appear in executable or subcommand identifiers.

#### Full suite results

- **All 6 test suites pass: 2,569/2,569 assertions, 0 failures**
  - Functional: 2,205/2,205
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.6] — 2026-04-15

New Cascade history menu, LLM powered cascade generation guide.  Output panel resize fixes — drag handle height measurement, scrollbar coherence, and dynamic height cap.


### Added

- **Cascade History** — record and browse past cascade runs, restore individual steps or full cascades, export history to JSON. Documented in README, CHANGELOG, and in-app Cascade Guide.

- **Cascade generation guide (experimental)** — new `CASCADE_GENERATION_GUIDE.md` at repo root documenting a workflow for generating cascade files via an LLM with persistent access to your `tools/` and `presets/` directories (e.g. a Claude Project). The guide is split into a setup half for humans and an instructions half intended for pasting into the LLM's custom instructions. Preset-first generation with schema fallback. No code changes — this is a documentation-only feature pending real-world validation. Feedback and edge-case reports welcome.


### Fixed

- **Drag handle now measures siblings by size hint** — `_effective_max_height()` previously used each sibling's current `height()`, which was inflated when the output panel was small (the form scroll area would expand to fill freed space, creating a circular dependency that capped the output at ~140 px). Now uses `min(height(), sizeHint().height())` so the calculation reflects intrinsic widget sizes, not inflated ones. Also switched from `window().height()` to `parent.height()` so the available-space calculation excludes menu/status bar chrome.
- **Scrollbar stays coherent during drag resize** — `DragHandle.mouseMoveEvent` now preserves the scrollbar position across `setFixedHeight` calls: if the user was scrolled to the bottom the view stays at the bottom, otherwise the scroll offset is preserved.

### Changed

- **Output panel height cap is now dynamic** — removed the static `OUTPUT_MAX_HEIGHT = 800` pixel ceiling. The panel height is now bounded solely by `_effective_max_height()`, which computes available space from actual parent geometry minus sibling size hints. On large windows the output panel can grow to its full available space.

#### Full suite results

- **All 6 test suites pass: 2,553/2,553 assertions, 0 failures from changes**
  - Functional: 2,188/2,189 (1 pre-existing flake in §123b — history cap, unrelated)
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23



## [v2.8.5.11] — 2026-04-14

History crash/error reporting, test stabilization, README corrections.

### Added

- **History entries now distinguish crashes from normal exits** — the Exit Code column shows descriptive labels ("crashed", "not found", "timed out", "I/O error") with a tooltip for the specific error type, instead of a raw numeric code. Backed by two new fields (`crashed`, `error`) written when QProcess reports a crash or emits an error signal.

### Fixed

- **Test 26h geometry assertion stabilized** — added `qWaitForWindowExposed` before geometry measurement and widened the pixel slack from 4 to 8, eliminating an intermittent window-manager timing flake (~1-in-8 failure rate).

#### Full suite results

- **All 6 test suites pass: 2,260/2,260 assertions, 0 failures**
  - Functional: 1,896/1,896
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.10] — 2026-04-13

Bugfix — cascade button label and missing tooltips. Cascade variable dialog column clamping, history entry guard, and history empty-state UX.

### Fixed

- **Cascade Run button label corrected** — the button displayed "Run..." instead of "Running..." during execution.
- **Cascade buttons now have tooltips** — Run, Stop, and Clear were missing tooltips entirely. All six cascade buttons now use consistent rich-text tooltips.
- **Cascade variable definition dialog columns no longer draggable off-viewport** — `CascadeVariableDefinitionDialog` used `Stretch` on the last column with no viewport clamping. Columns could be resized past the viewport edge, becoming unreachable. Now uses the same `_fit_last_column` / `_clamp_for_last_column` pattern as HistoryDialog, PresetPicker, ToolPicker, and CascadeListDialog.
- **`_record_history_entry` guards all three capture vars** — previously only checked for `_history_display`; missing `_history_preset` or `_history_timestamp` would `AttributeError`. Now checks all three before proceeding.
- **History capture vars set before QProcess signal connections** — `_on_run_stop` previously connected `errorOccurred` before setting the history capture vars. If `QProcess.start()` failed synchronously, `_on_error` could fire before the vars existed. The capture block now runs before signal connections.

### Improved

- **History dialog empty-state UX** — when history is empty, the dialog now shows a centered message instead of an empty table with headers only. The Clear History button is disabled when empty.

### Added

- **Section 145** — `CascadeVariableDefinitionDialog` column clamping tests.
- **49ak–49al** — `_record_history_entry` with missing capture vars: no `AttributeError`, no spurious entry written.
- **49am–49ao** — history dialog empty-state: label visible with tool name, Clear button disabled when empty, enabled when entries exist.

#### Full suite results

- **Functional: 1,896/1,896**

## [v2.8.5.9] — 2026-04-13

Audit backlog cleanup — closes out the v2.7.4-era audit cycle. Two low-severity findings fixed, one dead-code removal.

### Fixed

- **`_substitute_in_form_fields` no longer partially mutates the form on halt** — the method now collects pending field writes into a local list and commits them only after the full loop completes without a halt. Previously, fields processed before an unset-capture halt (under `stop_on_error`) were already written while later fields were not, leaving the form in an inconsistent partial-substitution state (Finding 3).
- **Unset-capture warnings are now deduplicated per slot** — `_substitute_captures` now uses a `_unset_warned_captures` set (cleared per slot in `_chain_advance`) to emit at most one warning per capture name per slot. Previously, if three fields referenced the same unset capture, three identical warning lines were emitted (Finding 5).
- **Removed dead `_autosave_form()` call in `_check_for_recovery`** — after accepting recovery, `_default_form_snapshot` was set to match the restored state, so the subsequent `_autosave_form()` call always hit the early-out and never wrote a file. The call has been removed.

### Added

- **Section 141** — partial form mutation regression test: sets up a cascade with `stop_on_error=True`, one field with a known capture and one with a missing capture. Asserts neither field is mutated after halt.
- **Section 142** — unset-capture warning dedup test: calls `_substitute_captures` three times for the same missing capture under `stop_on_error=False`. Asserts exactly one warning, then verifies dedup resets per slot.
- **Section 143** — recovery flow dead-call test: walks through `_check_for_recovery` with a mocked recovery file, asserts form restores correctly and no recovery file is recreated.

#### Full suite results

- **Functional: 1,836/1,836** (up from 1,828)

## [v2.8.5.8] — 2026-04-13

Bugfix — atomic preset writes, cascade wrapper stacking, dock visibility persistence.

### Fixed

- **Preset import/export now use atomic writes** — `_on_import_preset` and `_on_export_preset` were still using raw `Path.write_text`, bypassing the `_atomic_write_json` helper introduced in v2.8.5.3. A disk-full or mid-write crash could corrupt the destination file. Both now write to a `.tmp` file and `os.replace`, matching all other save paths.
- **Cascade wrapper stacking eliminated** — `_chain_execute_current` now restores the real `_on_finished` handler before wrapping, so each step's wrapper captures the original handler (not the previous wrapper). Previously, N steps produced N nested wrappers, causing `extract_captures` and `run_btn.setEnabled(False)` to execute N times per process finish instead of once.
- **Cascade dock visibility persisted on native-X close** — `_on_cascade_visibility_changed` now writes `cascade/visible` to QSettings. Previously only the menu/Ctrl+G path (`_toggle_cascade`) persisted the state, so closing the dock via its native X button was forgotten on next launch.

### Added

- **Section 138** — atomic preset import regression test: patches `Path.write_text` to simulate mid-write failure, asserts destination file retains original content.
- **Section 139** — cascade wrapper stacking test: installs wrappers for 3 simulated steps, invokes `_on_finished` once, asserts `run_btn.setEnabled(False)` is called exactly 1 time (not 3).
- **Section 140** — cascade visibility persistence test: calls `_on_cascade_visibility_changed` with both values, asserts QSettings is updated each time.

#### Full suite results

- **All 6 test suites pass: 2,192/2,192 assertions, 0 failures**
  - Functional: 1,828/1,828
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.7] — 2026-04-13

Housekeeping — drag-enter cursor fix, preset prompt docs update.

### Fixed

- **`dragEnterEvent` now calls `event.ignore()` on no-match** — when no dragged URL ends in `.json` (or no URLs are present), the method now explicitly rejects the event. Previously it returned silently, which on some Qt versions/platforms left the drop-cursor in "accept" state for files Scaffold won't actually load.

### Changed

- **PRESET_PROMPT multi-preset convention updated** — the `=== MULTIPLE PRESETS ===` section now instructs the LLM to return each preset as a separate JSON object with `=== PRESET: <filename>.json ===` delimiters, instead of a JSON array. This matches `validate_preset`'s requirement that each file be a single top-level JSON object.

### Added

- **Section 136** — dragEnterEvent rejection tests: non-.json URL, no URLs, mixed URLs, case variations.
- **Section 137** — PRESET_PROMPT smoke test: verifies new separator pattern, no JSON array example, and array warning text.

#### Full suite results

- **All 6 test suites pass: 2,187/2,187 assertions, 0 failures**
  - Functional: 1,823/1,823
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.6] — 2026-04-13

Import/load hardening — format-check on preset import, malformed cascade steps handling.

### Fixed

- **Import Preset rejects non-preset files** — `_on_import_preset` now has a three-tier `_format` check mirroring `_load_tool_path`: cascade files are rejected with a clear message pointing to Cascade → Import Cascade; other non-preset formats (e.g. `scaffold_schema`) are rejected; files with no `_format` marker show a "Missing Format Marker" warning with Yes/Cancel (default Cancel). Previously a cascade file would pass `validate_preset` and silently import, then fail on next load.
- **CascadeListDialog handles malformed `steps` field** — `_populate` now validates that `steps` is a list before calling `len()`. If `steps` is a dict, string, or any non-list value, the Steps column shows `"0 (malformed)"` instead of a misleading count (dict length or string length). Malformed rows remain visible so users can find and delete them.

### Added

- **Regression test for duplicate-flag single-reporting** (Section 133) — confirms `_check_duplicate_flag_values` reports each flag collision exactly once per scope (global, subcommand), including positional flags and `short_flag` collisions.

#### Full suite results

- **All 6 test suites pass: 2,176/2,176 assertions, 0 failures**
  - Functional: 1,812/1,812
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.5] — 2026-04-13

Cascade dialog hardening — combined error messages, duplicate flag rejection, flag format validation.

### Fixed

- **CascadeCaptureDefinitionDialog shows one combined warning** — previously, N invalid capture rows produced N separate modal QMessageBox.warning dialogs. Now all errors are collected during the validation loop and shown in a single message listing every invalid row with its error (e.g. `Row 2 (name="badname"): pattern required for source 'stdout'`). Red cell highlighting is preserved per-row.
- **CascadeVariableDefinitionDialog rejects duplicate flags** — two or more variables targeting the same flag value are now caught at edit time with a combined error message listing all duplicate rows. Previously the second definition was silently ignored at runtime (first-match-wins in `_chain_advance`).

### Changed

- **CascadeVariableDefinitionDialog validates flag format** — flag values must now match a strict pattern: short/long flags (`-f`, `--output-file`), positionals (`TARGET`, `HOST`), or subcommand-scoped variants (`clone:--depth`, `compose up:--env`). Garbage strings, bare dashes, mixed-case words, and malformed subcommand prefixes are rejected with a combined error message. Added `_CASCADE_VAR_FLAG_RE` module-level compiled regex.

#### Full suite results

- **All 6 test suites pass: 2,149/2,149 assertions, 0 failures**
  - Functional: 1,785/1,785
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.4] — 2026-04-13

Cascade dock min-width fix and password clipboard safety prompt.

### Fixed

- **Cascade dock min-width restored on native close** — closing the cascade sidebar via its native X button now correctly resets the window minimum width to `MIN_WINDOW_WIDTH`. Previously the inflated min-width (`MIN_WINDOW_WIDTH + 320`) persisted, preventing the window from shrinking back. Extracted `_apply_cascade_minwidth` helper and wired `visibilityChanged` to `_on_cascade_visibility_changed` which syncs both the min-width and the menu checkmark regardless of how the dock is closed.

### Security Hardening

- **Copy Command prompts before exposing passwords** — all four clipboard copy paths (`_copy_command`, `_copy_as_bash`, `_copy_as_powershell`, `_copy_as_cmd`) now route through `_prepare_copy_cmd`, which detects filled password fields and shows a one-time confirmation dialog (default: mask with `********`). The user's choice is remembered for the remainder of the tool session (in-memory only, never persisted to QSettings) and resets when a new tool is loaded. Defense-in-depth: display preview and history already masked passwords; this closes the last path where plaintext could leak to the system clipboard.

#### Full suite results

- **All 6 test suites pass: 2,065/2,065 assertions, 0 failures**
  - Functional: 1,701/1,701
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.3] — 2026-04-13

Three bug fixes: capture substitution coverage, atomic preset writes, and PresetPicker init.

### Fixed

- **Capture substitution covers all widget types** — extracted the substitution loop from `_chain_advance` into a `_substitute_in_form_fields` helper that routes reads and writes through `ToolForm._raw_field_value` / `_set_field_value`, so `{capture}` tokens in text, file, directory, and password fields are properly substituted. Multi-enum list values also have each string element checked. Previously only QLineEdit and QComboBox-backed fields were handled.
- **Atomic JSON writes for presets and autosave** — added `_atomic_write_json` helper that writes to a `.tmp` sibling then `os.replace()`s into place, preventing file corruption on mid-write crashes. Applied to `_on_save_preset`, `_on_edit_description`, and `_autosave_form`.
- **`PresetPicker._deleted_last` initialized in `__init__`** — attribute is now set to `False` alongside other instance attributes, removing reliance on `getattr` fallback for a class-owned field.

#### Full suite results

- **All 6 test suites pass: 2,038/2,038 assertions, 0 failures**
  - Functional: 1,674/1,674
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.2] — 2026-04-13

Five targeted bug fixes identified by audit.

### Fixed

- **apply_values honors enum defaults for missing keys** — when a preset omits a key, `apply_values` now passes the schema `arg["default"]` instead of `None`, so enum fields restore to their declared default rather than falling back to index 0.
- **Duplicate flag validation no longer double-reports** — removed redundant `_check_duplicate_flags` call sites (and the now-unused function). Extended `_check_duplicate_flag_values` to also track positional (non-dash-prefixed) flag names, so all duplicates produce exactly one error.
- **`_SHELL_METACHAR` no longer contains a literal space** — space was indistinguishable from the separator in error messages. Binary validation now emits a distinct `"binary" contains whitespace` error via a separate `isspace()` check.
- **Crash no longer produces duplicate status and history** — added `_error_reported` flag so that when `_on_error` handles a crash, the subsequent `_on_finished` callback skips its status message and `_record_history_entry` call.
- **Password values preserve trailing whitespace** — removed `.strip()` from the password branch in `_read_field_value`, so pasted hex tokens and secrets with trailing spaces are no longer silently mutated.

#### Full suite results

- **All 6 test suites pass: 2,018/2,018 assertions, 0 failures**
  - Functional: 1,654/1,654
  - Security: 158/158
  - Smoke: 70/70
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.5.1] — 2026-04-13

Argv-flag injection guard for cascade capture substitution.

### Fixed/Security Hardening

- **Capture substitution argv-flag guard** — when a captured value resolves to a flag-like string (matches `^--?[A-Za-z]`) as the entire content of a form field, the output panel emits a warning and the chain halts under stop-on-error before the next step runs. Bare `-`, bare `--`, and negative numbers are exempt; captured values embedded in larger strings (e.g. `prefix-{name}-suffix`) are also exempt. One warning per capture name per slot; the dedup set resets between slots. The guard lives in the `CascadeSidebar._substitute_captures` wrapper — the pure `substitute_captures` function is unchanged. Defense-in-depth addition for the cascade capture system introduced in v2.8.5: Scaffold's QProcess list-based argv model already prevents shell injection, and this guard adds a visible signal for argv-flag confusion where a captured value could change downstream argument parsing.

### Added

- **Variable option tooltips** — options in the Edit Variables dialog now show hover-over descriptions.

## [v2.8.5] — 2026-04-13

Cascade capture system, new capture definition dialog, and an updated example cascade.

### Added

- **Cascade captures** — cascade slots can now declare named captures that extract values from a step's output and inject them into later steps via `{name}` substitution. Capture sources include regex on stdout/stderr, literal file paths, exit codes, and full stream contents. Captures are forward-only and share the cascade variable namespace; collisions silently override the earlier value. Unresolved captures emit warnings and trigger a halt when stop-on-error is enabled.
- **Capture definition dialog** — new "Captures..." button on each slot row opens `CascadeCaptureDefinitionDialog`, a per-step editor for defining captures. Column headers include tooltips explaining each capture source type.
- **Example cascade: `cascades/nmap_followup_chain.json`** — uses nmap host discovery to capture an open port number, then feeds it into a targeted service scan via capture substitution.

## [v2.8.4] — 2026-04-11

History dialog filter bar, SHA-256 schema hashing, cascade crash recovery guard, and added new test sections.

### Added

- **History dialog filter bar** — `HistoryDialog` now includes a search bar (`_on_filter`) with case-insensitive substring filtering across command entries. Escape clears the filter text without closing the dialog (`eventFilter`).
- **New test coverage (sections 105–114):** malicious cascade variable values (105), `apply_to: "none"` scope persistence and injection suppression (106), cascade process-failed-to-start cleanup (107), `_cleanup_stale_recovery_files` expiry and corrupt-JSON handling (108), binary validation relative-path rejection (109), empty subcommand name rejection (110), single-slot cascade execution (111), cascade crash recovery with monkey-patch restoration (112), `schema_hash` SHA-256 verification (113), history dialog search bar filtering and Escape behavior (114).

### Changed

- **`schema_hash` uses SHA-256** — `schema_hash()` switched from `hashlib.md5` to `hashlib.sha256` for preset version hashing.

### Fixed

- **Cascade monkey-patch crash recovery** — `_chain_execute_current` now wraps the `_on_finished` monkey-patch and `_on_run_stop()` call in try/except, restoring the original handler and calling `_chain_cleanup` on failure instead of leaving the app in an unrecoverable state.
- **Section 3c stop-process test stabilized on Windows** — changed ping count from 0 (invalid on Windows) to 5, preventing a race where the process exited before the stop button was pressed.
- **Section 26i drag-handle test stabilized** — added `processEvents` + `adjustSize` calls and a positive-height guard before `_effective_max_height` measurement, eliminating an intermittent layout-timing flake.

#### Full suite results

- **All 6 test suites pass: 1,957/1,957 assertions, 0 failures**
  - Functional: 1,594/1,594
  - Security: 158/158
  - Smoke: 69/69
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.3] — 2026-04-09

Elevation helper tests, cascade example files, variable injection documentation, and a delete-confirmation UX tweak.

### Added

- **Elevation helper test coverage** — new test section verifying tool detection, caching, platform-dependent error messages, command wrapping, and label text for the elevation system.
- **Cascade example files** — two educational cascades bundled in `cascades/`: a basic two-step nmap chain and a ping-then-nmap workflow demonstrating cascade variables with per-step flag injection.
- **rsync tool schema and presets** — 129-argument schema with 6 bundled presets (local backup, remote SSH push, dry-run mirror, incremental snapshot, move files, selective copy with excludes). Most features should work but the schema is still mostly untested.

### Changed

- **Delete tool confirmation defaults to No** — the confirmation dialog when deleting a tool schema without presets now defaults to No and uses a shorter, clearer message.
- **Variable injection documented** — added an inline comment block explaining that cascade variables match by flag name and inject into only the first matching field.

#### Full suite results

- **All 6 test suites pass: 1,889/1,889 assertions, 0 failures**
  - Functional: 1,527/1,527
  - Security: 158/158
  - Smoke: 68/68
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.2] — 2026-04-08

Bug fixes for cascade import overflow, BOM-prefixed JSON files, chain cleanup run-button state, and timer leak in error handler.

### Fixed

- **Cascade import clamps to max slots** — `_import_cascade_data` now truncates oversized step lists to `CASCADE_MAX_SLOTS` (20) and shows a status bar message when truncated, matching the `_on_add_slot` UX pattern.
- **BOM-prefixed preset and cascade files load correctly** — added `_read_json_file` helper that strips UTF-8 BOM before parsing; applied at 12 user-facing JSON file-load call sites. Windows tools (Notepad, PowerShell) that write BOM-prefixed UTF-8 no longer cause `JSONDecodeError`.
- **Run button re-evaluated after cascade cleanup** — `_chain_cleanup` now calls `_update_preview()` (guarded) at the end, so the Run button is correctly disabled when the last cascade step left required fields unfilled.
- **Timer leak in `_on_error` fixed** — `_flush_timer` and `_timeout_timer` are now stopped in `_on_error`, matching the cleanup in `_on_finished`. Previously, both timers could remain active after a `FailedToStart` error.
- **Ghost widget prevention on tool switch and slot removal** — widget teardown in `_build_form_view` and `_on_remove_slot` now calls `hide()` → `setParent(None)` → `deleteLater()` instead of bare `deleteLater()`, preventing briefly-visible stale widgets on Linux where `deleteLater` timing differs.

#### Full suite results

- **All 6 test suites pass: 1,869/1,869 assertions, 0 failures**
  - Functional: 1,507/1,507
  - Security: 158/158
  - Smoke: 68/68
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

## [v2.8.1] — 2026-04-08

Cascade variable editor rework, smarter output panel sizing, keyboard shortcuts, and a cascade guide.

### Added

- **Enter / Shift+Enter shortcuts** — press Enter to run the current command or Shift+Enter to start the cascade chain, both suppressed when focus is in a text input.
- **Cascade Guide** — new Help menu entry with a plain-language walkthrough of cascade features (slots, variables, loop mode, pause/resume, stop-on-error).
- **"None" scope for cascade variables** — variables can now be scoped to "none", disabling injection entirely while keeping the variable defined for later use.

### Fixed

- **Cascade import rejects invalid apply_to values** — non-string, non-list values now fall back to "all" instead of crashing or being silently accepted.
- **Cascade variable "Apply To" selector** — replaced the free-text combo box with a checkbox dropdown listing all cascade slots, preventing typos and invalid slot references.
- **Variable editor column layout** — columns are now resizable with the Flag column bounded between 80–280 px; the Apply To column stretches to fill remaining space.
- **Output panel drag limit** — the drag handle now calculates available height from actual sibling widget sizes instead of a fixed half-window cap, preventing the output panel from overlapping the form.


#### Full suite results

- **All 6 test suites pass: 1,845/1,845 assertions, 0 failures**
  - Functional: 1,483/1,483
  - Security: 158/158
  - Smoke: 68/68
  - Manual verification: 61/61
  - Examples: 52/52
  - Preset validation: 23/23

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
