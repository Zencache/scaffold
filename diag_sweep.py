#!/usr/bin/env python3
"""Diagnostic sweep — stress-test scaffold.py against all real tool schemas."""

import json
import os
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path

# Must be set before any PySide6 import (scaffold imports PySide6 on load)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import scaffold
from PySide6.QtWidgets import QApplication, QMessageBox

# ---------------------------------------------------------------------------
# QApplication singleton
# ---------------------------------------------------------------------------
app = QApplication(sys.argv)

# ---------------------------------------------------------------------------
# Monkeypatch QMessageBox to avoid blocking dialogs
#   warning  -> Yes  (so "missing _format" prompts proceed)
#   question -> No
#   critical -> Ok
# ---------------------------------------------------------------------------
QMessageBox.warning = lambda *a, **kw: QMessageBox.StandardButton.Yes
QMessageBox.question = lambda *a, **kw: QMessageBox.StandardButton.No
QMessageBox.critical = lambda *a, **kw: QMessageBox.StandardButton.Ok
QMessageBox.information = lambda *a, **kw: QMessageBox.StandardButton.Ok

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
total_checks = 0
total_passed = 0
total_failed = 0
failures = []
current_schema = ""


def check(label, condition, detail=""):
    global total_checks, total_passed, total_failed
    total_checks += 1
    if condition:
        total_passed += 1
    else:
        total_failed += 1
        msg = f"  FAIL: {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
        failures.append(
            f"{current_schema}: {label}" + (f" -- {detail}" if detail else "")
        )


# ---------------------------------------------------------------------------
# Recovery-file cleanup
# ---------------------------------------------------------------------------
def cleanup_recovery():
    tmp = Path(tempfile.gettempdir())
    for f in tmp.glob("scaffold_recovery_*.json"):
        try:
            f.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Type-contract map  (value is never None when these are called)
# ---------------------------------------------------------------------------
TYPE_CHECK = {
    "boolean": lambda v: isinstance(v, (bool, int)),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "text": lambda v: isinstance(v, str),
    "file": lambda v: isinstance(v, str),
    "directory": lambda v: isinstance(v, str),
    "enum": lambda v: isinstance(v, str),
    "multi_enum": lambda v: isinstance(v, list),
    "password": lambda v: isinstance(v, str),
}


# ---------------------------------------------------------------------------
# Collect files
# ---------------------------------------------------------------------------
tools_dir = SCRIPT_DIR / "tools"
schema_paths = sorted(tools_dir.rglob("*.json"))

presets_dir = SCRIPT_DIR / "presets"
preset_paths = sorted(presets_dir.rglob("*.json")) if presets_dir.exists() else []


# ===========================================================================
# Main sweep
# ===========================================================================
cleanup_recovery()

print(f"Diagnostic sweep: {len(schema_paths)} schemas, {len(preset_paths)} presets")
print("=" * 70)

