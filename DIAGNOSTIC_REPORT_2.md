# Diagnostic Report 2 -- Cascade Panel + Tooltip + Linux Bugs

Platform: Windows 11 (win32), Qt style `windows11`, Python 3.14
Script: `cascade_diag2.py` -- all 7 sections ran successfully.

---

## Section 1 -- Hamburger menu button extra caret

**Symptom:** The cascade panel header shows a hamburger icon AND an extra down-arrow next to it.

**Root cause:** `_menu_btn` is a `QToolButton` with `popupMode=InstantPopup` and a `QMenu` attached (`setMenu(panel_menu)` at line 4206). Qt automatically draws a native menu-indicator arrow on any QToolButton that has an associated menu, unless suppressed. The app stylesheet contains **no** `QToolButton::menu-indicator` rule -- not in `apply_theme(True)` (dark mode QSS) and not on the button's own styleSheet (which is empty: `''`).

**Measurements:**
- Button text: `'\u2630'` (hamburger), popupMode: InstantPopup, arrowType: NoArrow
- Button pixel width: 24px, glyph width: 12px -- the extra 12px is consumed by the native menu-indicator arrow
- No `menu-indicator` suppression anywhere in the application stylesheet

**What's built:** The button, its menu, and InstantPopup mode all work correctly.
**What's missing:** A QSS rule to suppress the native indicator: `QToolButton::menu-indicator { image: none; width: 0; height: 0; }` -- either on the button itself or globally in `apply_theme()`.

**Confidence:** HIGH -- directly measured.

**Open questions for fix:**
- Apply the suppression globally in `apply_theme()` (both branches) or only on `_menu_btn.setStyleSheet()`?
- If global, does it affect any other QToolButton in the app that intentionally shows a menu indicator?

---

## Section 2 -- "Save cascade by name" -- current state

**Symptom:** User wants to know if saving a cascade by name is already implemented, and whether the UI tracks which named cascade is currently loaded.

**Root cause:** N/A -- this is a feature audit, not a bug.

**Findings:**
- `_on_save_cascade_file` (line 4649) **does** prompt for a name via `QInputDialog.getText`. The user can enter any name; it is sanitized and saved as `{safe_name}.json` in the cascades directory.
- The user can also provide an optional description.
- Overwriting an existing cascade prompts for confirmation and pre-fills the old description.
- **No attribute tracks the currently-loaded cascade name.** Searched for `_current_cascade_name`, `_loaded_cascade`, `current_cascade`, `_cascade_name`, `_loaded_name` -- none found in `CascadeSidebar` source.
- After loading a cascade from the list, there is no visual indicator of which cascade is active.

**What's built:** Full save-by-name workflow (name prompt, sanitization, overwrite confirmation, description). Full load-from-list workflow (`CascadeListDialog`).
**What's missing:** A `_current_cascade_name` attribute (or equivalent) on `CascadeSidebar` that is set when loading a named cascade and displayed in the panel header or status bar.

**Confidence:** HIGH -- source inspection.

**Open questions for fix:**
- Where should the current cascade name be displayed? Panel title bar, a label in the header row, or status bar?
- Should the name clear when the user manually modifies slots after loading?
- Should the name survive app restart (persist in QSettings)?

---

## Section 3 -- Required-field handling on cascade run

**Symptom:** Even when nmap's required `TARGET` field is populated, running a cascade still triggers a "required fields missing" abort.

**Root cause:** The chain execution flow is:
1. `_on_run_chain()` (line 4994) -- if `_cascade_variables` is non-empty, shows `CascadeVariableDialog`; otherwise skips straight to step 2.
2. `_chain_advance()` (line 5039) -- calls `_load_tool_path(tool_path)` which **creates a brand new `ToolForm`**, replacing the user's filled-in form.
3. If a preset is assigned to the slot, `apply_values(preset_data)` restores saved field values (line 5109).
4. After 150ms, `_chain_execute_current()` (line 5133) calls `form.validate_required()` (line 5139).
5. If the slot has **no preset**, the new form has all fields at defaults -- required fields like `TARGET` are empty.
6. `validate_required()` finds `TARGET` missing and returns it; the chain aborts with `"Cascade stopped: required fields missing"`.

**Verified behavior:**
- Filled `TARGET=192.168.1.1` in the original form.
- `_on_run_chain` did NOT show `CascadeVariableDialog` (empty `_cascade_variables`).
- After `_chain_advance` -> `_load_tool_path`, the new form's `TARGET` value was `None`.
- Chain state went to `idle` (aborted by `_chain_execute_current`).

**The dialog the user sees is NOT CascadeVariableDialog.** It is not a dialog at all -- it is `_chain_cleanup("Cascade stopped: required fields missing")` writing to the status bar. The user may also see the red validation border on the required field.

**What's built:** The chain correctly validates required fields and applies presets.
**What's missing:** A way to handle required fields when no preset is assigned. The user's manually-entered values are discarded by `_load_tool_path`.

**Confidence:** HIGH -- directly reproduced and traced.

