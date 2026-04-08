"""Diagnostic Test Suite for Scaffold.

Bug-hunting suite that probes for consistency errors, state leakage, and
edge-case crashes.  NOT a feature-verification suite — those exist in
test_functional.py, test_smoke.py, etc.  This suite stress-tests assumptions
and finds bugs that only appear under unusual-but-valid conditions.
"""

import io
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Fix Unicode output on Windows (cp1252 can't encode special characters)
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)

# Monkeypatch QMessageBox.warning to auto-accept "Missing Format Marker" dialogs
# (test schemas intentionally lack _format to test the warning path)
_original_qmb_warning = QMessageBox.warning
def _patched_warning(parent, title, text, *args, **kwargs):
    if title == "Missing Format Marker":
        return QMessageBox.StandardButton.Yes
    return _original_qmb_warning(parent, title, text, *args, **kwargs)
QMessageBox.warning = _patched_warning

# Monkeypatch QMessageBox.question to auto-decline recovery prompts
QMessageBox.question = lambda *a, **kw: QMessageBox.StandardButton.No

# Monkeypatch QMessageBox.critical to auto-dismiss (for format-rejection tests)
_original_qmb_critical = QMessageBox.critical
QMessageBox.critical = lambda *a, **kw: QMessageBox.StandardButton.Ok

import scaffold


def _cleanup_recovery_files():
    """Remove all Scaffold recovery files from temp directory."""
    tmp = Path(tempfile.gettempdir())
    for f in tmp.glob("scaffold_recovery_*.json"):
        try:
            f.unlink()
        except OSError:
            pass

_cleanup_recovery_files()

passed = 0
failed = 0
errors = []


def check(condition, name):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  FAIL: {name}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GLOBAL = scaffold.ToolForm.GLOBAL


def _make_arg(name, flag, type_, **kwargs):
    """Return a minimal argument dict."""
    arg = {"name": name, "flag": flag, "type": type_}
    arg.update(kwargs)
    return arg


def _make_tool(binary="echo", args=None, tool_name="diag_test", **kwargs):
    """Return a minimal valid tool dict."""
    d = {
        "tool": tool_name,
        "binary": binary,
        "description": "diagnostic test tool",
        "arguments": args or [],
    }
    d.update(kwargs)
    return d


def _write_schema(tmpdir, name, data):
    """Write a tool schema to tmpdir and return its path."""
    path = Path(tmpdir) / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# =====================================================================
print("\n--- Section 1: Preset Round-Trip Consistency ---")
# =====================================================================

_s1_schema = _make_tool(args=[
    _make_arg("Verbose", "--verbose", "boolean"),
    _make_arg("Debug", "-d", "boolean", repeatable=True),
    _make_arg("Name", "--name", "string"),
    _make_arg("Format", "--format", "string", examples=["json", "xml", "csv"]),
    _make_arg("Body", "--body", "text"),
    _make_arg("Count", "--count", "integer"),
    _make_arg("Rate", "--rate", "float"),
    _make_arg("Mode", "--mode", "enum", choices=["fast", "slow", "balanced"]),
    _make_arg("Tags", "--tags", "multi_enum", choices=["alpha", "beta", "gamma"]),
    _make_arg("Input", "--input", "file"),
    _make_arg("OutDir", "--outdir", "directory"),
    _make_arg("Target", "TARGET", "string", positional=True),
    _make_arg("Suffix", "--suffix", "string", depends_on="--name"),
])

_s1_form = scaffold.ToolForm(_s1_schema)

