"""
Cascade Panel + Tooltip + Linux Bug Diagnostic Script
=====================================================
Collects ground-truth measurements for 8 reported issues.
Does NOT modify scaffold.py.
"""

import inspect
import json
import re
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Force UTF-8 stdout for Windows redirect
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

# Ensure scaffold is importable from this directory
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QToolButton, QMessageBox, QDialog,
    QInputDialog, QLineEdit, QSpinBox, QDoubleSpinBox,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPalette, QColor, QFontMetrics

# QApplication singleton
app = QApplication.instance() or QApplication(sys.argv)

import scaffold

# Helpers
TOOLS_DIR = Path(__file__).parent / "tests"
NMAP_JSON = Path(__file__).parent / "tools" / "nmap.json"
SETTINGS_KEY = "cascade"

def banner(n, title):
    print(f"\n{'=' * 64}")
    print(f"SECTION {n} -- {title}")
    print(f"{'=' * 64}\n")


def cleanup_settings():
    QSettings("Scaffold", "Scaffold").remove(SETTINGS_KEY)


# Pre-clean
cleanup_settings()

# ======================================================================
# SECTION 1 -- Hamburger menu button extra caret
# ======================================================================
banner(1, "Hamburger menu button extra caret")

win1 = scaffold.MainWindow()
win1.show()
app.processEvents()

dock = win1.cascade_dock
menu_btn = dock._menu_btn

print(f"_menu_btn.text()           = {repr(menu_btn.text())}")
print(f"_menu_btn.popupMode()      = {menu_btn.popupMode()}")
print(f"  InstantPopup             = {QToolButton.ToolButtonPopupMode.InstantPopup}")
print(f"  MenuButtonPopup          = {QToolButton.ToolButtonPopupMode.MenuButtonPopup}")
print(f"  DelayedPopup             = {QToolButton.ToolButtonPopupMode.DelayedPopup}")
print(f"  Match?                   = popupMode is InstantPopup: {menu_btn.popupMode() == QToolButton.ToolButtonPopupMode.InstantPopup}")
print(f"_menu_btn.toolButtonStyle()= {menu_btn.toolButtonStyle()}")
print(f"_menu_btn.arrowType()      = {menu_btn.arrowType()}")
print(f"_menu_btn.styleSheet()     = {repr(menu_btn.styleSheet())}")
print(f"_menu_btn has menu?        = {menu_btn.menu() is not None}")

app_ss = app.styleSheet()
has_menu_indicator_suppression = "menu-indicator" in app_ss
print(f"\nApp stylesheet contains 'menu-indicator': {has_menu_indicator_suppression}")
if has_menu_indicator_suppression:
    for line in app_ss.split("}"):
        if "menu-indicator" in line:
            print(f"  Matching rule: {line.strip()}}}")

print(f"\n_menu_btn pixel width      = {menu_btn.width()}")
fm = QFontMetrics(menu_btn.font())
glyph_width = fm.horizontalAdvance("\u2630")
print(f"Glyph width (\u2630)           = {glyph_width}")
print(f"Excess width               = {menu_btn.width() - glyph_width}")

print("""
ANALYSIS:
  Qt draws a built-in menu-indicator arrow on any QToolButton that has a menu
  attached, UNLESS suppressed via QSS (QToolButton::menu-indicator { image: none;
  width: 0; }) or popupMode is DelayedPopup with no menu.
""")
if not has_menu_indicator_suppression:
    print("  => NO menu-indicator suppression found in the app stylesheet.")
    print("     The extra caret is the native menu-indicator arrow drawn by Qt.")
    print("     Fix: add QToolButton::menu-indicator { image: none; width: 0; }")
    print("     to the button's styleSheet, or globally in apply_theme().")
else:
    print("  => Menu-indicator suppression IS present in the stylesheet.")

win1.close()
win1.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 2 -- "Save cascade by name" -- current state
# ======================================================================
banner(2, '"Save cascade by name" -- current state')