**Open questions for fix:**
- Should the chain auto-capture the current form state as an implicit preset before running?
- Or should cascade variables be the mechanism (prompt the user for required fields that have no preset value)?
- Or should validation be skipped/relaxed for cascade steps that inherit from the current form state?
- Should this only apply to the *first* step (which the user may have been editing) or all steps?

---

## Section 4 -- Tooltip wrapping

**Symptom:** Long tooltips on cascade panel buttons render as a single very long line.

**Root cause:** Qt only auto-wraps tooltips when the text is detected as rich text (starts with `<html>`, `<p>`, `<qt>`, etc.). All cascade button tooltips are **plain text** strings:

| Button | Tooltip | Length | Rich? |
|--------|---------|--------|-------|
| run_chain_btn | (none) | 0 | -- |
| pause_chain_btn | "Pause cascade after the current step completes..." | 70 | No |
| stop_chain_btn | (none) | 0 | -- |
| clear_all_btn | (none) | 0 | -- |
| loop_btn | "Click to toggle. Loop: repeat chain until stopped." | 50 | No |
| stop_on_error_btn | "Stop on error: halt cascade if any step exits..." | 106 | No |
| add_step_btn | (none) | 0 | -- |
| _menu_btn | (none) | 0 | -- |
| MainWindow.run_btn | (none) | 0 | -- |

By contrast, field tooltips use `_build_tooltip()` (line 1549) which wraps content in `<p>...</p>` tags -- these ARE rich text and DO auto-wrap. Example: `<p>-iL (file)<br><br>Read targets from a file...</p>`.

**What's built:** `_build_tooltip()` correctly uses `<p>` tags for field tooltips.
**What's missing:** Cascade button tooltips are plain text. The longest one (`stop_on_error_btn` at 106 chars) will render as a single line and may extend off-screen on smaller displays.

**Confidence:** HIGH -- directly measured.

**Open questions for fix:**
- Wrap all button tooltips in `<p>` tags?
- Or use a fixed-width approach: `<p style="max-width:300px">...</p>`?
- Should buttons with no tooltip (run_chain_btn, stop_chain_btn, clear_all_btn, add_step_btn, menu_btn) get tooltips added?

---

## Section 5 -- Cascade panel "Running..." text cutoff

**Symptom:** When a cascade runs, the Run button text changes to "Running..." which is too wide for its allocated space.

**Root cause:** `_on_run_chain` sets `self.run_chain_btn.setText("Running...")` at line 5019. The cascade content widget is `fixedWidth=220`. The three buttons in `chain_row1` (Run, Pause, Stop) share this width with stretch factor 1 each (`addWidget(..., 1)` at lines 4264-4266), after subtracting margins (6+6=12) and spacing (4*2=8). Each button gets roughly `(220 - 12 - 8) / 3 = 66px`.

**Measurements:**
- `run_chain_btn` width: 67px (layout-allocated)
- sizeHint for current text: 81px
- Font advance for "Running...": 54px (text alone, without padding)
- Font advance for "Run": 21px, "Stop": 24px
- After `setText("Running...")`: width stays 67px, sizeHint stays 81px
- **Clipped: YES** (width 67 < sizeHint 81)

The button text is likely truncated with ellipsis or simply cut off visually.

**What's built:** The MainWindow's `run_btn` correctly uses `setMinimumWidth(QFontMetrics(...).horizontalAdvance("Stopping...") + 40)` (line 6323) to prevent clipping. The cascade `run_chain_btn` has no such minimum width.
**What's missing:** Either a minimum width on `run_chain_btn` to fit "Running...", or use a shorter text like "Run..." or keep it as "Run" (disabled).

**Confidence:** HIGH -- directly measured, clipping confirmed.

**Open questions for fix:**
- Change the text to something shorter ("Run..." or keep "Run" while disabled)?
- Or widen the button / reduce the number of buttons in the row?
- The MainWindow pattern (setMinimumWidth based on longest text) could be replicated, but 220px is tight for 3 buttons.

---

## Section 6 -- Tooltip colors in light mode (Linux bug)

**Symptom:** On Linux in light mode, hovering the required Target field shows black text on dark grey background -- unreadable.

**Root cause (code analysis):** `apply_theme(False)` (the light-mode branch, lines 839-846) does three things:
1. Sets `Qt.ColorScheme.Light` via `styleHints().setColorScheme()`
2. Restores `_original_palette` (captured at first call)
3. Clears the stylesheet to `""`

It does **NOT**:
- Explicitly set `ToolTipBase` or `ToolTipText` palette colors
- Add any `QToolTip` QSS rule

In dark mode, tooltips are covered by **both** the palette (`ToolTipBase=#2a2a3c`, `ToolTipText=#cdd6f4`) and QSS (`QToolTip { background-color: #2a2a3c; color: #cdd6f4; ... }`). In light mode, everything depends on `_original_palette`, which comes from the system/desktop theme.

On Windows, `_original_palette` has sensible light tooltip colors (`ToolTipBase=#f3f3f3`, `ToolTipText=#000000`). On Linux, the "original palette" varies wildly depending on the desktop environment and GTK/Qt theme. A dark GNOME/KDE theme will give dark ToolTipBase with dark ToolTipText, or the reverse -- either way, unreadable.

