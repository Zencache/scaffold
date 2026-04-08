# Diagnostic Sweep Report

Date: 2026-04-07 | File: scaffold.py (7377 lines) | PySide6 6.11.0

---

## M1/TG6 — Extra flags fallback to `text.split()` on shlex failure

**Verdict: REAL — cosmetic only, execution is safe.**

`get_extra_flags()` (line 1777) falls back to `text.split()` when `shlex.split()` raises `ValueError`. Three callers exist: `build_command()` (line 2075), and `_update_preview()` (lines 6798, 6801). `build_command()` calls `get_extra_flags()` unconditionally — it does NOT check `extra_flags_valid()` first. `_update_preview()` calls `build_command()` (and thus `get_extra_flags()`) before the validity check at line 6825. This means the command preview **does** render the malformed `text.split()` tokens. However, the Run button is disabled when `extra_flags_valid()` returns False (line 6825–6826), and `_run_command()` independently checks `extra_flags_valid()` at line 6969 before building the command. So the malformed tokens appear in the preview display but can never reach execution.

---

## M2 — Temp arrow directory leak on crash

**Verdict: REAL — negligible severity.**

`_make_arrow_icons()` (line 628) creates a `tempfile.mkdtemp(prefix="scaffold_arrows_")` and registers cleanup via `app.aboutToQuit.connect(lambda: shutil.rmtree(...))` (line 630). On clean exit, the directory is removed. On crash (SIGKILL, power loss, unhandled segfault), `aboutToQuit` never fires and the directory leaks. There is no startup-time scan or cleanup of stale `scaffold_arrows_*` directories — the only reference to that prefix is the `mkdtemp` call itself. Each leaked directory contains two tiny PNG files (~200 bytes total), and the OS temp directory is periodically purged, so practical impact is negligible.

---

## M5 — `_colored_preview_html` negative-number heuristic

**Verdict: NOT REAL — correct for all realistic CLI input.**

The heuristic at line 2366–2367 is: `is_value = not next_tok.startswith("-") or (len(next_tok) > 1 and next_tok[1:].replace(".", "", 1).isdigit())`. Tested against representative tokens:

| Token      | `is_value` | Correct? |
|------------|------------|----------|
| `"-5"`     | True       | Yes — negative integer |
| `"-.5"`    | True       | Yes — negative float |
| `"5"`      | True       | Yes — positive value |
| `"--flag"` | False      | Yes — flag, not value |
| `"-"`      | False      | Yes — bare dash, ambiguous but safe |
| `"-1.2.3"` | False      | Yes — not a valid number |

The only edge case is a version-like string `"-1.2.3"` being classified as a flag rather than a value, but no real CLI tool passes negative version strings as flag arguments. The heuristic is sound.

---

## M6 — `_validate_extra_flags` clearing stylesheet

**Verdict: NOT REAL — no-op clobber.**

`_validate_extra_flags()` (line 1143/1147) calls `self.extra_flags_edit.setStyleSheet("")` to clear the widget-level override. The app-level dark-mode stylesheet (line 830) applies a generic `QPlainTextEdit { ... }` rule that covers all plain text edits, including `extra_flags_edit`. No code targets `extra_flags_edit` by object name or any other widget-specific selector in the theme. Clearing the widget-level stylesheet simply allows the app-level rule to cascade back — which is exactly the intended behavior. There is nothing to clobber.

---

## M7 — `_on_group_toggled` enum comparison

**Verdict: NOT REAL — correct for current PySide6.**

Line 1627 compares `state != Qt.CheckState.Checked.value`. In PySide6 6.11.0 (the installed version), `QCheckBox.stateChanged` emits an `int` (value `2` for checked). `Qt.CheckState.Checked.value` evaluates to `2` (int). The comparison is int-to-int and works correctly. The project has no pinned version or lockfile, but the `.value` accessor is the standard way to extract the underlying int from a PySide6 enum and has been stable across PySide6 6.x releases.