# Set non-default values on every field
_s1_values = {
    (GLOBAL, "--verbose"): True,
    (GLOBAL, "-d"): 3,
    (GLOBAL, "--name"): "test_name",
    (GLOBAL, "--format"): "xml",
    (GLOBAL, "--body"): "multi\nline\ntext",
    (GLOBAL, "--count"): 42,
    (GLOBAL, "--rate"): 3.14,
    (GLOBAL, "--mode"): "balanced",
    (GLOBAL, "--tags"): ["alpha", "gamma"],
    (GLOBAL, "--input"): "/tmp/test.txt",
    (GLOBAL, "--outdir"): "/tmp/output",
    (GLOBAL, "TARGET"): "my_target",
    (GLOBAL, "--suffix"): "sfx",
}

for key, value in _s1_values.items():
    _s1_form._set_field_value(key, value)

# Serialize → reset → apply → verify
_s1_preset = _s1_form.serialize_values()
_s1_form.reset_to_defaults()
_s1_form.apply_values(_s1_preset)

check(_s1_form._raw_field_value((GLOBAL, "--verbose")) == True,
      "boolean round-trip")
check(_s1_form._raw_field_value((GLOBAL, "-d")) == 3,
      "boolean repeatable round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--name")) == "test_name",
      "string round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--format")) == "xml",
      "string with examples round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--body")) == "multi\nline\ntext",
      "text round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--count")) == 42,
      "integer round-trip")
_s1_rate = _s1_form._raw_field_value((GLOBAL, "--rate"))
check(_s1_rate is not None and abs(_s1_rate - 3.14) < 0.001,
      "float round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--mode")) == "balanced",
      "enum round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--tags")) == ["alpha", "gamma"],
      "multi_enum round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--input")) == "/tmp/test.txt",
      "file round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--outdir")) == "/tmp/output",
      "directory round-trip")
check(_s1_form._raw_field_value((GLOBAL, "TARGET")) == "my_target",
      "positional round-trip")
check(_s1_form._raw_field_value((GLOBAL, "--suffix")) == "sfx",
      "depends_on field round-trip")


# =====================================================================
print("\n--- Section 2: Command Builder Boundary Values ---")
# =====================================================================

_s2_tmp = tempfile.mkdtemp(prefix="scaffold_diag_s2_")


def _s2_build(schema, key, value):
    """Build a form, set a value, call build_command(). Returns (cmd, display) or raises."""
    form = scaffold.ToolForm(schema)
    form._set_field_value(key, value)
    return form.build_command()


def _s2_check_cmd(cmd, label):
    """Assert cmd is a list of str with no empty elements (basic sanity)."""
    check(isinstance(cmd, list) and all(isinstance(c, str) for c in cmd),
          f"{label}: returns list[str]")


# --- String edge cases ---
_s2_str_schema = _make_tool(args=[_make_arg("X", "--x", "string")])
_s2_str_key = (GLOBAL, "--x")

# empty string → field returns None → flag absent
_s2_f = scaffold.ToolForm(_s2_str_schema)
_s2_f._set_field_value(_s2_str_key, "")
_s2_cmd, _ = _s2_f.build_command()
_s2_check_cmd(_s2_cmd, "string empty")
check("--x" not in _s2_cmd, "string empty: flag absent (empty → None)")

# string with spaces
_s2_cmd, _ = _s2_build(_s2_str_schema, _s2_str_key, "a b c")
check("a b c" in _s2_cmd, "string spaces: value preserved as single element")

# string with shell metacharacters
_s2_cmd, _ = _s2_build(_s2_str_schema, _s2_str_key, "; rm -rf / #")
check("; rm -rf / #" in _s2_cmd, "string metacharacters: literal passthrough")

# string with unicode
_s2_cmd, _ = _s2_build(_s2_str_schema, _s2_str_key, "日本語")
check("日本語" in _s2_cmd, "string unicode: preserved")

# very long string
_s2_cmd, _ = _s2_build(_s2_str_schema, _s2_str_key, "x" * 1000)
check("x" * 1000 in _s2_cmd, "string long (1000 chars): preserved")

# --- Integer edge cases ---
_s2_int_schema = _make_tool(args=[
    _make_arg("X", "--x", "integer", default=0)
])
_s2_int_key = (GLOBAL, "--x")