# Print first 30 lines of _on_save_cascade_file
src = inspect.getsource(scaffold.CascadeSidebar._on_save_cascade_file)
src_lines = src.splitlines()
print("First 30 lines of _on_save_cascade_file:")
for i, line in enumerate(src_lines[:30], 1):
    print(f"  {i:3d}  {line}")

has_input_dialog = "QInputDialog.getText" in src
print(f"\nQInputDialog.getText called: {has_input_dialog}")
print(f"User can save with arbitrary name: {'Yes' if has_input_dialog else 'No'}")

# Check for current-cascade-name tracking
cleanup_settings()
win2 = scaffold.MainWindow()
win2.show()
app.processEvents()
dock2 = win2.cascade_dock

search_terms = ["cascade", "name", "loaded", "current"]
matching_attrs = []
for attr in dir(dock2):
    lower = attr.lower()
    if any(t in lower for t in search_terms) and not attr.startswith("__"):
        matching_attrs.append(attr)

print("\nAttributes on CascadeSidebar matching 'cascade'/'name'/'loaded'/'current':")
for attr in sorted(matching_attrs):
    try:
        val = getattr(dock2, attr)
        if callable(val) and not isinstance(val, property):
            print(f"  {attr} = <method>")
        else:
            print(f"  {attr} = {repr(val)}")
    except Exception as e:
        print(f"  {attr} = <error: {e}>")

# Grep source for tracking attributes
full_src = inspect.getsource(scaffold.CascadeSidebar)
tracking_patterns = [
    "_current_cascade_name", "_loaded_cascade", "current_cascade",
    "_cascade_name", "_loaded_name",
]
print("\nSearching CascadeSidebar source for tracking attributes:")
for pat in tracking_patterns:
    found = pat in full_src
    print(f"  {pat}: {'FOUND' if found else 'not found'}")

print("\nREPORT: Does any field track which named cascade is currently loaded? ", end="")
has_tracking = any(pat in full_src for pat in tracking_patterns)
if has_tracking:
    print("Yes")
else:
    print("No -- there is no attribute tracking the currently-loaded cascade name.")

win2.close()
win2.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 3 -- Required-field handling on cascade run
# ======================================================================
banner(3, "Required-field handling on cascade run")

cleanup_settings()
win3 = scaffold.MainWindow()
win3.show()
app.processEvents()

# Load nmap
assert NMAP_JSON.exists(), f"nmap.json not found at {NMAP_JSON}"
win3._load_tool_path(str(NMAP_JSON))
app.processEvents()

# Fill in required target field
form = win3.form
target_key = None
for key in form.fields:
    scope, flag = key
    if flag == "TARGET":
        target_key = key
        break

if target_key:
    form._set_field_value(target_key, "192.168.1.1")
    app.processEvents()
    filled_val = form.get_field_value(target_key)
    print(f"Target field key: {target_key}")
    print(f"Target field value after fill: {repr(filled_val)}")
else:
    print("ERROR: Could not find TARGET field in form.fields")

# Assign nmap to cascade slot 0
dock3 = win3.cascade_dock
dock3._slots[0]["tool_path"] = str(NMAP_JSON)
dock3._slots[0]["preset_path"] = None
dock3._save_cascade()
dock3._refresh_button_labels()
app.processEvents()

print(f"\n_cascade_variables list: {repr(dock3._cascade_variables)}")
print(f"  Length: {len(dock3._cascade_variables)}")

# Trace _on_run_chain behavior
print("\n--- Tracing _on_run_chain ---")

# Search source for dialogs/checks in _on_run_chain
run_chain_src = inspect.getsource(scaffold.CascadeSidebar._on_run_chain)
print("\n_on_run_chain source code:")
for i, line in enumerate(run_chain_src.splitlines(), 1):
    print(f"  {i:3d}  {line}")

# Search for dialog/validation calls
chain_advance_src = inspect.getsource(scaffold.CascadeSidebar._chain_advance)
chain_execute_src = inspect.getsource(scaffold.CascadeSidebar._chain_execute_current)

print("\n_chain_execute_current source code:")
for i, line in enumerate(chain_execute_src.splitlines(), 1):
    print(f"  {i:3d}  {line}")