---

## M8 — `_history_display` `hasattr` guard

**Verdict: NOT REAL — valid defensive pattern.**

`_history_display` is set at line 7008 inside `_run_command()`, just before the process starts. It is read at line 7153 inside `_record_history_entry()`, called when a process finishes. The `hasattr` guard (line 7153) protects against `_record_history_entry` being invoked on a `MainWindow` instance that has never run a command — the attribute simply doesn't exist on the instance until the first `_run_command()` call. This is a straightforward instance-attribute lifecycle guard, not a monkey-patching smell. It would be reachable if, for example, an error-handling path called `_record_history_entry` before any process was launched.

---

## M9 — `validate_preset` unknown-key warning ordering

**Verdict: REAL — acceptable tradeoff.**

Line 507: `if tool_data is not None and not errors:` gates the unknown-key warnings behind a "no prior errors" check. This means a preset with both structural errors (wrong types, oversized strings) and stale keys will only report the structural errors; the unknown-key warnings are suppressed. This is intentional: structural errors (e.g., non-string keys, non-dict input) could cause the key-matching loop to produce false positives. The unknown-key messages are informational ("may be from an older version"), not blocking errors. Reporting structural errors first and requiring a clean pass before checking keys is a reasonable priority ordering.

---

## M10 — `apply_values` `blockSignals` scope

**Verdict: NOT REAL — no observable side effects.**

`self.blockSignals(True)` at line 1902 blocks signals emitted by the `ToolForm` QWidget itself (notably `command_changed`), but does NOT block child widget signals. During the `_set_field_value` loop, child widgets fire `stateChanged`, `valueChanged`, `textChanged`, etc. These trigger three kinds of connected slots: (1) lambdas calling `self.command_changed.emit()` — blocked because ToolForm's signals are suppressed; (2) `_on_group_toggled` for mutual-exclusion groups — executes correctly, uses its own `blockSignals` on sibling checkboxes; (3) `_update_dependent` for dependency chains — executes and updates enabled/disabled state (which is correct and desired), then calls `command_changed.emit()` which is blocked. After the loop, `blockSignals(False)` is called and a single `command_changed.emit()` at line 1939 consolidates all updates into one preview refresh. No flicker, no redundant renders, no bugs.

---

## L1–L8 — Code smells

**L1:** 5 module-level mutable globals (lines 530, 531, 615, 616, 617). `_dark_mode`, `_original_palette`, `_arrow_dir` are set once at theme-apply time; `_elevation_tool`, `_already_elevated` are set once on first call. None are ever reset to initial state.
KEEP

**L2:** `_build_widget_inner` (lines 1378–1556) is 179 lines with 11 branches (1 if + 9 elif + 1 else), one per widget type. Flat dispatch, no nesting — each branch is independent.
KEEP

**L3:** `json` is imported at module top (line 26). Local re-import as `_json` at line 4922 is dead weight.
TRIVIAL

**L4:** `html` is NOT imported at module top. Local import at line 2320 inside `_colored_preview_html` is the only usage. This is a deliberate lazy import for a stdlib module used in one place.
KEEP

**L5:** `self.parent()._clear_history()` at line 3481 is the only place in the entire file that accesses a parent's private method. No other dialog or widget reaches into its parent's internals.
KEEP

**L6:** Monkey-patch dance spans 41 lines for setup (5222–5262) and 4 lines for restore (5309–5312). `_stored_original_on_finished` is restored inside `_chain_cleanup` (line 5310), and every failure path (5 callers) routes through `_chain_cleanup`, so the restore is always reached.
KEEP

**L7:** SKIPPED — covered by Diagnostic 7 (output buffer).

**L8:** `table.resizeEvent = lambda e: (...)` pattern appears at exactly 3 call sites (lines 2528, 3026, 3387). All three are identical in structure.
KEEP