# value 0
_s2_cmd, _ = _s2_build(_s2_int_schema, _s2_int_key, 0)
_s2_check_cmd(_s2_cmd, "integer zero")

# negative value -1 (need explicit min to avoid sentinel)
_s2_int_neg_schema = _make_tool(args=[
    _make_arg("X", "--x", "integer", min=-100)
])
_s2_cmd, _ = _s2_build(_s2_int_neg_schema, _s2_int_key, -1)
check("-1" in _s2_cmd, "integer negative: -1 in command")

# large value
_s2_cmd, _ = _s2_build(_s2_int_schema, _s2_int_key, 999999)
check("999999" in _s2_cmd, "integer large: 999999 in command")

# --- Float edge cases ---
_s2_float_schema = _make_tool(args=[
    _make_arg("X", "--x", "float", default=0.0)
])
_s2_float_key = (GLOBAL, "--x")

_s2_cmd, _ = _s2_build(_s2_float_schema, _s2_float_key, 0.0)
_s2_check_cmd(_s2_cmd, "float zero")

_s2_float_neg_schema = _make_tool(args=[
    _make_arg("X", "--x", "float", min=-100.0)
])
_s2_cmd, _ = _s2_build(_s2_float_neg_schema, _s2_float_key, -3.14)
check(any("-3.14" in c for c in _s2_cmd), "float negative: -3.14 in command")

_s2_cmd, _ = _s2_build(_s2_float_schema, _s2_float_key, 0.001)
# QDoubleSpinBox with 2 decimals rounds 0.001 to 0.00
_s2_check_cmd(_s2_cmd, "float small (0.001 → rounded)")

# --- Enum edge cases ---
_s2_enum_schema = _make_tool(args=[
    _make_arg("X", "--x", "enum", choices=["first", "middle", "last"], required=True)
])
_s2_enum_key = (GLOBAL, "--x")

_s2_cmd, _ = _s2_build(_s2_enum_schema, _s2_enum_key, "first")
check("first" in _s2_cmd, "enum first choice: in command")

_s2_cmd, _ = _s2_build(_s2_enum_schema, _s2_enum_key, "last")
check("last" in _s2_cmd, "enum last choice: in command")

# --- Multi-enum edge cases ---
_s2_menum_schema = _make_tool(args=[
    _make_arg("X", "--x", "multi_enum", choices=["a", "b", "c"])
])
_s2_menum_key = (GLOBAL, "--x")

# no selections → None → absent
_s2_f = scaffold.ToolForm(_s2_menum_schema)
_s2_f._set_field_value(_s2_menum_key, [])
_s2_cmd, _ = _s2_f.build_command()
check("--x" not in _s2_cmd, "multi_enum empty: flag absent")

# all selections
_s2_cmd, _ = _s2_build(_s2_menum_schema, _s2_menum_key, ["a", "b", "c"])
check(any("a,b,c" in c for c in _s2_cmd), "multi_enum all: comma-joined in command")

# single selection
_s2_cmd, _ = _s2_build(_s2_menum_schema, _s2_menum_key, ["b"])
check(any("b" in c for c in _s2_cmd), "multi_enum single: value in command")

# --- Boolean with repeatable ---
_s2_bool_schema = _make_tool(args=[
    _make_arg("X", "--x", "boolean", repeatable=True)
])
_s2_bool_key = (GLOBAL, "--x")

# count 0 → unchecked → absent
_s2_f = scaffold.ToolForm(_s2_bool_schema)
_s2_f._set_field_value(_s2_bool_key, 0)
_s2_cmd, _ = _s2_f.build_command()
check("--x" not in _s2_cmd, "boolean repeatable count=0: flag absent")

# count 1
_s2_cmd, _ = _s2_build(_s2_bool_schema, _s2_bool_key, 1)
check(_s2_cmd.count("--x") == 1, "boolean repeatable count=1: flag once")