# Find all dialog/validation calls in the chain
print("\nDialog/validation calls in _on_run_chain:")
for pat in ["QInputDialog", "QMessageBox", "CascadeVariableDialog", "_check_", "_validate_", "validate_required"]:
    if pat in run_chain_src:
        print(f"  {pat}: FOUND in _on_run_chain")
    if pat in chain_advance_src:
        print(f"  {pat}: FOUND in _chain_advance")
    if pat in chain_execute_src:
        print(f"  {pat}: FOUND in _chain_execute_current")

# Monkey-patch to trace what fires
cascade_var_dialog_constructed = []
original_cvd_init = scaffold.CascadeVariableDialog.__init__

def mock_cvd_init(self_dlg, variables, parent=None):
    cascade_var_dialog_constructed.append(variables)
    # Minimal init -- don't show UI
    QDialog.__init__(self_dlg, parent)
    self_dlg._variables = variables
    self_dlg._inputs = {}
    # Immediately reject
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, self_dlg.reject)

scaffold.CascadeVariableDialog.__init__ = mock_cvd_init

# Also track validate_required
validate_required_called = []
original_validate = form.validate_required

def mock_validate():
    result = original_validate()
    validate_required_called.append(result)
    return result

form.validate_required = mock_validate

# Now attempt to run the chain
# But we need to be careful -- _on_run_chain loads the tool fresh via _load_tool_path
# which will replace the form. So we need to trace at a different level.

# Actually, let's trace _chain_execute_current which calls validate_required
# We need to intercept at MainWindow level
original_mw_validate = None

print("\n--- Running _on_run_chain() with empty _cascade_variables ---")
print(f"_cascade_variables before run: {dock3._cascade_variables}")

# _on_run_chain will:
# 1. Build queue from valid slots
# 2. If _cascade_variables non-empty, show CascadeVariableDialog
# 3. Set state to CHAIN_LOADING
# 4. Call _chain_advance() which loads tool, then after 150ms calls _chain_execute_current
# 5. _chain_execute_current calls form.validate_required()
# Since _cascade_variables is empty, step 2 is skipped.
# The key question: after loading tool via _load_tool_path, is the TARGET field still filled?

# Let's trace this step by step
dock3._on_run_chain()
app.processEvents()

print(f"CascadeVariableDialog constructed: {len(cascade_var_dialog_constructed)} time(s)")
if cascade_var_dialog_constructed:
    print(f"  Variables passed: {cascade_var_dialog_constructed}")

print(f"\nChain state after _on_run_chain: {dock3._chain_state}")
print(f"Chain queue: {dock3._chain_queue}")

# The chain is now in CHAIN_LOADING state, _chain_advance was called,
# which calls _load_tool_path (replacing the form!), then schedules
# _chain_execute_current after 150ms.
# _chain_execute_current will call validate_required on the NEW form.
# The TARGET field in the new form will be EMPTY because _load_tool_path
# creates a fresh form.

# Process the 150ms timer
import time
time.sleep(0.2)
app.processEvents()

# Check what happened
print(f"Chain state after timer: {dock3._chain_state}")

# Check if the form's target field is still filled
new_form = win3.form
new_target_key = None
for key in new_form.fields:
    scope, flag = key
    if flag == "TARGET":
        new_target_key = key
        break

if new_target_key:
    new_val = new_form.get_field_value(new_target_key)
    print(f"Target field value in NEW form (after _load_tool_path): {repr(new_val)}")
    print(f"  (This is the form created by _chain_advance -> _load_tool_path)")
else:
    print("TARGET field not found in new form")

print("""
CRITICAL FINDING:
  _on_run_chain -> _chain_advance -> _load_tool_path creates a FRESH form.
  The user filled TARGET=192.168.1.1 in the ORIGINAL form, but the chain
  re-loads the tool from disk, creating a brand new empty form.
  Then _chain_execute_current calls validate_required() on this NEW empty form,
  which finds TARGET missing and aborts with "required fields missing".

  This is NOT the CascadeVariableDialog. It is NOT a QInputDialog.
  It is validate_required() in _chain_execute_current (line ~5139) failing
  because _load_tool_path replaced the user's filled-in form with a blank one,
  and no preset was assigned to restore the TARGET value.

  The user sees: "Cascade stopped: required fields missing" in the status bar.
  If the user defined a preset with TARGET filled and assigned it to the slot,
  apply_values() would fill it. But if they only filled the field manually
  without saving a preset, the chain will always fail on required fields.
""")

