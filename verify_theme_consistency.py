#!/usr/bin/env python3
"""Verify dark mode QSS achieves visual consistency with light mode.

Loads the nmap schema, captures sizeHint().height() and contentsMargins()
for each widget type in both light and dark mode, prints a comparison table,
and flags any widget where the height difference exceeds 2px.

Also verifies that every border rule in the dark QSS has a matching
border-radius.
"""

import re
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox,
    QLineEdit, QPlainTextEdit, QSpinBox,
)

app = QApplication(sys.argv)

sys.path.insert(0, str(Path(__file__).parent))
import scaffold

NMAP = Path(__file__).parent / "tools" / "nmap.json"
EXAMPLE = Path(__file__).parent / "tools" / "example.json"

passed = 0
failed = 0

def check(cond, label):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")


# ------------------------------------------------------------------
# Part 1: sizeHint height comparison
# ------------------------------------------------------------------
print("=== Widget sizeHint Height Comparison ===")

nmap_data = scaffold.load_tool(NMAP)
example_data = scaffold.load_tool(EXAMPLE)

# Collect one specimen per widget class from form fields
def collect_specimens(form):
    """Return dict of {widget_class_name: widget} for unique widget types."""
    specimens = {}
    for key, field in form.fields.items():
        w = field["widget"]
        cls = type(w).__name__
        if cls not in specimens:
            specimens[cls] = w
    return specimens


# Light mode measurements
scaffold.apply_theme(False)
app.processEvents()

form_light_nmap = scaffold.ToolForm(nmap_data)
form_light_nmap.resize(700, 750)
app.processEvents()
form_light_example = scaffold.ToolForm(example_data)
form_light_example.resize(700, 750)
app.processEvents()

light_specimens = collect_specimens(form_light_nmap)
light_specimens.update(collect_specimens(form_light_example))

light_heights = {}
light_margins = {}
for cls, w in light_specimens.items():
    light_heights[cls] = w.sizeHint().height()
    m = w.contentsMargins()
    light_margins[cls] = (m.left(), m.top(), m.right(), m.bottom())


# Dark mode measurements
scaffold.apply_theme(True)
app.processEvents()

form_dark_nmap = scaffold.ToolForm(nmap_data)
form_dark_nmap.resize(700, 750)
app.processEvents()
form_dark_example = scaffold.ToolForm(example_data)
form_dark_example.resize(700, 750)
app.processEvents()

dark_specimens = collect_specimens(form_dark_nmap)
dark_specimens.update(collect_specimens(form_dark_example))

dark_heights = {}
dark_margins = {}
for cls, w in dark_specimens.items():
    dark_heights[cls] = w.sizeHint().height()
    m = w.contentsMargins()
    dark_margins[cls] = (m.left(), m.top(), m.right(), m.bottom())


# Print comparison table
TARGET_CLASSES = ["QCheckBox", "QLineEdit", "QSpinBox", "QDoubleSpinBox", "QComboBox", "QPlainTextEdit"]

print()
print(f"  {'Widget':20s} | {'Light H':>8s} {'Dark H':>8s} {'Delta':>6s} | {'Light Margins':>20s} {'Dark Margins':>20s} {'Match':>6s}")
print(f"  {'-'*20} | {'-'*8} {'-'*8} {'-'*6} | {'-'*20} {'-'*20} {'-'*6}")

for cls in TARGET_CLASSES:
    lh = light_heights.get(cls, "?")
    dh = dark_heights.get(cls, "?")
    lm = light_margins.get(cls, "?")
    dm = dark_margins.get(cls, "?")
    if isinstance(lh, int) and isinstance(dh, int):
        delta = dh - lh
        delta_str = f"{delta:+d}"
    else:
        delta = None
        delta_str = "?"
    margin_match = "Yes" if lm == dm else "No"
    print(f"  {cls:20s} | {str(lh):>8s} {str(dh):>8s} {delta_str:>6s} | {str(lm):>20s} {str(dm):>20s} {margin_match:>6s}")

# Check height deltas
print()
for cls in TARGET_CLASSES:
    lh = light_heights.get(cls)
    dh = dark_heights.get(cls)
    if lh is not None and dh is not None:
        delta = abs(dh - lh)
        check(delta <= 2, f"{cls} height delta <= 2px (got {dh - lh:+d})")


# ------------------------------------------------------------------
# Part 2: QGroupBox border-radius verification
# ------------------------------------------------------------------
print()
print("=== QGroupBox Border-Radius Verification ===")

# Check that the dark QSS includes border-radius for QGroupBox
dark_qss = QApplication.instance().styleSheet()
gb_rules = re.findall(r'QGroupBox\s*\{([^}]+)\}', dark_qss)
has_radius = any("border-radius" in rule for rule in gb_rules)
check(has_radius, "QGroupBox dark QSS has border-radius")

if gb_rules:
    for rule in gb_rules:
        radius_match = re.search(r'border-radius:\s*(\d+)px', rule)
        if radius_match:
            check(int(radius_match.group(1)) >= 3, f"QGroupBox border-radius >= 3px (got {radius_match.group(1)}px)")


# ------------------------------------------------------------------
# Part 3: Every border rule has border-radius
# ------------------------------------------------------------------
print()
print("=== Border / Border-Radius Coverage ===")

rules = re.findall(r'([^{}]+)\{([^}]+)\}', dark_qss)
for selector, body in rules:
    selector = selector.strip()
    has_border = bool(re.search(r'\bborder:\s', body))
    has_border_radius = "border-radius" in body
    # Sub-controls (::indicator, ::up-button, etc.) and pseudo-states (:hover)
    # don't need border-radius — only main widget selectors do
    is_subcontrol = "::" in selector or ":hover" in selector or ":pressed" in selector or ":checked" in selector or ":selected" in selector
    # Item views and table headers are rectangular by convention
    is_rectangular = "QHeaderView" in selector or "QAbstractItemView" in selector
    if has_border and not is_subcontrol and not is_rectangular:
        check(has_border_radius, f"{selector} has border-radius alongside border")


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print()
print(f"{'='*60}")
print(f"THEME CONSISTENCY: {passed}/{passed+failed} passed, {failed} failed")
print(f"{'='*60}")