# count REPEAT_SPIN_MAX
_s2_cmd, _ = _s2_build(_s2_bool_schema, _s2_bool_key, scaffold.REPEAT_SPIN_MAX)
check(_s2_cmd.count("--x") == scaffold.REPEAT_SPIN_MAX,
      f"boolean repeatable count={scaffold.REPEAT_SPIN_MAX}: flag repeated")

# --- File/directory with spaces and unicode ---
_s2_file_schema = _make_tool(args=[_make_arg("X", "--x", "file")])
_s2_file_key = (GLOBAL, "--x")

_s2_cmd, _ = _s2_build(_s2_file_schema, _s2_file_key, "/tmp/my dir/file.txt")
check("/tmp/my dir/file.txt" in _s2_cmd, "file with spaces: preserved")

_s2_dir_schema = _make_tool(args=[_make_arg("X", "--x", "directory")])
_s2_cmd, _ = _s2_build(_s2_dir_schema, (GLOBAL, "--x"), "/tmp/データ")
check("/tmp/データ" in _s2_cmd, "directory with unicode: preserved")

shutil.rmtree(_s2_tmp, ignore_errors=True)


# =====================================================================
print("\n--- Section 3: State Leakage Between Tool Loads ---")
# =====================================================================

_s3_tmp = tempfile.mkdtemp(prefix="scaffold_diag_s3_")

_s3_schema_a = _make_tool(
    binary="tool_alpha",
    tool_name="alpha_tool",
    args=[
        _make_arg("Aaa", "--aaa", "string"),
        _make_arg("Bbb", "--bbb", "integer", default=0),
    ],
)
_s3_schema_b = _make_tool(
    binary="tool_beta",
    tool_name="beta_tool",
    args=[
        _make_arg("Ccc", "--ccc", "boolean"),
        _make_arg("Ddd", "--ddd", "enum", choices=["x", "y"]),
    ],
)
_s3_path_a = _write_schema(_s3_tmp, "alpha", _s3_schema_a)
_s3_path_b = _write_schema(_s3_tmp, "beta", _s3_schema_b)

_s3_win = scaffold.MainWindow()
app.processEvents()

# Load schema A, set non-default values
_s3_win._load_tool_path(_s3_path_a)
app.processEvents()
_s3_win.form._set_field_value((GLOBAL, "--aaa"), "leaky_value")
_s3_win.form._set_field_value((GLOBAL, "--bbb"), 999)

# Load schema B
_s3_win._load_tool_path(_s3_path_b)
app.processEvents()

check(_s3_win.data["tool"] == "beta_tool",
      "tool name is B's after loading B")
check(_s3_win.data["binary"] == "tool_beta",
      "binary is B's after loading B")

# Fields contain only B's keys
_s3_b_keys = {(GLOBAL, "--ccc"), (GLOBAL, "--ddd")}
check(set(_s3_win.form.fields.keys()) == _s3_b_keys,
      "form.fields contains only B's keys (no A leftovers)")

# B's fields are at defaults
check(_s3_win.form._raw_field_value((GLOBAL, "--ccc")) is None,
      "B's boolean at default (unchecked)")
check(_s3_win.form._raw_field_value((GLOBAL, "--ddd")) is None or
      _s3_win.form._raw_field_value((GLOBAL, "--ddd")) == "",
      "B's enum at default")

# build_command uses B's binary
_s3_cmd, _ = _s3_win.form.build_command()
check(_s3_cmd[0] == "tool_beta",
      "build_command uses B's binary")

# Preview doesn't contain A's binary
_s3_preview = _s3_win.preview.toPlainText()
check("tool_alpha" not in _s3_preview,
      "preview does not contain A's binary name")

_s3_win.close()
_s3_win.deleteLater()
app.processEvents()
shutil.rmtree(_s3_tmp, ignore_errors=True)


