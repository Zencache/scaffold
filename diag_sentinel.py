"""
Diagnostic 1 — Sentinel system probe (C2, C3, M4, TG1, TG5)

Constructs ToolForms for five schemas with various integer/float min/max
combinations and reports exact widget state, _is_field_active(), get_field_value(),
and build_command() at initial and programmatically-set positions.

DO NOT MODIFY scaffold.py — this is a read-only diagnostic.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

# Must create QApplication before importing scaffold widgets
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

sys.path.insert(0, str(Path(__file__).parent))
import scaffold


# ---------------------------------------------------------------------------
# Helper: build a single-argument tool schema
# ---------------------------------------------------------------------------
def make_tool(name, arg_type, min_val, max_val, default=None, flag="--val"):
    return {
        "_format": "scaffold_schema",
        "tool": name, "binary": "echo", "description": "Diagnostic",
        "subcommands": None, "elevated": None,
        "arguments": [{
            "name": "Val", "flag": flag, "type": arg_type,
            "description": "test", "required": False, "default": default,
            "choices": None, "group": None, "depends_on": None,
            "repeatable": False, "separator": "space", "positional": False,
            "validation": None, "examples": None, "min": min_val, "max": max_val,
        }],
    }


# ---------------------------------------------------------------------------
# Helper: probe a form and return a dict of results
# ---------------------------------------------------------------------------
def probe(form, key, label):
    w = form.fields[key]["widget"]
    active = form._is_field_active(key)
    val = form.get_field_value(key)
    cmd, display = form.build_command()
    return {
        "label": label,
        "widget_min": w.minimum(),
        "widget_max": w.maximum(),
        "widget_value": w.value(),
        "specialValueText": repr(w.specialValueText()),
        "is_field_active": active,
        "get_field_value": val,
        "build_command": cmd,
    }


def fmt_probe(p):
    lines = []
    lines.append(f"  [{p['label']}]")
    lines.append(f"    widget.minimum()       = {p['widget_min']}")
    lines.append(f"    widget.maximum()       = {p['widget_max']}")
    lines.append(f"    widget.value()         = {p['widget_value']}")
    lines.append(f"    specialValueText()     = {p['specialValueText']}")
    lines.append(f"    _is_field_active()     = {p['is_field_active']}")
    lines.append(f"    get_field_value()      = {p['get_field_value']}")
    lines.append(f"    build_command()        = {p['build_command']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Float-specific diagnostics
# ---------------------------------------------------------------------------
def float_probe_extra(form, key, schema_min):
    w = form.fields[key]["widget"]
    sentinel = float(schema_min) - 1.0
    # After construction, widget minimum should already be sentinel
    results = []
    results.append(f"    repr(widget.value())   = {repr(w.value())}")
    results.append(f"    repr(widget.minimum()) = {repr(w.minimum())}")
    results.append(f"    value == minimum        = {w.value() == w.minimum()}")
    results.append(f"    math.isclose(val, min, abs_tol=1e-9) = "
                   f"{math.isclose(w.value(), w.minimum(), abs_tol=1e-9)}")
    return "\n".join(results)


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------
SCHEMAS = [
    ("S1", "integer", 5, 10, None),
    ("S2", "integer", -5, 5, None),
    ("S3", "integer", 0, 10, None),    # control — matches 36b range
    ("S4", "float", 0.1, 99.9, None),
    ("S5", "float", -1.5, 1.5, None),
]

tmpdir = tempfile.mkdtemp()
output_lines = []

def out(s=""):
    output_lines.append(s)
    print(s)


out("=" * 72)
out("DIAGNOSTIC 1 — Sentinel System Probe")
out("=" * 72)

for sid, arg_type, schema_min, schema_max, default in SCHEMAS:
    out(f"\n{'-' * 72}")
    out(f"Schema {sid}: type={arg_type}, min={schema_min}, max={schema_max}, default={default}")
    out(f"{'-' * 72}")

    tool = make_tool(f"diag_{sid}", arg_type, schema_min, schema_max, default)
    path = Path(tmpdir) / f"diag_{sid}.json"
    path.write_text(json.dumps(tool))
    win = scaffold.MainWindow(tool_path=str(path))
    form = win.form
    key = (form.GLOBAL, "--val")
    w = form.fields[key]["widget"]

    # --- (a)-(e) Initial state ---
    out("\n  === INITIAL STATE ===")
    p = probe(form, key, "initial")
    out(fmt_probe(p))

    # Float extras at initial state
    if arg_type == "float":
        out("\n  === FLOAT EXTRAS (initial) ===")
        out(float_probe_extra(form, key, schema_min))

    # --- Programmatic sets ---
    sentinel = w.minimum()
    test_values = [
        ("sentinel + 1 (widget.minimum() + 1)", sentinel + (1 if arg_type == "integer" else 1.0)),
        (f"schema min ({schema_min})", schema_min),
        (f"schema min + 1 ({schema_min + 1})", schema_min + (1 if arg_type == "integer" else 1.0)),
        (f"schema max ({schema_max})", schema_max),
    ]

    for label, set_val in test_values:
        out(f"\n  === SET: {label} ===")
        if arg_type == "integer":
            w.setValue(int(set_val))
        else:
            w.setValue(float(set_val))
        app.processEvents()
        p = probe(form, key, label)
        out(fmt_probe(p))

        # Float extras after each set
        if arg_type == "float":
            out(float_probe_extra(form, key, schema_min))

    # Reset to sentinel for any further checks
    w.setValue(sentinel if arg_type == "integer" else float(sentinel))
    app.processEvents()

    win.close()
    win.deleteLater()
    app.processEvents()


# ---------------------------------------------------------------------------
# Special float edge-case probe: do value == minimum comparisons break?
# ---------------------------------------------------------------------------
out(f"\n{'=' * 72}")
out("FLOAT EQUALITY EDGE CASES")
out(f"{'=' * 72}")

# Test a range of sentinel values for float equality issues
float_edge_cases = [
    ("F_edge1", 0.1, 99.9),    # sentinel = -0.9
    ("F_edge2", -1.5, 1.5),    # sentinel = -2.5
    ("F_edge3", 0.3, 10.0),    # sentinel = -0.7  (tricky binary fraction)
    ("F_edge4", 0.7, 5.0),     # sentinel = -0.3  (tricky binary fraction)
    ("F_edge5", 1.1, 9.9),     # sentinel = 0.1
    ("F_edge6", 0.01, 1.0),    # sentinel = -0.99
]

for eid, emin, emax in float_edge_cases:
    tool = make_tool(f"diag_{eid}", "float", emin, emax, None)
    path = Path(tmpdir) / f"diag_{eid}.json"
    path.write_text(json.dumps(tool))
    win = scaffold.MainWindow(tool_path=str(path))
    form = win.form
    key = (form.GLOBAL, "--val")
    w = form.fields[key]["widget"]

    sentinel_target = emin - 1.0
    actual_min = w.minimum()
    actual_val = w.value()
    eq_check = actual_val == actual_min
    isclose_check = math.isclose(actual_val, actual_min, abs_tol=1e-9)
    is_active = form._is_field_active(key)

    out(f"\n  {eid}: schema_min={emin}, sentinel_target={sentinel_target}")
    out(f"    repr(minimum)     = {repr(actual_min)}")
    out(f"    repr(value)       = {repr(actual_val)}")
    out(f"    value == minimum  = {eq_check}")
    out(f"    isclose           = {isclose_check}")
    out(f"    _is_field_active  = {is_active}")
    if not eq_check:
        out(f"    *** EQUALITY FAILURE: sentinel not detected! ***")
    if is_active:
        out(f"    *** BUG: field shows active when at sentinel! ***")

    win.close()
    win.deleteLater()
    app.processEvents()


# ---------------------------------------------------------------------------
# Specific Q1 probe: does any in-range value get dropped?
# ---------------------------------------------------------------------------
out(f"\n{'=' * 72}")
out("Q1 PROBE: In-range values silently dropped from command?")
out(f"{'=' * 72}")

for sid, arg_type, schema_min, schema_max, default in SCHEMAS:
    tool = make_tool(f"diag_q1_{sid}", arg_type, schema_min, schema_max, default)
    path = Path(tmpdir) / f"diag_q1_{sid}.json"
    path.write_text(json.dumps(tool))
    win = scaffold.MainWindow(tool_path=str(path))
    form = win.form
    key = (form.GLOBAL, "--val")
    w = form.fields[key]["widget"]

    # Check every integer in range, or a sampling for floats
    if arg_type == "integer":
        test_range = range(int(schema_min), int(schema_max) + 1)
    else:
        # Sample: min, min+0.01, min+0.1, ..., max
        test_range = []
        v = float(schema_min)
        while v <= float(schema_max) + 0.001:
            test_range.append(round(v, 2))
            v += 0.1

    dropped = []
    for tv in test_range:
        if arg_type == "integer":
            w.setValue(int(tv))
        else:
            w.setValue(float(tv))
        app.processEvents()
        fv = form.get_field_value(key)
        active = form._is_field_active(key)
        if fv is None or not active:
            dropped.append((tv, fv, active))

    if dropped:
        out(f"\n  {sid} ({arg_type}, [{schema_min}, {schema_max}]): "
            f"DROPPED {len(dropped)} value(s)!")
        for tv, fv, active in dropped:
            out(f"    value={tv} -> get_field_value={fv}, active={active}")
    else:
        out(f"\n  {sid} ({arg_type}, [{schema_min}, {schema_max}]): "
            f"All {len(list(test_range))} in-range values OK")

    win.close()
    win.deleteLater()
    app.processEvents()


# ---------------------------------------------------------------------------
# Summary answers
# ---------------------------------------------------------------------------
out(f"\n{'=' * 72}")
out("END OF DIAGNOSTIC OUTPUT")
out(f"{'=' * 72}")

# Write output to file for report
report_path = Path(__file__).parent / "diag_sentinel_output.txt"
report_path.write_text("\n".join(output_lines), encoding="utf-8")
print(f"\nOutput also saved to: {report_path}")

app.quit()