for path in schema_paths:
    rel = path.relative_to(SCRIPT_DIR)
    current_schema = str(rel).replace("\\", "/")
    print(f"\n--- {current_schema} ---")

    # ------------------------------------------------------------------
    # 1. Load + validate
    # ------------------------------------------------------------------
    try:
        data = scaffold.load_tool(path)
    except Exception as e:
        check("load_tool", False, str(e))
        continue

    errors = scaffold.validate_tool(data)
    check("validate_tool", not errors, "; ".join(errors) if errors else "")

    # ------------------------------------------------------------------
    # 2. Normalize idempotency
    # ------------------------------------------------------------------
    try:
        n1 = scaffold.normalize_tool(data)
        n2 = scaffold.normalize_tool(n1)
        j1 = json.dumps(n1, sort_keys=True)
        j2 = json.dumps(n2, sort_keys=True)
        if j1 != j2:
            pos = next(
                (i for i, (a, b) in enumerate(zip(j1, j2)) if a != b), "?"
            )
            check("normalize_idempotent", False, f"first diff at char {pos}")
        else:
            check("normalize_idempotent", True)
    except Exception as e:
        check("normalize_idempotent", False, traceback.format_exc().splitlines()[-1])

    # ------------------------------------------------------------------
    # 3. Build form  (MainWindow loads, validates, normalizes, builds UI)
    # ------------------------------------------------------------------
    win = None
    form = None
    try:
        win = scaffold.MainWindow(tool_path=str(path))
        form = getattr(win, "form", None)
        check(
            "build_form",
            form is not None,
            "form not created (validation or format check may have failed)"
            if form is None
            else "",
        )
    except Exception as e:
        check("build_form", False, traceback.format_exc().splitlines()[-1])

    if form is None:
        if win:
            win.close()
            win.deleteLater()
        app.processEvents()
        continue

    # ------------------------------------------------------------------
    # 4. Field type contracts
    # ------------------------------------------------------------------
    for key, field in form.fields.items():
        t = field["arg"]["type"]
        try:
            v = form._raw_field_value(key)
        except Exception as e:
            check(f"type_contract {key}", False, f"raised: {e}")
            continue
        if v is None:
            check(f"type_contract {key}", True)
            continue
        tc = TYPE_CHECK.get(t)
        ok = tc(v) if tc else True
        check(
            f"type_contract {key}",
            ok,
            f"type={t}, got {type(v).__name__}={v!r}" if not ok else "",
        )

    # ------------------------------------------------------------------
    # 5. build_command invariants
    # ------------------------------------------------------------------
    try:
        cmd, _ = form.build_command()

        # cmd[0] must be the binary
        check(
            "cmd[0]==binary",
            bool(cmd) and cmd[0] == form.data["binary"],
            f"got {cmd[0]!r}" if cmd else "empty cmd",
        )

        # No None or empty strings in cmd[1:]
        bad = [(i, tok) for i, tok in enumerate(cmd[1:], 1) if tok is None or tok == ""]
        check(
            "cmd_no_empty",
            not bad,
            f"indices {[i for i, _ in bad]}" if bad else "",
        )

        # No duplicate flags (exclude repeatable).
        # Build set of known flags from schema to avoid false positives on
        # negative numeric values like "-1" that appear as argument values.
        known_flags = set()
        repeatable = set()
        for arg in form.data.get("arguments", []):
            f = arg.get("flag", "")
            if f.startswith("-"):
                known_flags.add(f)
            if arg.get("repeatable"):
                repeatable.add(f)
        for sub in form.data.get("subcommands") or []:
            for arg in sub.get("arguments", []):
                f = arg.get("flag", "")
                if f.startswith("-"):
                    known_flags.add(f)
                if arg.get("repeatable"):
                    repeatable.add(f)

        flag_tokens = [
            t
            for t in cmd[1:]
            if t in known_flags and t not in repeatable
        ]
        dupes = {f: c for f, c in Counter(flag_tokens).items() if c > 1}
        check("cmd_no_dupes", not dupes, f"{dupes}" if dupes else "")

    except Exception as e:
        check("build_command", False, traceback.format_exc().splitlines()[-1])

    # ------------------------------------------------------------------
    # 6. Preset round-trip
    #    serialize -> reset -> apply -> serialize again; compare non-meta keys
    # ------------------------------------------------------------------
    try:
        s1 = form.serialize_values()
        form.reset_to_defaults()
        form.apply_values(s1)
        s2 = form.serialize_values()

        diffs = []
        for k in sorted(set(s1) | set(s2)):
            if k.startswith("_"):
                continue
            if s1.get(k) != s2.get(k):
                diffs.append(f"{k}: {s1.get(k)!r} -> {s2.get(k)!r}")
        check("preset_round_trip", not diffs, "; ".join(diffs) if diffs else "")

    except Exception as e:
        check("preset_round_trip", False, traceback.format_exc().splitlines()[-1])

    # ------------------------------------------------------------------
    # 7. Subcommand cycling
    # ------------------------------------------------------------------
    if form.sub_combo is not None:
        try:
            n = form.sub_combo.count()
            for _ in range(2):
                for idx in range(n):
                    form.sub_combo.setCurrentIndex(idx)
                    app.processEvents()
                    form.build_command()
            check("subcommand_cycling", True)
        except Exception as e:
            check("subcommand_cycling", False, traceback.format_exc().splitlines()[-1])

    # ------------------------------------------------------------------
    # 8. Determinism
    # ------------------------------------------------------------------
    try:
        a, _ = form.build_command()
        b, _ = form.build_command()
        check("determinism", a == b, "commands differ" if a != b else "")
    except Exception as e:
        check("determinism", False, traceback.format_exc().splitlines()[-1])

    # Cleanup
    win.close()
    win.deleteLater()
    app.processEvents()


# ===========================================================================
# 9. Preset validation
# ===========================================================================
print(f"\n{'=' * 70}")
print(f"Preset validation: {len(preset_paths)} files")
print(f"{'=' * 70}")

for pp in preset_paths:
    rel = pp.relative_to(SCRIPT_DIR)
    current_schema = str(rel).replace("\\", "/")
    print(f"\n  {current_schema}")
    try:
        raw = pp.read_text(encoding="utf-8")
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        pdata = json.loads(raw)
    except Exception as e:
        check("preset_load", False, str(e))
        continue

    errs = scaffold.validate_preset(pdata)
    check("validate_preset", not errs, "; ".join(errs) if errs else "")


# ===========================================================================
# Final cleanup + summary
# ===========================================================================
cleanup_recovery()

print(f"\n{'=' * 70}")
print(f"SUMMARY: {total_checks} checks  |  {total_passed} passed  |  {total_failed} failed")
print(f"{'=' * 70}")

if failures:
    print("\nAll failures:")
    for f in failures:
        print(f"  X {f}")
else:
    print("\nNo failures detected.")