# =====================================================================
print("\n--- Section 4: Schema Edge Cases ---")
# =====================================================================

_s4_tmp = tempfile.mkdtemp(prefix="scaffold_diag_s4_")

_s4_cases = {
    "empty args": {
        "tool": "t", "binary": "t", "description": "d", "arguments": []
    },
    "minimal arg": {
        "tool": "t", "binary": "t", "description": "d",
        "arguments": [{"name": "X", "flag": "--x", "type": "string"}]
    },
    "all optional fields null": {
        "tool": "t", "binary": "t", "description": "d",
        "arguments": [{
            "name": "X", "flag": "--x", "type": "string",
            "short_flag": None, "description": None, "required": None,
            "default": None, "choices": None, "group": None,
            "depends_on": None, "repeatable": None, "separator": None,
            "positional": None, "validation": None, "examples": None,
            "display_group": None, "min": None, "max": None,
            "deprecated": None, "dangerous": None,
        }]
    },
    "enum single choice": {
        "tool": "t", "binary": "t", "description": "d",
        "arguments": [{"name": "X", "flag": "--x", "type": "enum", "choices": ["only"]}]
    },
    "subcommand zero args": {
        "tool": "t", "binary": "t", "description": "d", "arguments": [],
        "subcommands": [{"name": "sub", "description": "d", "arguments": []}]
    },
    "many arguments (50)": {
        "tool": "t", "binary": "t", "description": "d",
        "arguments": [
            {"name": f"Arg{i:03d}", "flag": f"--arg-{i:03d}", "type": "string"}
            for i in range(1, 51)
        ]
    },
    "long description": {
        "tool": "t", "binary": "t", "description": "d" * 5000,
        "arguments": [{"name": "X", "flag": "--x", "type": "string"}]
    },
    "all types with all properties": {
        "tool": "t", "binary": "t", "description": "d",
        "arguments": [
            {"name": "B", "flag": "--b", "type": "boolean", "display_group": "Opts"},
            {"name": "S", "flag": "--s", "type": "string",
             "examples": ["a", "b"], "validation": "^[a-z]+$", "description": "str"},
            {"name": "I", "flag": "--i", "type": "integer", "min": 0, "max": 100},
            {"name": "F", "flag": "--f", "type": "float", "min": -1.0, "max": 1.0},
            {"name": "E", "flag": "--e", "type": "enum", "choices": ["x", "y"]},
            {"name": "M", "flag": "--m", "type": "multi_enum", "choices": ["p", "q"]},
            {"name": "T", "flag": "--t", "type": "text"},
            {"name": "Fi", "flag": "--fi", "type": "file"},
            {"name": "Di", "flag": "--di", "type": "directory"},
        ]
    },
    "duplicate display_group across subcommands": {
        "tool": "t", "binary": "t", "description": "d", "arguments": [],
        "subcommands": [
            {"name": "sub1", "description": "d", "arguments": [
                {"name": "A", "flag": "--a", "type": "string", "display_group": "Options"}
            ]},
            {"name": "sub2", "description": "d", "arguments": [
                {"name": "B", "flag": "--b", "type": "string", "display_group": "Options"}
            ]},
        ]
    },
    "multi-word subcommand": {
        "tool": "t", "binary": "t", "description": "d", "arguments": [],
        "subcommands": [
            {"name": "remote add", "description": "d", "arguments": [
                {"name": "URL", "flag": "--url", "type": "string"}
            ]}
        ]
    },
}

for label, schema in _s4_cases.items():
    try:
        errs = scaffold.validate_tool(schema)
        if not errs:
            norm = scaffold.normalize_tool(schema)
            form = scaffold.ToolForm(norm)
            # Also verify build_command doesn't crash
            form.build_command()
        check(True, f"schema edge case: {label}")
    except Exception as e:
        check(False, f"schema edge case: {label} — {type(e).__name__}: {e}")