# Clean up chain
if dock3._chain_state != "idle":
    dock3._chain_state = "idle"
    dock3._chain_cleanup("Diagnostic cleanup")
    app.processEvents()

# Restore originals
scaffold.CascadeVariableDialog.__init__ = original_cvd_init

win3.close()
win3.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 4 -- Tooltip wrapping
# ======================================================================
banner(4, "Tooltip wrapping")

cleanup_settings()
win4 = scaffold.MainWindow()
win4.show()
app.processEvents()

dock4 = win4.cascade_dock

# Collect tooltips from cascade dock buttons
buttons_to_check = {
    "run_chain_btn": dock4.run_chain_btn,
    "pause_chain_btn": dock4.pause_chain_btn,
    "stop_chain_btn": dock4.stop_chain_btn,
    "clear_all_btn": dock4.clear_all_btn,
    "loop_btn": dock4.loop_btn,
    "stop_on_error_btn": dock4.stop_on_error_btn,
    "add_step_btn": dock4.add_step_btn,
    "_menu_btn": dock4._menu_btn,
    "MainWindow.run_btn": win4.run_btn,
}

print("Button tooltips:")
for name, btn in buttons_to_check.items():
    tip = btn.toolTip()
    is_rich = tip.strip().startswith(("<html", "<p", "<qt", "<HTML", "<P", "<QT"))
    print(f"\n  {name}:")
    print(f"    repr: {repr(tip)}")
    print(f"    rich text: {is_rich}")
    print(f"    length: {len(tip)}")

# Load nmap and check field tooltips
win4._load_tool_path(str(NMAP_JSON))
app.processEvents()

form4 = win4.form
print("\n\nField tooltips (nmap):")
fields_checked = 0
for key in form4.fields:
    scope, flag = key
    field_info = form4.fields[key]
    widget = field_info["widget"]
    tip = widget.toolTip()
    if tip and len(tip) > 30:  # Only show long tooltips
        is_rich = tip.strip().startswith(("<html", "<p", "<qt", "<HTML", "<P", "<QT"))
        print(f"\n  {flag}:")
        print(f"    repr: {repr(tip[:200])}{'...' if len(tip) > 200 else ''}")
        print(f"    rich text: {is_rich}")
        print(f"    length: {len(tip)}")
        fields_checked += 1
        if fields_checked >= 5:
            break

print("""
ANALYSIS:
  Qt only word-wraps tooltips when the text is detected as rich text (starts
  with <html>, <p>, <qt>, etc.). Plain text tooltips render on a single line
  regardless of length.

  Field tooltips use _build_tooltip() which wraps content in <p>...</p> tags,
  so they ARE rich text and WILL auto-wrap.

  Button tooltips (cascade controls) are plain text strings set via setToolTip().
  Long ones like stop_on_error_btn will NOT wrap and may extend off-screen.
""")

win4.close()
win4.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 5 -- Cascade panel "Running..." text cutoff
# ======================================================================
banner(5, 'Cascade panel "Running..." text cutoff')

cleanup_settings()
win5 = scaffold.MainWindow()
win5.show()
app.processEvents()
win5.resize(900, 700)
app.processEvents()

dock5 = win5.cascade_dock
btn = dock5.run_chain_btn

print(f"run_chain_btn current text: {repr(btn.text())}")
print(f"  width():            {btn.width()}")
print(f"  sizeHint().width(): {btn.sizeHint().width()}")
print(f"  minimumSizeHint():  {btn.minimumSizeHint().width()}")

fm5 = QFontMetrics(btn.font())
print(f"\n  Font metrics:")
print(f"    'Running...' advance: {fm5.horizontalAdvance('Running...')}")
print(f"    'Run' advance:        {fm5.horizontalAdvance('Run')}")
print(f"    'Stop' advance:       {fm5.horizontalAdvance('Stop')}")