**Measurements (Windows -- for reference):**
- Light mode: ToolTipBase `#f3f3f3`, ToolTipText `#000000` (readable)
- Dark mode: ToolTipBase `#2a2a3c`, ToolTipText `#cdd6f4` (readable)
- TARGET widget inherits app palette: ToolTipBase `#f3f3f3`, ToolTipText `#000000`

**What's built:** Dark mode handles tooltips correctly with both palette and QSS.
**What's missing:** Light mode has no tooltip safety net. On Linux, it needs either:
- Explicit `ToolTipBase`/`ToolTipText` colors in the restored palette, or
- A `QToolTip` QSS rule in light mode too (e.g., `QToolTip { background-color: #f5f5f5; color: #1a1a1a; ... }`)

**Confidence:** MEDIUM -- code analysis is conclusive but could not reproduce on Windows. The vulnerability is clear from reading `apply_theme(False)`.

**Open questions for fix:**
- Add explicit light-mode tooltip colors to the palette? Or add a light-mode QToolTip QSS rule?
- Should the light-mode branch override `_original_palette`'s ToolTipBase/ToolTipText specifically, or set all colors explicitly (losing native theme integration)?
- Should this be conditional on `sys.platform == "linux"` or unconditional?

---

## Section 7 -- Cascade clear behavior (Linux bug)

**Symptom:** On Linux, clicking Clear doesn't actually clear the slots.

**Root cause analysis:** `_on_clear_all_slots` (line 4961) does:
1. Confirms via `QMessageBox.question`
2. Calls `info["widget"].deleteLater()` for each slot widget
3. Clears `_slot_widgets`, `_slot_buttons`, `_arrow_buttons` lists
4. Creates new empty `_slots` list
5. Calls `_add_slot_widget(i)` for each new slot (inserts into `_slots_container`)
6. Calls `_refresh_button_labels()`, `_update_add_button_state()`, `_update_remove_button_state()`
7. Calls `_save_cascade()` (persists empty state to QSettings)

**Verified behavior (Windows):** Clear works correctly -- slots reset to `(empty)`, QSettings updated.

**Key observation:** After clear, `_slots_container.count()` was **6**, not the expected **4** (2 new slot widgets + Add Step button + stretch). The extra 2 are the **old slot widgets still pending `deleteLater()`**. On Windows, these ghost widgets are invisible and get destroyed in the next event loop cycle. On Linux/X11, the event loop timing may differ:

- `deleteLater()` defers destruction until the next event loop iteration
- `_add_slot_widget()` calls `_slots_container.insertWidget(insert_pos, ...)` where `insert_pos = len(self._slot_widgets)` (0, then 1)
- The old widgets are still in the layout at positions 0 and 1 (not yet destroyed)
- The new widgets are inserted at positions 0 and 1, pushing old ones down
- If the layout renders before `deleteLater()` fires, the old (populated) widgets may be visible on top of or alongside the new (empty) ones
- No `processEvents()` is called between `deleteLater()` and `_add_slot_widget()`

**What's built:** The data model (`_slots`, `_slot_buttons`, etc.) is correctly cleared and rebuilt. `_save_cascade()` persists the correct empty state.
**What's missing:** Either:
- Call `app.processEvents()` after the `deleteLater()` loop and before creating new widgets, to force destruction, OR
- Use `widget.setParent(None)` or remove from layout explicitly before `deleteLater()`, OR
- Hide old widgets immediately with `widget.hide()` before `deleteLater()`

**Confidence:** MEDIUM -- clear works correctly on Windows. The layout count anomaly (6 vs 4) confirms ghost widgets exist. The Linux failure mode is inferred from Qt `deleteLater()` semantics on X11 but not directly reproduced.

**Open questions for fix:**
- Is `widget.hide()` before `deleteLater()` sufficient, or should `_slots_container.removeWidget(widget)` be called?
- Does `_load_cascade()` have the same issue? (Yes -- it also uses `deleteLater()` at line 4523 without `processEvents()` or `hide()`)
- Are there other places in the codebase where `deleteLater()` + immediate widget creation could cause similar ghost-widget issues on Linux?

---

## Summary Table

| # | Issue | Root Cause | Confidence | Platform |
|---|-------|-----------|------------|----------|
| 1 | Hamburger extra caret | No `QToolButton::menu-indicator` suppression in QSS | HIGH | All |
| 2 | Save cascade by name | Already implemented; no current-name tracking attribute | HIGH | All |
| 3 | Required-field cascade abort | `_load_tool_path` replaces form; no preset = empty required fields | HIGH | All |
| 4 | Tooltip wrapping | Button tooltips are plain text, not rich text | HIGH | All |
| 5 | "Running..." cutoff | Button too narrow (67px) for "Running..." text in 3-button row | HIGH | All |
| 6 | Linux tooltip colors | Light mode trusts OS palette; no explicit tooltip colors | MEDIUM | Linux |
| 7 | Linux clear bug | `deleteLater()` ghost widgets visible before event loop processes | MEDIUM | Linux |