shutil.rmtree(_s4_tmp, ignore_errors=True)


# =====================================================================
print("\n--- Section 5: Graceful Failure on Bad Input ---")
# =====================================================================

_s5_tmp = tempfile.mkdtemp(prefix="scaffold_diag_s5_")

# 5a: Not JSON
_s5_bad_json = _write_schema(_s5_tmp, "bad_json", None)
Path(_s5_bad_json).write_text("this is not json {{", encoding="utf-8")
try:
    scaffold.load_tool(_s5_bad_json)
    check(False, "not-JSON: should have raised RuntimeError")
except RuntimeError:
    check(True, "not-JSON: RuntimeError raised")
except Exception as e:
    check(False, f"not-JSON: unexpected {type(e).__name__}")

# 5b: JSON but not dict → validate_tool rejects cleanly
_s5_list_json = _write_schema(_s5_tmp, "list_json", [1, 2, 3])
_s5_list_data = scaffold.load_tool(_s5_list_json)
_s5_list_errs = scaffold.validate_tool(_s5_list_data)
check(len(_s5_list_errs) > 0 and any("dict" in e for e in _s5_list_errs),
      "JSON-but-not-dict: validate_tool returns errors mentioning 'dict'")

# 5c: Missing required keys
_s5_missing = {"tool": "t"}
errs = scaffold.validate_tool(_s5_missing)
check(len(errs) > 0, "missing required keys: validate_tool returns errors")

# 5d: Wrong _format (preset format) → _load_tool_path rejects
_s5_preset_schema = {
    "_format": "scaffold_preset",
    "tool": "t", "binary": "b", "description": "d",
    "arguments": [{"name": "X", "flag": "--x", "type": "string"}],
}
_s5_preset_path = _write_schema(_s5_tmp, "preset_format", _s5_preset_schema)
_s5_win = scaffold.MainWindow()
app.processEvents()
_s5_old_data = _s5_win.data  # should be None initially
_s5_win._load_tool_path(_s5_preset_path)
app.processEvents()
check(_s5_win.data is _s5_old_data,
      "wrong _format (preset): data unchanged after rejected load")
_s5_win.close()
_s5_win.deleteLater()
app.processEvents()

# 5e: Cascade file as tool → _load_tool_path rejects
_s5_cascade_schema = {"_format": "scaffold_cascade", "steps": []}
_s5_cascade_path = _write_schema(_s5_tmp, "cascade_as_tool", _s5_cascade_schema)
_s5_win2 = scaffold.MainWindow()
app.processEvents()
_s5_old_data2 = _s5_win2.data
_s5_win2._load_tool_path(_s5_cascade_path)
app.processEvents()
check(_s5_win2.data is _s5_old_data2,
      "cascade as tool: data unchanged after rejected load")
_s5_win2.close()
_s5_win2.deleteLater()
app.processEvents()

# 5f: Unknown field type
_s5_bad_type = {
    "tool": "t", "binary": "t", "description": "d",
    "arguments": [{"name": "X", "flag": "--x", "type": "path"}]
}
errs = scaffold.validate_tool(_s5_bad_type)
check(any("type" in e.lower() or "path" in e.lower() for e in errs),
      "unknown field type: validate_tool reports error about type")

# 5g: Preset with nested dict value
errs = scaffold.validate_preset({"key": {"nested": True}})
check(len(errs) > 0, "preset with nested dict: validate_preset returns errors")

# 5h: Preset that is actually a schema
errs = scaffold.validate_preset({"binary": "x", "arguments": []})
check(any("schema" in e.lower() for e in errs),
      "schema-as-preset: validate_preset detects mistake")

# 5i: Oversized file
_s5_big_path = Path(_s5_tmp) / "oversized.json"
_s5_big_path.write_text("x" * (scaffold.MAX_SCHEMA_SIZE + 1), encoding="utf-8")
try:
    scaffold.load_tool(str(_s5_big_path))
    check(False, "oversized file: should have raised RuntimeError")