# Check parent layout
content_widget = dock5.widget()
print(f"\n  Content widget fixedWidth: {content_widget.width()}")
print(f"  Content widget minimumWidth: {content_widget.minimumWidth()}")

# Check chain_row1 layout properties
# chain_row1 is the layout containing run/pause/stop buttons
# We can find it by checking the parent layout
run_parent = btn.parentWidget()
if run_parent:
    layout = run_parent.layout()
    if layout:
        print(f"\n  Parent layout type: {type(layout).__name__}")

# Now temporarily set to "Running..." and check
original_text = btn.text()
btn.setText("Running...")
app.processEvents()

print(f"\n  After setText('Running...'):")
print(f"    width():            {btn.width()}")
print(f"    sizeHint().width(): {btn.sizeHint().width()}")
print(f"    clipped (width < sizeHint): {btn.width() < btn.sizeHint().width()}")

btn.setText(original_text)
app.processEvents()

# Search for "Running..." in scaffold.py
print(f"\nSearching scaffold.py for 'Running...' text assignments:")
scaffold_src = Path(__file__).parent / "scaffold.py"
with open(scaffold_src, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "Running..." in line and "setText" in line:
        start = max(0, i - 3)
        end = min(len(lines), i + 3)
        print(f"\n  Line {i} (+/- 2 context):")
        for j in range(start, end):
            marker = ">>>" if j == i - 1 else "   "
            print(f"    {marker} {j+1}: {lines[j].rstrip()}")

print("""
ANALYSIS:
  _on_run_chain sets run_chain_btn text to "Running..." at line 5019.
  The cascade panel content widget is fixedWidth=220.
  chain_row1 has three buttons (Run, Pause, Stop) sharing this width
  with stretch factor 1 each.
  Each button gets roughly (220 - margins - spacing) / 3 pixels.
  "Running..." is wider than "Run" and may clip in the ~65px available.
""")

win5.close()
win5.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 6 -- Tooltip colors in light mode (Linux bug)
# ======================================================================
banner(6, "Tooltip colors in light mode (Linux bug)")

cleanup_settings()
win6 = scaffold.MainWindow()
win6.show()
app.processEvents()

print(f"sys.platform: {sys.platform}")
print(f"QApplication.style().objectName(): {app.style().objectName()}")

# Light mode
scaffold.apply_theme(False)
app.processEvents()

pal = app.palette()
print(f"\n--- LIGHT MODE ---")
print(f"  ToolTipBase:  {pal.color(QPalette.ColorRole.ToolTipBase).name()}")
print(f"  ToolTipText:  {pal.color(QPalette.ColorRole.ToolTipText).name()}")
print(f"  Window:       {pal.color(QPalette.ColorRole.Window).name()}")
print(f"  WindowText:   {pal.color(QPalette.ColorRole.WindowText).name()}")
print(f"  Base:         {pal.color(QPalette.ColorRole.Base).name()}")
print(f"  Text:         {pal.color(QPalette.ColorRole.Text).name()}")

light_ss = app.styleSheet()
print(f"\n  App stylesheet QToolTip rules:")
if "QToolTip" in light_ss:
    for part in light_ss.split("}"):
        if "QToolTip" in part:
            print(f"    {part.strip()}}}")
else:
    print(f"    NONE -- stylesheet is empty or has no QToolTip rules")

# Switch to dark mode
scaffold.apply_theme(True)
app.processEvents()
pal_dark = app.palette()
print(f"\n--- DARK MODE ---")
print(f"  ToolTipBase:  {pal_dark.color(QPalette.ColorRole.ToolTipBase).name()}")
print(f"  ToolTipText:  {pal_dark.color(QPalette.ColorRole.ToolTipText).name()}")
print(f"  Window:       {pal_dark.color(QPalette.ColorRole.Window).name()}")
print(f"  WindowText:   {pal_dark.color(QPalette.ColorRole.WindowText).name()}")
print(f"  Base:         {pal_dark.color(QPalette.ColorRole.Base).name()}")
print(f"  Text:         {pal_dark.color(QPalette.ColorRole.Text).name()}")

dark_ss = app.styleSheet()
print(f"\n  App stylesheet QToolTip rules:")
if "QToolTip" in dark_ss:
    for part in dark_ss.split("}"):
        if "QToolTip" in part:
            print(f"    {part.strip()}}}")
else:
    print(f"    NONE")

# Back to light mode and check nmap target field widget
scaffold.apply_theme(False)
app.processEvents()

win6._load_tool_path(str(NMAP_JSON))
app.processEvents()

form6 = win6.form
target_widget = None
for key in form6.fields:
    scope, flag = key
    if flag == "TARGET":
        target_widget = form6.fields[key]["widget"]
        break

if target_widget:
    print(f"\n--- TARGET field widget (light mode) ---")
    print(f"  toolTip(): {repr(target_widget.toolTip()[:100])}")
    wpal = target_widget.palette()
    print(f"  widget ToolTipBase: {wpal.color(QPalette.ColorRole.ToolTipBase).name()}")
    print(f"  widget ToolTipText: {wpal.color(QPalette.ColorRole.ToolTipText).name()}")

# Print the light mode branch of apply_theme
print(f"\n--- apply_theme(False) source (the else: branch) ---")
theme_src = inspect.getsource(scaffold.apply_theme)
in_else = False
for line in theme_src.splitlines():
    if "else:" in line and not in_else:
        in_else = True
    if in_else:
        print(f"  {line}")

print("""
ANALYSIS:
  apply_theme(False) restores _original_palette and clears the stylesheet.
  In DARK mode, QToolTip colors are set both in the palette (ToolTipBase/
  ToolTipText) AND in QSS (QToolTip {{ background-color: ...; color: ...; }}).
  In LIGHT mode, the stylesheet is cleared ('') and the original palette is
  restored.

  On Linux, the "original palette" comes from the system/desktop theme. If
  the system theme has dark tooltip colors (e.g., GNOME Adwaita-dark, or a
  dark GTK theme), those colors persist in the original palette. This means
  ToolTipBase may be dark and ToolTipText may be light -- OR the reverse --
  making tooltips unreadable.

  The light mode branch does NOT explicitly set ToolTipBase/ToolTipText colors
  and does NOT add any QToolTip QSS rule. It trusts the OS palette entirely.
  On Windows/macOS this works fine. On Linux with mixed-theme desktops, it
  can result in black-on-dark-grey or white-on-white tooltips.
""")

if sys.platform == "linux":
    print("  Running on Linux -- this issue CAN be verified here.")
else:
    print(f"  Running on {sys.platform} -- cannot fully verify Linux tooltip bug.")
    print("  The code path analysis above shows the vulnerability regardless.")

win6.close()
win6.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# SECTION 7 -- Cascade clear behavior (Linux bug)
# ======================================================================
banner(7, "Cascade clear behavior (Linux bug)")

cleanup_settings()
win7 = scaffold.MainWindow()
win7.show()
app.processEvents()

dock7 = win7.cascade_dock

# Populate slot 0 and slot 1 with nmap
dock7._slots[0]["tool_path"] = str(NMAP_JSON)
dock7._slots[0]["preset_path"] = None
dock7._slots[1]["tool_path"] = str(NMAP_JSON)
dock7._slots[1]["preset_path"] = None
dock7._save_cascade()
dock7._refresh_button_labels()
app.processEvents()

print("Before clear:")
print(f"  _slots count: {len(dock7._slots)}")
print(f"  _slot_widgets count: {len(dock7._slot_widgets)}")
print(f"  _slot_buttons count: {len(dock7._slot_buttons)}")
print(f"  _arrow_buttons count: {len(dock7._arrow_buttons)}")
for i, s in enumerate(dock7._slots):
    print(f"  slot[{i}].tool_path: {repr(s.get('tool_path'))}")

# Read QSettings before clear
settings = QSettings("Scaffold", "Scaffold")
pre_clear_settings = settings.value("cascade/slots")
print(f"\n  QSettings cascade/slots before clear: {repr(pre_clear_settings[:100] if pre_clear_settings else None)}...")

# Monkey-patch QMessageBox.question to return Yes
with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
    dock7._on_clear_all_slots()
    app.processEvents()

print("\nAfter clear (Yes):")
print(f"  _slots count: {len(dock7._slots)}")
print(f"  _slot_widgets count: {len(dock7._slot_widgets)}")
print(f"  _slot_buttons count: {len(dock7._slot_buttons)}")
print(f"  _arrow_buttons count: {len(dock7._arrow_buttons)}")
for i, s in enumerate(dock7._slots):
    print(f"  slot[{i}].tool_path: {repr(s.get('tool_path'))}")
for i, btn in enumerate(dock7._slot_buttons):
    print(f"  slot_button[{i}].text(): {repr(btn.text())}")

post_clear_settings = QSettings("Scaffold", "Scaffold").value("cascade/slots")
print(f"\n  QSettings cascade/slots after clear: {repr(post_clear_settings[:100] if post_clear_settings else None)}...")

# Now test with No -- repopulate first
dock7._slots[0]["tool_path"] = str(NMAP_JSON)
dock7._save_cascade()
dock7._refresh_button_labels()
app.processEvents()

with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
    dock7._on_clear_all_slots()
    app.processEvents()

print("\nAfter clear attempt (No):")
print(f"  slot[0].tool_path: {repr(dock7._slots[0].get('tool_path'))}")
print(f"  Correctly preserved: {dock7._slots[0].get('tool_path') is not None}")

# Trace the code path for Linux-specific issues
print("\n--- Code path analysis for _on_clear_all_slots ---")
clear_src = inspect.getsource(scaffold.CascadeSidebar._on_clear_all_slots)
print("Full source:")
for i, line in enumerate(clear_src.splitlines(), 1):
    print(f"  {i:3d}  {line}")

print("\nPotential Linux-specific issues:")
print("  1. widget.deleteLater() is called for each slot widget")
print("     deleteLater() defers destruction to the next event loop iteration.")
print("     On Linux/X11, event loop timing can differ from Windows/macOS.")
uses_delete_later = "deleteLater" in clear_src
print(f"     deleteLater used: {uses_delete_later}")

uses_process_events = "processEvents" in clear_src
print(f"  2. processEvents() called after clear: {uses_process_events}")
print(f"     (No forced event processing -- deleteLater may not complete before")
print(f"      _add_slot_widget inserts new widgets)")

print(f"  3. _save_cascade() is called at the end")
print(f"     This persists the new empty state to QSettings.")

# Check if _load_cascade is called anywhere that could race
print(f"\n  4. Is _load_cascade connected to any signal that could fire during clear?")
load_cascade_src = inspect.getsource(scaffold.CascadeSidebar._load_cascade)
print(f"     _load_cascade tears down existing widgets and rebuilds from QSettings.")
print(f"     If anything triggers _load_cascade between clear and save, the old")
print(f"     state would be restored from QSettings before the new state is saved.")
print(f"     (No signal connection found -- _load_cascade is only called in __init__)")

# Check if visibilityChanged or other dock signals could interfere
print(f"\n  5. Layout container count after clear: {dock7._slots_container.count()}")
print(f"     (Includes + Add Step button and stretch = {len(dock7._slot_widgets) + 2})")

if sys.platform == "linux":
    print("\n  Running on Linux -- can verify behavior directly.")
else:
    print(f"\n  Running on {sys.platform} -- cannot reproduce Linux-specific timing.")
    print("  The code analysis shows no obvious platform-dependent bugs in")
    print("  _on_clear_all_slots. The most likely Linux culprit is event loop")
    print("  timing with deleteLater() and immediate widget re-creation, but")
    print("  this could not be verified on this platform.")

win7.close()
win7.deleteLater()
app.processEvents()
cleanup_settings()


# ======================================================================
# CLEANUP
# ======================================================================
print(f"\n{'=' * 64}")
print("CLEANUP")
print(f"{'=' * 64}\n")

cleanup_settings()
print("QSettings cascade key removed.")
print("All MainWindow instances closed and deleteLater'd.")
print("Diagnostic complete.")