except RuntimeError:
    check(True, "oversized file: RuntimeError raised")

shutil.rmtree(_s5_tmp, ignore_errors=True)


# =====================================================================
print("\n--- Section 6: Cascade Data Round-Trip ---")
# =====================================================================

_s6_tmp = tempfile.mkdtemp(prefix="scaffold_diag_s6_")

# Create dummy tool files so paths are real
_s6_tool1 = _write_schema(_s6_tmp, "c_tool1", _make_tool(tool_name="c1"))
_s6_tool2 = _write_schema(_s6_tmp, "c_tool2", _make_tool(tool_name="c2"))
_s6_tool3 = _write_schema(_s6_tmp, "c_tool3", _make_tool(tool_name="c3"))

# Also create a dummy preset file
_s6_preset1 = Path(_s6_tmp) / "preset1.json"
_s6_preset1.write_text(json.dumps({"_format": "scaffold_preset"}), encoding="utf-8")

_s6_win = scaffold.MainWindow()
app.processEvents()
_s6_dock = _s6_win.cascade_dock

# Build initial cascade data to import
_s6_initial_data = {
    "_format": "scaffold_cascade",
    "name": "test_cascade",
    "description": "test",
    "loop_mode": True,
    "steps": [
        {"tool": _s6_tool1, "preset": str(_s6_preset1), "delay": 5},
        {"tool": _s6_tool2, "preset": None, "delay": 0},
        {"tool": _s6_tool3, "preset": None, "delay": 10},
    ]
}

# Import the initial data
_s6_dock._import_cascade_data(_s6_initial_data)
app.processEvents()

# Export
_s6_export1 = _s6_dock._export_cascade_data("Test", "desc")

check(_s6_export1["_format"] == "scaffold_cascade",
      "cascade export: correct _format")
check(len(_s6_export1["steps"]) == 3,
      "cascade export: 3 steps")
check(_s6_export1["loop_mode"] == True,
      "cascade export: loop_mode preserved")

# Check delays round-tripped
_s6_exported_delays = [s["delay"] for s in _s6_export1["steps"]]
check(_s6_exported_delays == [5, 0, 10],
      "cascade export: delays preserved")

# Clear all slots by importing minimal data, then re-import
_s6_dock._import_cascade_data(_s6_export1)
app.processEvents()

# Export again
_s6_export2 = _s6_dock._export_cascade_data("Test", "desc")

check(_s6_export1 == _s6_export2,
      "cascade double round-trip: exports are identical")

# Error path: wrong format
try:
    _s6_dock._import_cascade_data({"_format": "wrong"})
    check(False, "cascade import wrong format: should have raised ValueError")
except ValueError:
    check(True, "cascade import wrong format: ValueError raised")

_s6_win.close()
_s6_win.deleteLater()
app.processEvents()
shutil.rmtree(_s6_tmp, ignore_errors=True)


# =====================================================================
print("\n--- Section 7: Subcommand Switching State Isolation ---")
# =====================================================================

_s7_schema = _make_tool(
    args=[_make_arg("Global", "--global", "string")],
    subcommands=[
        {
            "name": "sub1", "description": "first",
            "arguments": [
                {"name": "Alpha", "flag": "--alpha", "type": "string"},
                {"name": "Num1", "flag": "--num1", "type": "integer", "default": 0},
            ]
        },
        {
            "name": "sub2", "description": "second",
            "arguments": [
                {"name": "Beta", "flag": "--beta", "type": "string"},
                {"name": "Num2", "flag": "--num2", "type": "integer", "default": 0},
            ]
        },
    ]
)

_s7_form = scaffold.ToolForm(_s7_schema)

# Switch to subcommand 2 (index 1)
_s7_form.sub_combo.setCurrentIndex(1)
app.processEvents()

# Set values on sub2's fields
_s7_form._set_field_value(("sub2", "--beta"), "beta_val")
_s7_form._set_field_value(("sub2", "--num2"), 77)

# Switch back to sub1 (index 0)
_s7_form.sub_combo.setCurrentIndex(0)
app.processEvents()

# Sub1 fields should be at defaults
check(_s7_form._raw_field_value(("sub1", "--alpha")) is None,
      "sub1 --alpha at default after switching back")
check(_s7_form._raw_field_value(("sub1", "--num1")) == 0,
      "sub1 --num1 at default after switching back")

# Switch back to sub2
_s7_form.sub_combo.setCurrentIndex(1)
app.processEvents()

# Sub2 fields should retain their values
check(_s7_form._raw_field_value(("sub2", "--beta")) == "beta_val",
      "sub2 --beta retained after switch cycle")
check(_s7_form._raw_field_value(("sub2", "--num2")) == 77,
      "sub2 --num2 retained after switch cycle")

# Also verify build_command uses the correct subcommand
_s7_cmd, _ = _s7_form.build_command()
check("sub2" in _s7_cmd,
      "build_command includes current subcommand name")
check("beta_val" in _s7_cmd,
      "build_command includes sub2 field value")


# =====================================================================
print("\n--- Section 8: Wrong-Type Preset Values ---")
# =====================================================================

_s8_schema = _make_tool(args=[
    _make_arg("Count", "--count", "integer", default=0),
    _make_arg("Rate",  "--rate",  "float",   default=0.0),
])

# --- Invalid values: should silently skip, leaving default intact ---

# integer ← non-numeric string
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_crashed = False
try:
    _s8_form.apply_values({"--count": "forty-two"})
except Exception:
    _s8_crashed = True
check(not _s8_crashed, "integer ← 'forty-two': no exception")
check(_s8_form._raw_field_value((GLOBAL, "--count")) == 0,
      "integer ← 'forty-two': field stays at default")

# integer ← float-like string (int("3.14") also raises ValueError)
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_crashed = False
try:
    _s8_form.apply_values({"--count": "3.14"})
except Exception:
    _s8_crashed = True
check(not _s8_crashed, "integer ← '3.14': no exception")
check(_s8_form._raw_field_value((GLOBAL, "--count")) == 0,
      "integer ← '3.14': field stays at default")

# float ← non-numeric string
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_crashed = False
try:
    _s8_form.apply_values({"--rate": "not-a-number"})
except Exception:
    _s8_crashed = True
check(not _s8_crashed, "float ← 'not-a-number': no exception")
check(abs(_s8_form._raw_field_value((GLOBAL, "--rate")) - 0.0) < 0.001,
      "float ← 'not-a-number': field stays at default")

# --- Valid coercions: should still work correctly ---

# integer ← 3.14 (float truncates to 3)
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_form.apply_values({"--count": 3.14})
check(_s8_form._raw_field_value((GLOBAL, "--count")) == 3,
      "integer ← 3.14: truncates to 3")

# integer ← True (bool, int(True) = 1)
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_form.apply_values({"--count": True})
check(_s8_form._raw_field_value((GLOBAL, "--count")) == 1,
      "integer ← True: coerces to 1")

# float ← 42 (int, float(42) = 42.0)
_s8_form = scaffold.ToolForm(_s8_schema)
_s8_form.apply_values({"--rate": 42})
check(abs(_s8_form._raw_field_value((GLOBAL, "--rate")) - 42.0) < 0.001,
      "float ← 42: coerces to 42.0")


# =====================================================================
# Final cleanup
# =====================================================================
_cleanup_recovery_files()

print(f"\n{'='*60}")
print(f"DIAGNOSTIC RESULTS: {passed}/{passed+failed} passed, {failed} failed")
if errors:
    print(f"\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
if failed == 0:
    print("ALL TESTS PASSED")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
