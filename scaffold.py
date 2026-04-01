#!/usr/bin/env python3
"""Scaffold — CLI-to-GUI Translation Layer.

Turn any command-line tool into a native desktop GUI. Scaffold reads a JSON
schema describing a CLI tool's arguments and dynamically generates an
interactive form with live command preview, process execution, presets, and
dark mode support.

Usage:
    python scaffold.py                        Launch the tool picker GUI
    python scaffold.py tools/nmap.json        Open a specific tool directly
    python scaffold.py --validate FILE        Validate a schema (no GUI)
    python scaffold.py --prompt               Print the LLM schema-generation prompt
    python scaffold.py --version              Show version and exit
    python scaffold.py --help                 Show this help and exit

Requires: PySide6 (pip install PySide6) — no other dependencies.
Minimum Python version: 3.10
"""

__version__ = "2.6.5"

import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

VALID_TYPES = {"boolean", "string", "text", "integer", "float", "enum", "multi_enum", "file", "directory", "password"}
VALID_SEPARATORS = {"space", "equals", "none"}
VALID_ELEVATED = {"never", "optional", "always"}

ARG_DEFAULTS = {
    "short_flag": None,
    "description": "",
    "required": False,
    "default": None,
    "choices": None,
    "group": None,
    "depends_on": None,
    "repeatable": False,
    "separator": "space",
    "positional": False,
    "validation": None,
    "examples": None,
    "display_group": None,
    "min": None,
    "max": None,
    "deprecated": None,
    "dangerous": False,
}

# Widget size constants
SPINBOX_RANGE = 999999
REPEAT_SPIN_MAX = 10
REPEAT_SPIN_WIDTH = 60
TEXT_WIDGET_HEIGHT = 80
MULTI_ENUM_HEIGHT = 120

# Default window dimensions
DEFAULT_WINDOW_WIDTH = 700
DEFAULT_WINDOW_HEIGHT = 750

# Output panel limits
OUTPUT_MAX_BLOCKS = 10000       # Max lines kept in the output panel
OUTPUT_FLUSH_MS = 100           # Milliseconds between output buffer flushes
OUTPUT_MIN_HEIGHT = 80          # Minimum output panel height (pixels)
OUTPUT_MAX_HEIGHT = 800         # Maximum output panel height (pixels)
OUTPUT_DEFAULT_HEIGHT = 150     # Default output panel height (pixels)

# Tool schema file size limit (bytes)
MAX_SCHEMA_SIZE = 1_000_000     # 1 MB — skip files larger than this


# ---------------------------------------------------------------------------
# JSON loader, validator, normalizer
# ---------------------------------------------------------------------------

def load_tool(path: str | Path) -> dict:
    """Read and parse a JSON tool file. Raises RuntimeError on failure."""
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"File not found: {p}")
    try:
        size = p.stat().st_size
    except OSError:
        size = 0
    if size > MAX_SCHEMA_SIZE:
        raise RuntimeError(
            f"Schema file too large ({size:,} bytes, limit {MAX_SCHEMA_SIZE:,}): {p.name}"
        )
    try:
        text = p.read_text(encoding="utf-8")
    except PermissionError:
        raise RuntimeError(f"Permission denied: {p}")
    except OSError as e:
        raise RuntimeError(f"Cannot read file: {p} — {e}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {p} — {e}")


def validate_tool(data: dict) -> list[str]:
    """Validate a tool dict against the schema. Returns a list of error strings."""
    errors = []

    for key in ("tool", "binary", "description", "arguments"):
        if key not in data:
            errors.append(f"Missing required top-level key: \"{key}\"")

    # Validate binary field — security-sensitive (passed to QProcess.setProgram)
    if "binary" in data:
        binary = data["binary"]
        _SHELL_METACHAR = set("|;&$`(){}< >!~")
        if not isinstance(binary, str) or not binary.strip():
            errors.append("\"binary\" must be a non-empty string")
        elif len(binary) > 256:
            errors.append(f"\"binary\" too long ({len(binary)} chars, limit 256)")
        else:
            # Check for shell metacharacters (never valid in a binary name)
            bad_chars = sorted(set(binary) & _SHELL_METACHAR)
            if bad_chars:
                errors.append(
                    f"\"binary\" contains shell metacharacters: {' '.join(bad_chars)}"
                )
            # Check for path separators — only allowed if the path is absolute
            has_sep = "/" in binary or "\\" in binary
            if has_sep:
                is_absolute = (
                    binary.startswith("/")  # Unix absolute
                    or (len(binary) >= 3 and binary[1] == ":" and binary[2] in "/\\")  # Windows C:\
                )
                if not is_absolute:
                    errors.append(
                        "\"binary\" contains path separators but is not an absolute path "
                        "(use a bare executable name or an absolute path)"
                    )

    if "arguments" in data and not isinstance(data["arguments"], list):
        errors.append("\"arguments\" must be a list")

    if "arguments" in data and isinstance(data["arguments"], list):
        _validate_args(data["arguments"], "top-level", errors)
        _check_duplicate_flags(data["arguments"], "top-level", errors)
        _check_groups(data["arguments"], "top-level", errors)
        _check_dependencies(data["arguments"], "top-level", errors)

    if data.get("elevated") is not None:
        if data["elevated"] not in VALID_ELEVATED:
            errors.append(
                f"Invalid \"elevated\" value \"{data['elevated']}\" "
                f"(must be one of: {', '.join(sorted(VALID_ELEVATED))}, or null)"
            )

    if data.get("subcommands") is not None:
        if not isinstance(data["subcommands"], list):
            errors.append("\"subcommands\" must be a list or null")
        else:
            for i, sub in enumerate(data["subcommands"]):
                label = f"subcommand[{i}]"
                if not isinstance(sub, dict):
                    errors.append(f"{label}: must be an object")
                    continue
                if "name" not in sub:
                    errors.append(f"{label}: missing required key \"name\"")
                else:
                    label = f"subcommand \"{sub['name']}\""
                if "arguments" not in sub:
                    errors.append(f"{label}: missing required key \"arguments\"")
                elif not isinstance(sub["arguments"], list):
                    errors.append(f"{label}: \"arguments\" must be a list")
                else:
                    _validate_args(sub["arguments"], label, errors)
                    _check_duplicate_flags(sub["arguments"], label, errors)
                    _check_groups(sub["arguments"], label, errors)
                    _check_dependencies(sub["arguments"], label, errors)

    return errors


def _validate_args(args: list, scope: str, errors: list) -> None:
    for i, arg in enumerate(args):
        if not isinstance(arg, dict):
            errors.append(f"{scope} argument[{i}]: must be an object")
            continue
        name = arg.get("name", f"argument[{i}]")
        prefix = f"{scope} \"{name}\""

        for key in ("name", "flag", "type"):
            if key not in arg:
                errors.append(f"{prefix}: missing required key \"{key}\"")

        if "type" in arg:
            t = arg["type"]
            if t not in VALID_TYPES:
                errors.append(f"{prefix}: invalid type \"{t}\" (must be one of: {', '.join(sorted(VALID_TYPES))})")
            if t in ("enum", "multi_enum"):
                choices = arg.get("choices")
                if not isinstance(choices, list) or len(choices) == 0:
                    errors.append(f"{prefix}: type \"{t}\" requires a non-empty \"choices\" list")

        if "separator" in arg and arg["separator"] not in VALID_SEPARATORS:
            errors.append(f"{prefix}: invalid separator \"{arg['separator']}\" (must be one of: {', '.join(sorted(VALID_SEPARATORS))})")

        if "examples" in arg and arg["examples"] is not None:
            if not isinstance(arg["examples"], list) or not all(isinstance(e, str) for e in arg["examples"]):
                errors.append(f"{prefix}: \"examples\" must be a list of strings or null")
            if "type" in arg and arg["type"] == "enum":
                errors.append(f"{prefix}: has both \"choices\" and \"examples\" set. For enum types, \"choices\" is used and \"examples\" is ignored")
            if "type" in arg and arg["type"] == "password":
                errors.append(f"{prefix}: \"examples\" should not be used with password type (sensitive values should not be suggested)")

        if "display_group" in arg and arg["display_group"] is not None:
            if not isinstance(arg["display_group"], str):
                errors.append(f"{prefix}: \"display_group\" must be a string or null")

        # min/max validation
        for bound in ("min", "max"):
            if bound in arg and arg[bound] is not None:
                if not isinstance(arg[bound], (int, float)):
                    errors.append(f"{prefix}: \"{bound}\" must be a number or null")
                elif "type" in arg and arg["type"] not in ("integer", "float"):
                    errors.append(f"{prefix}: \"{bound}\" is only valid for integer and float types")
        if (arg.get("min") is not None and arg.get("max") is not None
                and isinstance(arg.get("min"), (int, float))
                and isinstance(arg.get("max"), (int, float))):
            if arg["min"] > arg["max"]:
                errors.append(f"{prefix}: \"min\" ({arg['min']}) must be <= \"max\" ({arg['max']})")

        # deprecated validation
        if "deprecated" in arg and arg["deprecated"] is not None:
            if not isinstance(arg["deprecated"], str):
                errors.append(f"{prefix}: \"deprecated\" must be a string or null")
            elif arg["deprecated"] == "":
                errors.append(f"{prefix}: \"deprecated\" must be a non-empty string or null")

        # dangerous validation
        if "dangerous" in arg and not isinstance(arg["dangerous"], bool):
            errors.append(f"{prefix}: \"dangerous\" must be a boolean")


def _check_duplicate_flags(args: list, scope: str, errors: list) -> None:
    seen = {}
    for arg in args:
        if not isinstance(arg, dict):
            continue
        flag = arg.get("flag")
        if flag is None:
            continue
        if flag in seen:
            errors.append(f"{scope}: duplicate flag \"{flag}\" (used by \"{seen[flag]}\" and \"{arg.get('name', '?')}\")")
        else:
            seen[flag] = arg.get("name", "?")


def _check_groups(args: list, scope: str, errors: list) -> None:
    groups = {}
    for arg in args:
        if not isinstance(arg, dict):
            continue
        g = arg.get("group")
        if g:
            groups.setdefault(g, []).append(arg.get("name", "?"))
    for g, members in groups.items():
        if len(members) < 2:
            errors.append(f"{scope}: group \"{g}\" has only 1 member (\"{members[0]}\") — mutual exclusivity requires at least 2")


def _check_dependencies(args: list, scope: str, errors: list) -> None:
    """Validate that every depends_on reference points to an existing flag in the same scope."""
    flags = set()
    for arg in args:
        if not isinstance(arg, dict):
            continue
        flag = arg.get("flag")
        if flag:
            flags.add(flag)
    for arg in args:
        if not isinstance(arg, dict):
            continue
        dep = arg.get("depends_on")
        if dep and dep not in flags:
            name = arg.get("name", "?")
            errors.append(f"{scope}: argument \"{name}\" depends on \"{dep}\" which does not exist in this scope")


def normalize_tool(data: dict) -> dict:
    """Fill in missing optional fields with safe defaults."""
    data.setdefault("subcommands", None)
    data.setdefault("description", "")
    data.setdefault("elevated", None)

    def _normalize_args(args):
        for arg in args:
            for key, default in ARG_DEFAULTS.items():
                arg.setdefault(key, default)

    _normalize_args(data.get("arguments", []))

    if data.get("subcommands"):
        for sub in data["subcommands"]:
            sub.setdefault("description", "")
            _normalize_args(sub.get("arguments", []))

    return data


def schema_hash(data: dict) -> str:
    """Compute a short hash of a tool's argument flags for preset versioning."""
    flags = sorted(arg["flag"] for arg in data.get("arguments", []) if isinstance(arg, dict))
    if data.get("subcommands"):
        for sub in data["subcommands"]:
            for arg in sub.get("arguments", []):
                if isinstance(arg, dict):
                    flags.append(f"{sub['name']}:{arg['flag']}")
        flags.sort()
    return hashlib.md5(json.dumps(flags).encode()).hexdigest()[:8]


# ANSI escape sequence pattern — compiled once, used in _flush_output()
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

# Maximum length for any single string key or value in a preset
_PRESET_MAX_STRING_LEN = 10_000

# Safe value types allowed in presets
_PRESET_SAFE_TYPES = (str, int, float, bool, list, type(None))


def validate_preset(data, tool_data=None) -> list[str]:
    """Validate a preset dict. Returns a list of error strings (empty = valid).

    Checks structure, value types, and string lengths. If *tool_data* is
    provided, emits informational warnings for keys that don't match any
    known flag in the schema (stale keys from older schema versions).
    """
    errors = []

    if not isinstance(data, dict):
        errors.append(f"Preset must be a dict, got {type(data).__name__}")
        return errors

    # Check all keys are strings
    for key in data:
        if not isinstance(key, str):
            errors.append(f"Preset key must be a string, got {type(key).__name__}: {key!r}")
            continue

        if len(key) > _PRESET_MAX_STRING_LEN:
            errors.append(f"Preset key too long ({len(key)} chars, limit {_PRESET_MAX_STRING_LEN})")

    # Detect schema-as-preset mistake
    if "binary" in data and "arguments" in data:
        errors.append("This looks like a tool schema, not a preset")

    # Check values
    for key, value in data.items():
        if not isinstance(key, str):
            continue  # already reported above

        # Meta keys (_schema_hash, _subcommand, _extra_flags) — skip value-type
        # checks. Meta keys start with _ and do NOT contain ":" (field keys
        # use scope:flag format like "__global__:--verbose").
        if key.startswith("_") and ":" not in key:
            # Still enforce string-length on string meta values
            if isinstance(value, str) and len(value) > _PRESET_MAX_STRING_LEN:
                errors.append(
                    f"Preset value for \"{key}\" too long ({len(value)} chars, limit {_PRESET_MAX_STRING_LEN})"
                )
            continue

        if not isinstance(value, _PRESET_SAFE_TYPES):
            errors.append(
                f"Preset value for \"{key}\" has unsupported type {type(value).__name__} "
                f"(allowed: str, int, float, bool, list, None)"
            )
            continue

        # List values must contain only strings (multi_enum storage)
        if isinstance(value, list):
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    errors.append(
                        f"Preset list value for \"{key}\"[{i}] must be a string, "
                        f"got {type(item).__name__}"
                    )

        # String length check on values
        if isinstance(value, str) and len(value) > _PRESET_MAX_STRING_LEN:
            errors.append(
                f"Preset value for \"{key}\" too long ({len(value)} chars, limit {_PRESET_MAX_STRING_LEN})"
            )

    # Optional: warn about unknown keys if tool_data is provided
    if tool_data is not None and not errors:
        known_flags = set()
        for arg in tool_data.get("arguments", []):
            if isinstance(arg, dict) and "flag" in arg:
                known_flags.add(f"__global__:{arg['flag']}")
        for sub in tool_data.get("subcommands", None) or []:
            for arg in sub.get("arguments", []):
                if isinstance(arg, dict) and "flag" in arg:
                    known_flags.add(f"{sub['name']}:{arg['flag']}")

        for key in data:
            if key.startswith("_") and ":" not in key:
                continue
            if key not in known_flags:
                errors.append(f"Unknown preset key \"{key}\" — not found in current schema (may be from an older version)")

    return errors


# ---------------------------------------------------------------------------
# Elevation helpers
# ---------------------------------------------------------------------------

_elevation_tool = None  # cached result: str path or None
_already_elevated = None  # cached result: bool


def _check_already_elevated():
    """Check if the app is already running with elevated privileges."""
    global _already_elevated
    if _already_elevated is not None:
        return _already_elevated
    if sys.platform == "win32":
        try:
            import ctypes
            _already_elevated = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            _already_elevated = False
    else:
        import os
        _already_elevated = os.geteuid() == 0
    return _already_elevated


def _find_elevation_tool():
    """Find the platform-appropriate elevation tool. Cached after first call."""
    global _elevation_tool
    if _elevation_tool is not None:
        return _elevation_tool
    if sys.platform == "win32":
        _elevation_tool = shutil.which("gsudo") or ""
    else:
        _elevation_tool = shutil.which("pkexec") or ""
    return _elevation_tool


def get_elevation_command(cmd_list: list[str]) -> tuple[list[str], str | None]:
    """
    Returns (elevated_cmd_list, error_message).
    If elevation is available, returns the modified command and None.
    If not available, returns the original command and an error message.
    """
    tool = _find_elevation_tool()
    if tool:
        return [tool] + cmd_list, None

    if sys.platform == "win32":
        return cmd_list, (
            "Elevated execution requires gsudo.\n"
            "Install it with: winget install gerardog.gsudo\n"
            "Or relaunch Scaffold as Administrator (right-click > Run as administrator)."
        )
    elif sys.platform == "darwin":
        return cmd_list, (
            "Elevated execution requires pkexec.\n"
            "Install it with: brew install polkit\n"
            "Or run Scaffold itself with sudo."
        )
    else:
        return cmd_list, (
            "Elevated execution requires PolicyKit (pkexec).\n"
            "Install it with your package manager, or run Scaffold itself with sudo."
        )


def _elevation_label():
    """Return platform-appropriate label for the elevation checkbox."""
    if sys.platform == "win32":
        return "Run as Administrator"
    return "Run with elevated privileges (sudo)"


# ---------------------------------------------------------------------------
# GUI renderer
# ---------------------------------------------------------------------------

from PySide6.QtCore import QPoint, QProcess, QSettings, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QAction, QActionGroup, QColor, QCursor, QDragEnterEvent, QDropEvent, QFont, QImage, QKeySequence, QPainter, QPalette, QPen, QPolygon, QShortcut, QTextCharFormat, QTextCursor  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QInputDialog, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
    QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)


_dark_mode = False
_original_palette = None
_arrow_dir = None


def _make_arrow_icons():
    """Generate small arrow PNGs for dark mode dropdown/spinbox controls."""
    global _arrow_dir
    if _arrow_dir is not None:
        return _arrow_dir
    _arrow_dir = tempfile.mkdtemp(prefix="scaffold_arrows_")
    color = QColor(DARK_COLORS["text"])
    for name, points in [
        ("down", [(1, 2), (5, 6), (9, 2)]),
        ("up", [(1, 6), (5, 2), (9, 6)]),
    ]:
        img = QImage(10, 8, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygon([QPoint(*p) for p in points]))
        painter.end()
        img.save(f"{_arrow_dir}/{name}.png")
    return _arrow_dir


DARK_COLORS = {
    "window": "#1e1e2e",
    "widget": "#2a2a3c",
    "input": "#313244",
    "text": "#cdd6f4",
    "text_dim": "#a6adc8",
    "accent": "#89b4fa",
    "selection": "#45475a",
    "border": "#585b70",
    "required": "#f38ba8",
    "disabled": "#6c7086",
    "success": "#a6e3a1",
    "error": "#f38ba8",
    "stderr": "#fab387",
    "output_bg": "#11111b",
    "output_text": "#cdd6f4",
    "command": "#89b4fa",
    "warning_bg": "#45475a",
    "warning_text": "#fab387",
    "warning_border": "#585b70",
}

# Preview syntax coloring — light mode
LIGHT_PREVIEW = {
    "binary": "#0550ae",       # blue, bold
    "flag": "#953800",         # amber/orange
    "value": "#24292f",        # default text
    "subcommand": "#0550ae",   # blue, bold
    "extra": "#656d76",        # dimmed gray
}

# Preview syntax coloring — dark mode
DARK_PREVIEW = {
    "binary": "#89b4fa",       # light blue, bold
    "flag": "#fab387",         # peach/orange
    "value": "#cdd6f4",        # default text
    "subcommand": "#89b4fa",   # light blue, bold
    "extra": "#a6adc8",        # dimmed
}


# Status/output colors — theme-independent (output panel is always dark)
COLOR_OK = "#4ec94e"       # success green
COLOR_ERR = "#e05555"      # error red
COLOR_WARN = "#e8a838"     # warning amber (stderr, stopped, cancelled)
COLOR_CMD = "#569cd6"      # command echo blue
COLOR_DIM = "#888888"      # dimmed text (unavailable tools in picker)
OUTPUT_BG = "#1e1e1e"      # output panel background
OUTPUT_FG = "#d4d4d4"      # output panel default foreground

# Light-mode warning bar colors
LIGHT_WARNING_BG = "#fff3cd"
LIGHT_WARNING_FG = "#856404"
LIGHT_WARNING_BORDER = "#ffc107"


def _detect_system_dark() -> bool:
    """Return True if the OS is currently using a dark color scheme."""
    try:
        scheme = QApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except AttributeError:
        pass
    try:
        lightness = QApplication.palette().color(QPalette.ColorRole.Window).lightness()
        return lightness < 128
    except Exception:
        pass
    return False


def apply_theme(dark: bool) -> None:
    """Apply or remove the dark palette and stylesheet application-wide."""
    global _dark_mode, _original_palette
    _dark_mode = dark
    app = QApplication.instance()
    if _original_palette is None:
        _original_palette = QPalette(app.palette())
    if dark:
        # Tell the platform to use its native dark mode for controls that
        # are not overridden by QSS (notably scrollbars).  This preserves
        # all native behavior — smooth animations, hover expansion, arrow
        # buttons — with dark colors, because the same native renderer
        # draws them.  Requires Qt 6.8+ (PySide6 6.8+); gracefully ignored
        # on older versions where scrollbars will fall back to palette hints.
        try:
            app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        except AttributeError:
            pass  # Qt < 6.8 — native dark scrollbars not available
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(DARK_COLORS["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(DARK_COLORS["text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(DARK_COLORS["input"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(DARK_COLORS["widget"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(DARK_COLORS["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(DARK_COLORS["widget"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(DARK_COLORS["text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(DARK_COLORS["accent"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(DARK_COLORS["window"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(DARK_COLORS["widget"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(DARK_COLORS["text"]))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(DARK_COLORS["disabled"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(DARK_COLORS["accent"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(DARK_COLORS["disabled"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(DARK_COLORS["disabled"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(DARK_COLORS["disabled"]))
        app.setPalette(palette)
        arrow_dir = _make_arrow_icons().replace("\\", "/")
        C = {**DARK_COLORS, "arrow_dir": arrow_dir}
        app.setStyleSheet(
            # Menu bar and menus
            f"QMenuBar {{ background-color: {C['widget']}; color: {C['text']}; }}"
            f"QMenuBar::item:selected {{ background-color: {C['selection']}; }}"
            f"QMenu {{ background-color: {C['widget']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; }}"
            f"QMenu::item:selected {{ background-color: {C['selection']}; }}"
            # Checkboxes
            f"QCheckBox {{ color: {C['text']}; }}"
            f"QCheckBox::indicator {{ background-color: {C['selection']};"
            f"  border: 1px solid {C['border']}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {C['accent']};"
            f"  border: 1px solid {C['accent']}; }}"
            # Comboboxes (dropdowns)
            f"QComboBox {{ background-color: {C['input']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; padding: 2px 4px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {C['widget']};"
            f"  color: {C['text']}; selection-background-color: {C['selection']};"
            f"  selection-color: {C['text']}; border: 1px solid {C['border']}; }}"
            f"QComboBox::drop-down {{ border-left: 1px solid {C['border']};"
            f"  background-color: {C['selection']}; }}"
            f"QComboBox::down-arrow {{ image: url({C['arrow_dir']}/down.png);"
            f"  width: 10px; height: 8px; }}"
            # Spinboxes
            f"QSpinBox, QDoubleSpinBox {{ background-color: {C['input']};"
            f"  color: {C['text']}; border: 1px solid {C['border']}; }}"
            f"QSpinBox::up-button, QSpinBox::down-button,"
            f"  QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
            f"  {{ background-color: {C['selection']}; border: 1px solid {C['border']}; }}"
            f"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow"
            f"  {{ image: url({C['arrow_dir']}/up.png); width: 10px; height: 8px; }}"
            f"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow"
            f"  {{ image: url({C['arrow_dir']}/down.png); width: 10px; height: 8px; }}"
            # Line edits
            f"QLineEdit {{ background-color: {C['input']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; }}"
            # List widgets (multi_enum)
            f"QListWidget {{ background-color: {C['input']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; }}"
            f"QListWidget::item:selected {{ background-color: {C['selection']};"
            f"  color: {C['text']}; }}"
            # Group boxes
            f"QGroupBox {{ color: {C['text']}; border: 1px solid {C['border']};"
            f"  margin-top: 6px; padding-top: 6px; }}"
            f"QGroupBox::title {{ color: {C['text']}; }}"
            # Table (tool picker)
            f"QTableWidget {{ background-color: {C['input']}; color: {C['text']};"
            f"  gridline-color: {C['border']}; }}"
            f"QTableWidget::item:selected {{ background-color: {C['selection']};"
            f"  color: {C['text']}; }}"
            f"QHeaderView::section {{ background-color: {C['widget']};"
            f"  color: {C['text']}; border: 1px solid {C['border']}; padding: 4px; }}"
            # NOTE: Scrollbars are NOT styled via QSS — doing so replaces the
            # native renderer and loses smooth animations, hover expansion, and
            # arrow buttons.  Instead, setColorScheme(Dark) tells the platform
            # to render native controls (including scrollbars) in dark mode.
            # Buttons
            f"QPushButton {{ background-color: {C['widget']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background-color: {C['selection']}; }}"
            f"QPushButton:pressed {{ background-color: {C['input']}; }}"
            # Plain text edits (extra flags, text-type fields)
            f"QPlainTextEdit {{ background-color: {C['input']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; }}"
            # Tooltips
            f"QToolTip {{ background-color: {C['widget']}; color: {C['text']};"
            f"  border: 1px solid {C['border']}; }}"
            # Status bar
            f"QStatusBar {{ color: {C['text']}; }}"
        )
    else:
        # Restore native light color scheme for platform controls.
        try:
            app.styleHints().setColorScheme(Qt.ColorScheme.Light)
        except AttributeError:
            pass
        app.setPalette(_original_palette)
        app.setStyleSheet("")


def _invalid_style() -> str:
    """Return a QSS border style string for invalid/failed-validation fields."""
    c = DARK_COLORS["required"]
    return f"border: 1px solid {c};" if _dark_mode else "border: 1px solid red;"


def _required_color() -> str:
    return DARK_COLORS["required"] if _dark_mode else "red"


class DragHandle(QWidget):
    """A small centered grip bar that the user drags vertically to resize the output panel."""

    HEIGHT = 8
    LINE_WIDTH = 32
    LINE_SPACING = 3

    def __init__(self, target: QWidget, settings: QSettings, parent=None):
        super().__init__(parent)
        self._target = target
        self._settings = settings
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_h = 0
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        self.setToolTip("Drag to resize output panel")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(DARK_COLORS["disabled"] if _dark_mode else "#888888")
        p.setPen(QPen(color, 1))
        cx = self.width() / 2
        cy = self.height() / 2
        x0 = int(cx - self.LINE_WIDTH / 2)
        x1 = int(cx + self.LINE_WIDTH / 2)
        y_top = int(cy - self.LINE_SPACING / 2)
        y_bot = int(cy + self.LINE_SPACING / 2)
        p.drawLine(x0, y_top, x1, y_top)
        p.drawLine(x0, y_bot, x1, y_bot)
        p.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_y = event.globalPosition().y()
            self._drag_start_h = self._target.height()
            event.accept()

    def _effective_max_height(self) -> int:
        """Return the effective maximum output height, capped to half the window."""
        win = self._target.window()
        if win:
            return min(OUTPUT_MAX_HEIGHT, win.height() // 2)
        return OUTPUT_MAX_HEIGHT

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            delta = int(self._drag_start_y - event.globalPosition().y())
            new_h = max(OUTPUT_MIN_HEIGHT, min(self._effective_max_height(), self._drag_start_h + delta))
            self._target.setFixedHeight(new_h)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self._settings.setValue("output/height", self._target.height())
            event.accept()


class ToolForm(QWidget):
    """Dynamically renders a GUI form from a validated, normalized tool dict."""

    command_changed = Signal()

    # Scope constant for global (top-level) arguments
    GLOBAL = "__global__"

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        # (scope, flag) -> {arg, widget, label, repeat_spin}
        self.fields = {}
        # (scope, group_name) -> list of (scope, flag) keys
        self.groups = {}
        # (scope, flag) -> compiled regex
        self.validators = {}
        # scope -> {display_group_name: QGroupBox}
        self.display_groups = {}

        self._build_ui()
        self._apply_groups()
        self._apply_dependencies()

    def eventFilter(self, obj, event) -> bool:
        """Handle key events on the search bar for Enter/Shift+Enter/Escape."""
        if obj is self._search_bar and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self._search_prev()
                else:
                    self._search_next()
                return True
            if key == Qt.Key.Key_Escape:
                self.close_search()
                return True
        return super().eventFilter(obj, event)

    def _field_key(self, scope: str, flag: str) -> tuple:
        """Return the canonical (scope, flag) key used to look up a field."""
        return (scope, flag)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build and lay out all widgets for the form."""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        header = QLabel(self.data["tool"])
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(header)

        if self.data["description"]:
            desc = QLabel(self.data["description"])
            desc.setWordWrap(True)
            root.addWidget(desc)

        # Separator between header and options
        self._header_sep = QFrame()
        self._header_sep.setFrameShape(QFrame.Shape.HLine)
        self._header_sep.setFrameShadow(QFrame.Shadow.Plain)
        color = DARK_COLORS["border"] if _dark_mode else "#999999"
        self._header_sep.setStyleSheet(
            f"QFrame {{ color: {color}; max-height: 1px; margin: 4px 0 2px 0; }}"
        )
        root.addWidget(self._header_sep)

        # Field search bar (always visible, Ctrl+F focuses it)
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Find field...  (Ctrl+F)")
        self._search_bar.textChanged.connect(self._on_search_text_changed)
        self._search_bar.installEventFilter(self)
        self._search_matches = []
        self._search_index = -1

        self._search_no_match_label = QLabel("No matches")
        err_color = DARK_COLORS["error"] if _dark_mode else "red"
        self._search_no_match_label.setStyleSheet(f"color: {err_color}; font-style: italic; margin-left: 4px;")
        self._search_no_match_label.setVisible(False)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.addWidget(self._search_bar, 1)
        search_row.addWidget(self._search_no_match_label)
        self._search_row_widget = QWidget()
        self._search_row_widget.setLayout(search_row)
        root.addWidget(self._search_row_widget)

        # Elevation control
        self.elevation_check = None
        elevated = self.data.get("elevated")
        if elevated in ("optional", "always") and not _check_already_elevated():
            elev_row = QHBoxLayout()
            self.elevation_check = QCheckBox(_elevation_label())
            if elevated == "always":
                self.elevation_check.setChecked(True)
                note = QLabel("This tool requires elevated privileges to function.")
            else:
                note = QLabel("Some features of this tool may require elevated privileges.")
            note.setWordWrap(True)
            note_color = DARK_COLORS["text_dim"] if _dark_mode else "gray"
            note.setStyleSheet(f"color: {note_color}; font-style: italic;")
            self._elevation_note = note
            elev_row.addWidget(self.elevation_check)
            elev_row.addWidget(note, 1)
            root.addLayout(elev_row)
            self.elevation_check.stateChanged.connect(lambda _: self.command_changed.emit())

        # Subcommand selector
        self.sub_combo = None
        if self.data["subcommands"]:
            row = QHBoxLayout()
            row.addWidget(QLabel("Subcommand:"))
            self.sub_combo = QComboBox()
            for sub in self.data["subcommands"]:
                label = sub["name"]
                full_desc = sub.get("description", "")
                if full_desc:
                    max_desc = 80 - len(label) - 5  # 5 for "  —  " separator
                    desc = full_desc
                    if max_desc > 20 and len(desc) > max_desc:
                        desc = desc[:max_desc - 1].rstrip() + "…"
                    if max_desc > 20:
                        label += f"  —  {desc}"
                self.sub_combo.addItem(label, sub["name"])
                if full_desc:
                    idx = self.sub_combo.count() - 1
                    self.sub_combo.setItemData(idx, f"<p>{full_desc}</p>", Qt.ItemDataRole.ToolTipRole)
            self.sub_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.sub_combo.setMinimumWidth(200)
            self.sub_combo.setMaximumWidth(600)
            row.addWidget(self.sub_combo, 1)
            root.addLayout(row)
            self.sub_combo.currentIndexChanged.connect(self._on_subcommand_changed)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll.setWidget(scroll_widget)
        root.addWidget(self._scroll, 1)

        # Global args section
        if self.data["arguments"]:
            if self.data["subcommands"]:
                box = QGroupBox("Global Options")
                box_layout = QFormLayout()
                box.setLayout(box_layout)
                self._add_args(self.data["arguments"], box_layout, self.GLOBAL)
                self.scroll_layout.addWidget(box)
            else:
                form = QFormLayout()
                self._add_args(self.data["arguments"], form, self.GLOBAL)
                self.scroll_layout.addLayout(form)

        # Subcommand args sections (stacked, toggle visibility)
        self.sub_sections = []
        if self.data["subcommands"]:
            for sub in self.data["subcommands"]:
                box = QGroupBox(f"{sub['name']} Options")
                box_layout = QFormLayout()
                box.setLayout(box_layout)
                self._add_args(sub["arguments"], box_layout, sub["name"])
                self.scroll_layout.addWidget(box)
                self.sub_sections.append(box)
            self._on_subcommand_changed(0)

        # Additional Flags
        self._build_extra_flags()

        self.scroll_layout.addStretch()

    def _build_extra_flags(self) -> None:
        """Build the collapsible 'Additional Flags' free-text section."""
        group = QGroupBox("Additional Flags")
        group.setCheckable(True)
        group.setChecked(False)
        layout = QVBoxLayout()
        self.extra_flags_edit = QPlainTextEdit()
        self.extra_flags_edit.setMaximumHeight(TEXT_WIDGET_HEIGHT)
        self.extra_flags_edit.setToolTip(
            "Raw flags appended directly to the command. "
            "Use this for flags not covered by the form above."
        )
        self.extra_flags_edit.textChanged.connect(self._validate_extra_flags)
        self.extra_flags_edit.textChanged.connect(lambda: self.command_changed.emit())
        layout.addWidget(self.extra_flags_edit)
        group.setLayout(layout)
        self.scroll_layout.addWidget(group)
        self.extra_flags_group = group

    def _validate_extra_flags(self) -> None:
        """Show a red border on the extra flags field if shlex parsing fails."""
        text = self.extra_flags_edit.toPlainText().strip()
        if not text:
            self.extra_flags_edit.setStyleSheet("")
            return
        try:
            shlex.split(text)
            self.extra_flags_edit.setStyleSheet("")
        except ValueError:
            self.extra_flags_edit.setStyleSheet(_invalid_style())

    def _add_args(self, args: list, form_layout: QFormLayout, scope: str) -> None:
        """Create and register a widget row for each arg in args under the given scope."""
        # Partition args by display_group while preserving order
        ungrouped = []
        display_groups: dict[str, list] = {}
        display_group_order: list[str] = []
        for arg in args:
            dg = arg.get("display_group")
            if dg:
                if dg not in display_groups:
                    display_groups[dg] = []
                    display_group_order.append(dg)
                display_groups[dg].append(arg)
            else:
                ungrouped.append(arg)

        # Add ungrouped args directly to the form layout
        for arg in ungrouped:
            self._add_single_arg(arg, form_layout, scope)

        # Add each display_group as a collapsible section
        for dg_name in display_group_order:
            dg_args = display_groups[dg_name]
            box = QGroupBox(dg_name)
            box_inner = QWidget()
            box_form = QFormLayout(box_inner)
            box_form.setContentsMargins(0, 0, 0, 0)
            box_layout = QVBoxLayout()
            box_layout.setContentsMargins(4, 4, 4, 4)
            box_layout.addWidget(box_inner)
            box.setLayout(box_layout)

            for arg in dg_args:
                self._add_single_arg(arg, box_form, scope)

            # Make the group box collapsible via title click
            box.setProperty("_dg_content", box_inner)
            box.setProperty("_dg_collapsed", False)
            box.mousePressEvent = lambda event, b=box: self._toggle_display_group(b)
            box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            # Store in parent layout — form_layout is a QFormLayout,
            # so wrap the group box in a row spanning both columns.
            form_layout.addRow(box)

            self.display_groups.setdefault(scope, {})[dg_name] = box

    def _toggle_display_group(self, box: QGroupBox) -> None:
        """Toggle visibility of a collapsible display group's contents."""
        content = box.property("_dg_content")
        if content is not None:
            collapsed = box.property("_dg_collapsed")
            collapsed = not collapsed
            box.setProperty("_dg_collapsed", collapsed)
            content.setVisible(not collapsed)

    # ------------------------------------------------------------------
    # Field search (Ctrl+F)
    # ------------------------------------------------------------------

    def open_search(self) -> None:
        """Focus the field search bar and select all text."""
        self._search_bar.setFocus()
        self._search_bar.selectAll()

    def close_search(self) -> None:
        """Clear search text, highlights, and defocus the search bar."""
        self._search_bar.clear()
        self._search_no_match_label.setVisible(False)
        self._clear_search_highlights()
        self._search_matches = []
        self._search_index = -1
        self._search_bar.clearFocus()

    def _on_search_text_changed(self, text: str) -> None:
        """Called when search bar text changes. Find all matches and highlight first."""
        self._clear_search_highlights()
        self._search_matches = []
        self._search_index = -1
        query = text.strip().lower()
        if not query:
            self._search_no_match_label.setVisible(False)
            return

        # Determine visible scopes
        visible_scopes = {self.GLOBAL}
        current_sub = self.get_current_subcommand()
        if current_sub:
            visible_scopes.add(current_sub)

        for key, field in self.fields.items():
            scope, flag = key
            if scope not in visible_scopes:
                continue
            arg = field["arg"]
            name_lower = arg["name"].lower()
            flag_lower = flag.lower()
            if query in name_lower or query in flag_lower:
                self._search_matches.append(key)

        if self._search_matches:
            self._search_no_match_label.setVisible(False)
            self._search_index = 0
            self._highlight_and_scroll(self._search_matches[0])
        else:
            self._search_no_match_label.setVisible(True)

    def _search_next(self) -> None:
        """Jump to the next search match (Enter key)."""
        if not self._search_matches:
            return
        self._clear_search_highlights()
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._highlight_and_scroll(self._search_matches[self._search_index])

    def _search_prev(self) -> None:
        """Jump to the previous search match (Shift+Enter)."""
        if not self._search_matches:
            return
        self._clear_search_highlights()
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._highlight_and_scroll(self._search_matches[self._search_index])

    def _highlight_and_scroll(self, key: tuple) -> None:
        """Highlight the matching field's label and scroll it into view."""
        field = self.fields[key]
        label = field["label"]

        # Expand any collapsed display_group containing this field
        scope = key[0]
        if scope in self.display_groups:
            for dg_name, box in self.display_groups[scope].items():
                if box.isAncestorOf(label) and box.property("_dg_collapsed"):
                    self._toggle_display_group(box)

        # Apply highlight — theme-aware
        highlight = DARK_COLORS["selection"] if _dark_mode else "#fff176"
        label.setStyleSheet(f"background-color: {highlight};")
        label.setProperty("_search_highlighted", True)

        # Scroll into view
        self._scroll.ensureWidgetVisible(label, 50, 50)

    def _clear_search_highlights(self) -> None:
        """Remove search highlight from all labels."""
        for field in self.fields.values():
            label = field["label"]
            if label.property("_search_highlighted"):
                label.setStyleSheet("")
                label.setProperty("_search_highlighted", False)

    def _add_single_arg(self, arg: dict, form_layout: QFormLayout, scope: str) -> None:
        """Create and register a single widget row for an arg under the given scope."""
        flag = arg["flag"]
        key = self._field_key(scope, flag)
        widget = self._build_widget(arg, key)
        label_text = arg["name"]
        if arg["required"]:
            label_text = f"<b>{label_text} <span style='color:{_required_color()};'>*</span></b>"
        # Dangerous: prepend red warning symbol
        if arg.get("dangerous"):
            warn_color = DARK_COLORS["required"] if _dark_mode else "red"
            label_text = f"<span style='color:{warn_color};'>\u26a0</span> {label_text}"
        # Deprecated: strikethrough + colored suffix
        if arg.get("deprecated"):
            dep_color = DARK_COLORS["warning_text"] if _dark_mode else "#856404"
            label_text = f"<s>{label_text}</s> <span style='color:{dep_color};'>(deprecated)</span>"
        label = QLabel(label_text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setToolTip(self._build_tooltip(arg))

        # Repeatable: add a count spinner next to the widget
        repeat_spin = None
        if arg["repeatable"] and arg["type"] == "boolean":
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(widget, 1)
            repeat_spin = QSpinBox()
            repeat_spin.setRange(1, REPEAT_SPIN_MAX)
            repeat_spin.setValue(1)
            repeat_spin.setPrefix("x")
            repeat_spin.setToolTip("Number of times to repeat this flag")
            repeat_spin.setMaximumWidth(REPEAT_SPIN_WIDTH)
            repeat_spin.valueChanged.connect(lambda _: self.command_changed.emit())
            row_layout.addWidget(repeat_spin)
            form_layout.addRow(label, row_widget)
        else:
            form_layout.addRow(label, widget)

        if arg["group"]:
            group_key = (scope, arg["group"])
            self.groups.setdefault(group_key, []).append(key)

        self.fields[key] = {
            "arg": arg,
            "widget": widget,
            "label": label,
            "repeat_spin": repeat_spin,
        }

    # ------------------------------------------------------------------
    # Widget factory
    # ------------------------------------------------------------------

    def _build_widget(self, arg: dict, key: tuple) -> QWidget:
        """Instantiate and return the appropriate widget for the given arg's type."""
        try:
            return self._build_widget_inner(arg, key)
        except Exception as exc:
            import traceback
            print(f"Warning: failed to render widget for \"{arg.get('name', '?')}\" "
                  f"(type \"{arg.get('type', '?')}\"): {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            w = QLineEdit()
            w._is_fallback = True
            w.setToolTip(f"This field could not be rendered as '{arg.get('type', '?')}' "
                         f"-- using text input as fallback")
            w.textChanged.connect(lambda _: self.command_changed.emit())
            return w

    def _build_widget_inner(self, arg: dict, key: tuple) -> QWidget:
        """Instantiate and return the appropriate widget for the given arg's type."""
        t = arg["type"]

        if t == "boolean":
            w = QCheckBox()
            if arg["default"] is True:
                w.setChecked(True)
            w.stateChanged.connect(lambda _: self.command_changed.emit())

        elif t == "string":
            examples = arg.get("examples")
            if examples:
                # Editable combo with suggestions
                w = QComboBox()
                w.setEditable(True)
                w.addItem("")  # empty first item so nothing is pre-selected
                w.addItems(examples)
                if arg["default"] is not None:
                    w.setCurrentText(str(arg["default"]))
                else:
                    w.setCurrentText("")
                if arg["description"]:
                    w.lineEdit().setPlaceholderText(arg["description"])
                if arg["validation"]:
                    regex = re.compile(arg["validation"])
                    self.validators[key] = regex
                    w.lineEdit().textChanged.connect(
                        lambda text, ww=w.lineEdit(), rx=regex: self._validate_input(ww, rx, text)
                    )
                w.currentTextChanged.connect(lambda _: self.command_changed.emit())
            else:
                # Plain line edit
                w = QLineEdit()
                if arg["default"] is not None:
                    w.setText(str(arg["default"]))
                if arg["description"]:
                    w.setPlaceholderText(arg["description"])
                if arg["validation"]:
                    regex = re.compile(arg["validation"])
                    self.validators[key] = regex
                    w.textChanged.connect(lambda text, ww=w, rx=regex: self._validate_input(ww, rx, text))
                w.textChanged.connect(lambda _: self.command_changed.emit())

        elif t == "password":
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            line = QLineEdit()
            line.setEchoMode(QLineEdit.EchoMode.Password)
            if arg["default"] is not None:
                line.setText(str(arg["default"]))
            if arg["description"]:
                line.setPlaceholderText(arg["description"])
            if arg["validation"]:
                regex = re.compile(arg["validation"])
                self.validators[key] = regex
                line.textChanged.connect(lambda text, ww=line, rx=regex: self._validate_input(ww, rx, text))
            line.textChanged.connect(lambda _: self.command_changed.emit())
            show_cb = QCheckBox("Show")
            show_cb.toggled.connect(
                lambda checked, le=line: le.setEchoMode(
                    QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
                )
            )
            layout.addWidget(line, 1)
            layout.addWidget(show_cb)
            container._line_edit = line
            container._show_toggle = show_cb
            w = container

        elif t == "text":
            w = QPlainTextEdit()
            w.setMaximumHeight(TEXT_WIDGET_HEIGHT)
            if arg["default"] is not None:
                w.setPlainText(str(arg["default"]))
            w.textChanged.connect(lambda: self.command_changed.emit())

        elif t == "integer":
            w = QSpinBox()
            w.setRange(-SPINBOX_RANGE, SPINBOX_RANGE)
            if arg["default"] is not None:
                w.setValue(int(arg["default"]))
            else:
                w.setRange(-1, SPINBOX_RANGE)
                w.setValue(-1)
                w.setSpecialValueText(" ")
            if arg.get("min") is not None:
                if arg["default"] is None:
                    # Sentinel is one below the schema min
                    w.setMinimum(arg["min"] - 1)
                    w.setValue(arg["min"] - 1)
                else:
                    w.setMinimum(int(arg["min"]))
            if arg.get("max") is not None:
                w.setMaximum(int(arg["max"]))
            w.valueChanged.connect(lambda _: self.command_changed.emit())

        elif t == "float":
            w = QDoubleSpinBox()
            w.setRange(-SPINBOX_RANGE, SPINBOX_RANGE)
            w.setDecimals(2)
            if arg["default"] is not None:
                w.setValue(float(arg["default"]))
            else:
                w.setRange(-1.0, SPINBOX_RANGE)
                w.setValue(-1.0)
                w.setSpecialValueText(" ")
            if arg.get("min") is not None:
                if arg["default"] is None:
                    w.setMinimum(float(arg["min"]) - 1.0)
                    w.setValue(float(arg["min"]) - 1.0)
                else:
                    w.setMinimum(float(arg["min"]))
            if arg.get("max") is not None:
                w.setMaximum(float(arg["max"]))
            w.valueChanged.connect(lambda _: self.command_changed.emit())

        elif t == "enum":
            w = QComboBox()
            if not arg["required"]:
                w.addItem("", "")
            for choice in (arg["choices"] or []):
                w.addItem(choice, choice)
            if arg["default"] is not None:
                idx = w.findData(str(arg["default"]))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            w.currentIndexChanged.connect(lambda _: self.command_changed.emit())

        elif t == "multi_enum":
            w = QListWidget()
            w.setMaximumHeight(MULTI_ENUM_HEIGHT)
            for choice in (arg["choices"] or []):
                item = QListWidgetItem(choice)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                w.addItem(item)
            w.itemChanged.connect(lambda: self.command_changed.emit())

        elif t == "file":
            w = QWidget()
            layout = QHBoxLayout(w)
            layout.setContentsMargins(0, 0, 0, 0)
            line = QLineEdit()
            if arg["default"] is not None:
                line.setText(str(arg["default"]))
            if arg["description"]:
                line.setPlaceholderText(arg["description"])
            btn = QPushButton("Browse...")
            btn.clicked.connect(lambda checked, le=line: self._browse_file(le))
            layout.addWidget(line, 1)
            layout.addWidget(btn)
            line.textChanged.connect(lambda _: self.command_changed.emit())
            w._line_edit = line

        elif t == "directory":
            w = QWidget()
            layout = QHBoxLayout(w)
            layout.setContentsMargins(0, 0, 0, 0)
            line = QLineEdit()
            if arg["default"] is not None:
                line.setText(str(arg["default"]))
            if arg["description"]:
                line.setPlaceholderText(arg["description"])
            btn = QPushButton("Browse...")
            btn.clicked.connect(lambda checked, le=line: self._browse_directory(le))
            layout.addWidget(line, 1)
            layout.addWidget(btn)
            line.textChanged.connect(lambda _: self.command_changed.emit())
            w._line_edit = line

        else:
            w = QLabel(f"[unsupported type: {t}]")

        if arg["description"]:
            w.setToolTip(self._build_tooltip(arg))

        return w

    @staticmethod
    def _build_tooltip(arg: dict) -> str:
        """Build a structured tooltip showing flag, type, description, and validation."""
        warning_lines = []
        if arg.get("deprecated"):
            warning_lines.append(f"\u26a0 DEPRECATED: {arg['deprecated']}")
        if arg.get("dangerous"):
            warning_lines.append("\u26a0 CAUTION: This flag may have destructive or irreversible effects.")
        parts = [arg["flag"]]
        if arg.get("short_flag"):
            parts.append(arg["short_flag"])
        type_info = arg["type"]
        sep = arg.get("separator", "space")
        if sep == "equals" or (sep == "none" and arg["type"] != "boolean"):
            type_info += f", separator: {sep}"
        header = f"{' '.join(parts)} ({type_info})"
        lines = warning_lines + [""] + [header] if warning_lines else [header]
        if arg.get("description"):
            lines.append(arg["description"])
        if arg.get("validation"):
            lines.append(f"Validation: {arg['validation']}")
        return "<p>" + "<br>".join(lines) + "</p>"

    # ------------------------------------------------------------------
    # Browse dialogs
    # ------------------------------------------------------------------

    def _browse_file(self, line_edit: QLineEdit) -> None:
        """Open a file-picker dialog and write the chosen path into line_edit."""
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            line_edit.setText(path)

    def _browse_directory(self, line_edit: QLineEdit) -> None:
        """Open a directory-picker dialog and write the chosen path into line_edit."""
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            line_edit.setText(path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_input(self, widget: QLineEdit, regex, text: str) -> None:
        """Apply a red border to widget if text is non-empty and fails regex."""
        if text and not regex.search(text):
            widget.setStyleSheet(_invalid_style())
        else:
            widget.setStyleSheet("")

    # ------------------------------------------------------------------
    # Group exclusivity
    # ------------------------------------------------------------------

    def _apply_groups(self) -> None:
        """Wire up mutual-exclusivity signals for all groups."""
        for group_key, field_keys in self.groups.items():
            for fk in field_keys:
                field = self.fields[fk]
                widget = field["widget"]
                if isinstance(widget, QCheckBox):
                    widget.stateChanged.connect(
                        lambda state, active=fk, gk=group_key: self._on_group_toggled(gk, active, state)
                    )

    def _on_group_toggled(self, group_key: tuple, active_key: tuple, state: int) -> None:
        """Uncheck all other members of a mutual-exclusivity group when one is checked."""
        if state != Qt.CheckState.Checked.value:
            return
        for fk in self.groups[group_key]:
            if fk != active_key:
                field = self.fields[fk]
                w = field["widget"]
                if isinstance(w, QCheckBox):
                    w.blockSignals(True)
                    w.setChecked(False)
                    w.blockSignals(False)
        self.command_changed.emit()

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    def _apply_dependencies(self) -> None:
        """Wire up enable/disable signals for all fields that have a depends_on parent."""
        for key, field in self.fields.items():
            dep_flag = field["arg"]["depends_on"]
            if not dep_flag:
                continue
            # Look for parent in the same scope first, then global
            scope = key[0]
            parent_key = (scope, dep_flag)
            if parent_key not in self.fields:
                parent_key = (self.GLOBAL, dep_flag)
            if parent_key not in self.fields:
                name = field["arg"].get("name", "?")
                print(f"Warning: dependency wiring failed for \"{name}\" — "
                      f"parent \"{dep_flag}\" not found in form. "
                      f"Field left enabled (fail-open).", file=sys.stderr)
                continue
            parent_field = self.fields[parent_key]
            # Set initial disabled state
            field["widget"].setEnabled(self._is_field_active(parent_key))
            field["label"].setEnabled(self._is_field_active(parent_key))
            # Connect parent changes
            self._connect_dependency(parent_key, parent_field, child_field=field)

    def _connect_dependency(self, parent_key: tuple, parent_field: dict, child_field: dict) -> None:
        """Connect the appropriate change signal on the parent widget to update the child's enabled state."""
        pw = parent_field["widget"]
        if isinstance(pw, QCheckBox):
            pw.stateChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        elif isinstance(pw, QLineEdit):
            pw.textChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        elif isinstance(pw, QPlainTextEdit):
            pw.textChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        elif isinstance(pw, QComboBox):
            if pw.isEditable():
                pw.currentTextChanged.connect(
                    lambda: self._update_dependent(parent_key, child_field)
                )
            else:
                pw.currentIndexChanged.connect(
                    lambda: self._update_dependent(parent_key, child_field)
                )
        elif isinstance(pw, QSpinBox):
            pw.valueChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        elif isinstance(pw, QDoubleSpinBox):
            pw.valueChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        elif isinstance(pw, QListWidget):
            pw.itemChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )
        # file/directory containers — connect the inner QLineEdit
        elif hasattr(pw, '_line_edit'):
            pw._line_edit.textChanged.connect(
                lambda: self._update_dependent(parent_key, child_field)
            )

    def _update_dependent(self, parent_key: tuple, child_field: dict) -> None:
        """Enable or disable a dependent field based on the parent's current value."""
        active = self._is_field_active(parent_key)
        child_field["widget"].setEnabled(active)
        child_field["label"].setEnabled(active)

    def _is_field_active(self, key: tuple) -> bool:
        """Return True if the given field's widget has a meaningful value."""
        field = self.fields[key]
        w = field["widget"]
        if isinstance(w, QCheckBox):
            return w.isChecked()
        if isinstance(w, QLineEdit):
            return bool(w.text().strip())
        if isinstance(w, QPlainTextEdit):
            return bool(w.toPlainText().strip())
        if isinstance(w, QComboBox):
            if w.isEditable():
                return bool(w.currentText().strip())
            return bool(w.currentData())
        if isinstance(w, (QSpinBox, QDoubleSpinBox)):
            if w.specialValueText() and w.value() == w.minimum():
                return False
            return True
        if isinstance(w, QListWidget):
            for i in range(w.count()):
                if w.item(i).checkState() == Qt.CheckState.Checked:
                    return True
            return False
        if hasattr(w, '_line_edit'):
            return bool(w._line_edit.text().strip())
        return False

    # ------------------------------------------------------------------
    # Subcommand switching
    # ------------------------------------------------------------------

    def _on_subcommand_changed(self, index: int) -> None:
        """Show only the selected subcommand's options section."""
        for i, section in enumerate(self.sub_sections):
            section.setVisible(i == index)
        self._scroll.verticalScrollBar().setValue(0)
        self.command_changed.emit()

    # ------------------------------------------------------------------
    # Value reading (for command assembly)
    # ------------------------------------------------------------------

    def get_current_subcommand(self) -> str | None:
        """Return the currently selected subcommand name, or None if no subcommands."""
        if self.sub_combo is not None:
            return self.sub_combo.currentData()
        return None

    def get_extra_flags(self) -> list[str]:
        """Return the parsed extra-flags tokens, or an empty list if the section is disabled."""
        if not self.extra_flags_group.isChecked():
            return []
        text = self.extra_flags_edit.toPlainText().strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()

    def get_field_value(self, key: tuple) -> int | str | list | None:
        """Return the current widget value for a field key, or None if empty/unchecked."""
        field = self.fields.get(key)
        if not field:
            return None
        w = field["widget"]
        if not w.isEnabled():
            return None
        arg = field["arg"]
        t = arg["type"]

        # Fallback widget — treat as plain string regardless of declared type
        if getattr(w, "_is_fallback", False):
            v = w.text().strip()
            return v if v else None

        if t == "boolean":
            if isinstance(w, QCheckBox) and w.isChecked():
                count = 1
                if field["repeat_spin"]:
                    count = field["repeat_spin"].value()
                return count
            return None

        elif t == "string":
            v = w.currentText().strip() if isinstance(w, QComboBox) else w.text().strip()
            return v if v else None

        elif t == "password":
            v = w._line_edit.text().strip()
            return v if v else None

        elif t == "text":
            v = w.toPlainText().strip()
            return v if v else None

        elif t == "integer":
            if w.specialValueText() and w.value() == w.minimum():
                return None
            return w.value()

        elif t == "float":
            if w.specialValueText() and w.value() == w.minimum():
                return None
            return w.value()

        elif t == "enum":
            v = w.currentData()
            return v if v else None

        elif t == "multi_enum":
            selected = []
            for i in range(w.count()):
                item = w.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected.append(item.text())
            return selected if selected else None

        elif t in ("file", "directory"):
            v = w._line_edit.text().strip()
            return v if v else None

        return None

    # ------------------------------------------------------------------
    # Preset serialization
    # ------------------------------------------------------------------

    def _raw_field_value(self, key: tuple) -> int | str | list | None:
        """Like get_field_value but ignores enabled state (reads widget regardless)."""
        field = self.fields.get(key)
        if not field:
            return None
        w = field["widget"]
        arg = field["arg"]
        t = arg["type"]

        # Fallback widget — treat as plain string regardless of declared type
        if getattr(w, "_is_fallback", False):
            v = w.text().strip()
            return v if v else None

        if t == "boolean":
            if isinstance(w, QCheckBox) and w.isChecked():
                if field["repeat_spin"]:
                    return field["repeat_spin"].value()
                return True
            return None

        elif t == "string":
            v = w.currentText().strip() if isinstance(w, QComboBox) else w.text().strip()
            return v if v else None

        elif t == "password":
            v = w._line_edit.text().strip()
            return v if v else None

        elif t == "text":
            v = w.toPlainText().strip()
            return v if v else None

        elif t == "integer":
            if w.specialValueText() and w.value() == w.minimum():
                return None
            return w.value()

        elif t == "float":
            if w.specialValueText() and w.value() == w.minimum():
                return None
            return w.value()

        elif t == "enum":
            v = w.currentData()
            return v if v else None

        elif t == "multi_enum":
            selected = []
            for i in range(w.count()):
                if w.item(i).checkState() == Qt.CheckState.Checked:
                    selected.append(w.item(i).text())
            return selected if selected else None

        elif t in ("file", "directory"):
            v = w._line_edit.text().strip()
            return v if v else None

        return None

    def serialize_values(self) -> dict:
        """Serialize all current field values to a flat dict for preset storage."""
        preset = {}
        preset["_format"] = "scaffold_preset"
        preset["_subcommand"] = self.get_current_subcommand()
        preset["_schema_hash"] = schema_hash(self.data)
        if self.elevation_check is not None:
            preset["_elevated"] = self.elevation_check.isChecked()
        extra_text = self.extra_flags_edit.toPlainText().strip()
        if self.extra_flags_group.isChecked() and extra_text:
            preset["_extra_flags"] = extra_text

        for key, field in self.fields.items():
            value = self._raw_field_value(key)
            if value is not None:
                # Use scope:flag as key to avoid collisions across subcommands
                scope, flag = key
                if scope == self.GLOBAL:
                    preset[flag] = value
                else:
                    preset[f"{scope}:{flag}"] = value

        return preset

    def apply_values(self, preset: dict) -> None:
        """Apply a preset dict to the form, resetting unmentioned fields to defaults."""
        self.blockSignals(True)

        # Subcommand
        sub = preset.get("_subcommand")
        if self.sub_combo is not None and sub:
            idx = self.sub_combo.findData(sub)
            if idx >= 0:
                self.sub_combo.setCurrentIndex(idx)

        # Elevation
        if self.elevation_check is not None and "_elevated" in preset:
            self.elevation_check.setChecked(bool(preset["_elevated"]))

        # Extra flags
        extra = preset.get("_extra_flags", "")
        if extra:
            self.extra_flags_group.setChecked(True)
            self.extra_flags_edit.setPlainText(extra)
        else:
            self.extra_flags_group.setChecked(False)
            self.extra_flags_edit.clear()

        # Apply field values — reset everything first, then set from preset
        for key, field in self.fields.items():
            scope, flag = key
            if scope == self.GLOBAL:
                preset_key = flag
            else:
                preset_key = f"{scope}:{flag}"
            value = preset.get(preset_key)
            self._set_field_value(key, value)

        self.blockSignals(False)
        self.command_changed.emit()

    def reset_to_defaults(self) -> None:
        """Reset all fields to their schema defaults."""
        self.blockSignals(True)

        if self.sub_combo is not None:
            self.sub_combo.setCurrentIndex(0)

        self.extra_flags_group.setChecked(False)
        self.extra_flags_edit.clear()

        if self.elevation_check is not None:
            self.elevation_check.setChecked(self.data.get("elevated") == "always")

        for key, field in self.fields.items():
            arg = field["arg"]
            default = arg["default"]
            t = arg["type"]
            if t == "boolean":
                self._set_field_value(key, True if default is True else None)
            else:
                self._set_field_value(key, default)

        self.blockSignals(False)
        self.command_changed.emit()

    def _set_field_value(self, key: tuple, value) -> None:
        """Set a widget's value. None resets to empty/default."""
        field = self.fields.get(key)
        if not field:
            return
        w = field["widget"]
        arg = field["arg"]
        t = arg["type"]

        # Fallback widget — treat as plain string regardless of declared type
        if getattr(w, "_is_fallback", False):
            w.setText(str(value) if value is not None else "")
            return

        if t == "boolean":
            if isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            if field["repeat_spin"] and isinstance(value, int) and value > 1:
                field["repeat_spin"].setValue(value)
            elif field["repeat_spin"]:
                field["repeat_spin"].setValue(1)

        elif t == "string":
            if isinstance(w, QComboBox):
                w.setCurrentText(str(value) if value is not None else "")
            else:
                w.setText(str(value) if value is not None else "")

        elif t == "password":
            w._line_edit.setText(str(value) if value is not None else "")

        elif t == "text":
            w.setPlainText(str(value) if value is not None else "")

        elif t == "integer":
            if value is not None:
                w.setValue(int(value))
            elif arg["default"] is not None:
                w.setValue(int(arg["default"]))
            else:
                w.setValue(w.minimum())

        elif t == "float":
            if value is not None:
                w.setValue(float(value))
            elif arg["default"] is not None:
                w.setValue(float(arg["default"]))
            else:
                w.setValue(w.minimum())

        elif t == "enum":
            if value is not None:
                idx = w.findData(str(value))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            else:
                w.setCurrentIndex(0)

        elif t == "multi_enum":
            selected = value if isinstance(value, list) else []
            for i in range(w.count()):
                item = w.item(i)
                if item.text() in selected:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)

        elif t in ("file", "directory"):
            w._line_edit.setText(str(value) if value is not None else "")

    # ------------------------------------------------------------------
    # Command assembly
    # ------------------------------------------------------------------

    def is_elevation_checked(self) -> bool:
        """Return True if the elevation checkbox exists and is checked."""
        if self.elevation_check is not None:
            return self.elevation_check.isChecked()
        return _check_already_elevated() and self.data.get("elevated") in ("optional", "always")

    def build_command(self) -> tuple[list[str], str]:
        """Build the CLI command. Returns (cmd_list, display_string)."""
        cmd = [self.data["binary"]]
        positional = []

        sub = self.get_current_subcommand()

        # Process global args before inserting subcommand name
        self._assemble_args(self.data["arguments"], self.GLOBAL, cmd, positional)

        # Insert subcommand name and its args
        if sub:
            sub_data = next(s for s in self.data["subcommands"] if s["name"] == sub)
            cmd.append(sub)
            self._assemble_args(sub_data["arguments"], sub, cmd, positional)

        # Positional args at end
        cmd.extend(positional)

        # Extra flags at very end
        cmd.extend(self.get_extra_flags())

        # Build display string
        display = _format_display(cmd)

        return cmd, display

    def _assemble_args(self, args: list, scope: str, cmd: list, positional: list) -> None:
        """Append active flag tokens to cmd and active positional tokens to positional."""
        for arg in args:
            flag = arg["flag"]
            key = self._field_key(scope, flag)
            value = self.get_field_value(key)
            if value is None:
                continue

            t = arg["type"]
            sep = arg["separator"]

            if arg["positional"]:
                if t == "multi_enum":
                    positional.extend(value)
                else:
                    positional.append(str(value))
                continue

            if t == "boolean":
                count = value if isinstance(value, int) else 1
                for _ in range(count):
                    cmd.append(flag)

            elif t == "multi_enum":
                joined = ",".join(value)
                if sep == "space":
                    cmd.extend([flag, joined])
                elif sep == "equals":
                    cmd.append(f"{flag}={joined}")
                else:
                    cmd.append(f"{flag}{joined}")

            else:
                sv = str(value)
                if sep == "space":
                    cmd.extend([flag, sv])
                elif sep == "equals":
                    cmd.append(f"{flag}={sv}")
                else:
                    cmd.append(f"{flag}{sv}")

    def update_theme(self) -> None:
        """Update theme-sensitive widget styles (required labels, validation borders)."""
        color = _required_color()
        for key, field in self.fields.items():
            arg = field["arg"]
            label = field["label"]
            if arg["required"]:
                name = arg["name"]
                label.setText(f"<b>{name} <span style='color:{color};'>*</span></b>")
            w = field["widget"]
            if w.styleSheet() and "border" in w.styleSheet():
                w.setStyleSheet(_invalid_style())
            if hasattr(w, "_line_edit") and w._line_edit.styleSheet() and "border" in w._line_edit.styleSheet():
                w._line_edit.setStyleSheet(_invalid_style())
        # Header separator
        sep_color = DARK_COLORS["border"] if _dark_mode else "#999999"
        self._header_sep.setStyleSheet(
            f"QFrame {{ color: {sep_color}; max-height: 1px; margin: 4px 0 2px 0; }}"
        )
        # Elevation note
        if hasattr(self, "_elevation_note"):
            note_color = DARK_COLORS["text_dim"] if _dark_mode else "gray"
            self._elevation_note.setStyleSheet(f"color: {note_color}; font-style: italic;")
        # Search no-match label
        err_color = DARK_COLORS["error"] if _dark_mode else "red"
        self._search_no_match_label.setStyleSheet(f"color: {err_color}; font-style: italic; margin-left: 4px;")

    def validate_required(self) -> list[tuple]:
        """Check required fields. Returns list of field keys that are missing values."""
        missing = []
        # Determine active scopes
        scopes = [(self.GLOBAL, self.data["arguments"])]
        sub = self.get_current_subcommand()
        if sub:
            sub_data = next(s for s in self.data["subcommands"] if s["name"] == sub)
            scopes.append((sub, sub_data["arguments"]))

        for scope, args in scopes:
            for arg in args:
                if not arg["required"]:
                    continue
                key = self._field_key(scope, arg["flag"])
                value = self.get_field_value(key)
                field = self.fields.get(key)
                if not field:
                    continue
                w = field["widget"]
                if value is None:
                    missing.append(key)
                    if hasattr(w, '_line_edit'):
                        w._line_edit.setStyleSheet(_invalid_style())
                    elif hasattr(w, 'setStyleSheet'):
                        w.setStyleSheet(_invalid_style())
                else:
                    if key not in self.validators:
                        if hasattr(w, '_line_edit'):
                            w._line_edit.setStyleSheet("")
                        elif hasattr(w, 'setStyleSheet'):
                            w.setStyleSheet("")

        return missing


def _format_display(cmd: list[str]) -> str:
    """Format a command list as a human-readable display string."""
    parts = []
    for token in cmd:
        if " " in token or "\t" in token:
            # Quote tokens with spaces for readability
            if "'" not in token:
                parts.append(f"'{token}'")
            else:
                parts.append(f'"{token}"')
        else:
            parts.append(token)
    return " ".join(parts)


def _quote_token(token: str) -> str:
    """Shell-quote a token for display if it contains whitespace."""
    if " " in token or "\t" in token:
        if "'" not in token:
            return f"'{token}'"
        return f'"{token}"'
    return token


def _colored_preview_html(cmd: list[str], extra_count: int, subcommand: str | None = None) -> str:
    """Build an HTML string with syntax-colored command tokens.

    Args:
        cmd: The full command list from build_command().
        extra_count: Number of tokens at the end that are extra flags.
        subcommand: The active subcommand name, if any, for distinct coloring.
    """
    import html as _html
    colors = DARK_PREVIEW if _dark_mode else LIGHT_PREVIEW
    parts = []
    core_len = len(cmd) - extra_count

    def _span(text: str, color: str, bold: bool = False, italic: bool = False) -> str:
        style = f"color:{color};"
        if bold:
            style += "font-weight:bold;"
        if italic:
            style += "font-style:italic;"
        return f"<span style='{style}'>{_html.escape(text)}</span>"

    i = 0
    while i < len(cmd):
        token = cmd[i]
        display_token = _quote_token(token)

        if i == 0:
            # Binary
            parts.append(_span(display_token, colors["binary"], bold=True))
        elif i >= core_len:
            # Extra flags section
            parts.append(_span(display_token, colors["extra"], italic=True))
        elif token.startswith("-"):
            # Flag — check for = separator (e.g., --flag=value)
            if "=" in token:
                flag_part, _, val_part = token.partition("=")
                display_flag = _quote_token(flag_part)
                display_val = _quote_token(val_part)
                parts.append(
                    _span(display_flag + "=", colors["flag"])
                    + _span(display_val, colors["value"])
                )
            else:
                parts.append(_span(display_token, colors["flag"]))
                # Next token is the value if it doesn't start with - and exists
                if i + 1 < core_len and not cmd[i + 1].startswith("-"):
                    i += 1
                    val_display = _quote_token(cmd[i])
                    parts.append(_span(val_display, colors["value"]))
        else:
            # Subcommand name or positional
            if subcommand and token == subcommand:
                parts.append(_span(display_token, colors["subcommand"], bold=True))
            else:
                parts.append(_span(display_token, colors["value"]))

        i += 1

    return " ".join(parts)


def _monospace_font() -> QFont:
    """Return a Consolas/monospace QFont for use in command preview and output panels."""
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def _tools_dir() -> Path:
    """Return the tools/ directory next to this script, creating it if needed."""
    d = Path(__file__).parent / "tools"
    if d.exists() and not d.is_dir():
        raise RuntimeError(f"Expected a directory but found a file at: {d}")
    d.mkdir(exist_ok=True)
    return d


def _presets_dir(tool_name: str) -> Path:
    """Return the presets/{tool_name}/ directory, creating it if needed.

    On first access for a tool, copies any bundled presets from
    default_presets/{tool_name}/ into the user's preset directory
    (without overwriting existing files).
    """
    d = Path(__file__).parent / "presets" / tool_name
    if d.exists() and not d.is_dir():
        raise RuntimeError(f"Expected a directory but found a file at: {d}")
    d.mkdir(parents=True, exist_ok=True)
    # Seed from bundled defaults (skip files the user already has)
    defaults = Path(__file__).parent / "default_presets" / tool_name
    if defaults.is_dir():
        for src in defaults.glob("*.json"):
            dest = d / src.name
            if not dest.exists():
                shutil.copy2(src, dest)
    return d


def _binary_in_path(binary: str) -> bool:
    """Check if binary is found in PATH."""
    return shutil.which(binary) is not None


# ---------------------------------------------------------------------------
# Tool picker
# ---------------------------------------------------------------------------

class ToolPicker(QWidget):
    """Displays available tools and lets the user pick one."""

    tool_selected = Signal(str)  # emits the file path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Scaffold — Select a Tool")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter tools...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self._on_filter)
        layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Tool", "Description", "Path"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel(
            "No tools found. Place JSON schema files in the tools/ directory,\n"
            "or use File \u2192 Load to open one."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; padding: 40px;")
        layout.addWidget(self.empty_label)

        btn_bar = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._on_open)
        btn_bar.addWidget(self.open_btn)

        load_btn = QPushButton("Load from File...")
        load_btn.clicked.connect(self._on_load_file)
        btn_bar.addWidget(load_btn)

        btn_bar.addStretch()

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete_tool)
        btn_bar.addWidget(self.delete_btn)

        layout.addLayout(btn_bar)

        self._entries = []  # list of (path, data_or_none, error_or_none, binary_available)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)
        QWidget.setTabOrder(self.search_bar, self.table)
        self.scan()

    def scan(self):
        """Scan tools/ directory and populate the table."""
        self._entries.clear()
        tools_path = _tools_dir()

        for json_file in sorted(tools_path.glob("*.json")):
            try:
                data = load_tool(str(json_file))
                errors = validate_tool(data)
                if errors:
                    self._entries.append((str(json_file), None, "; ".join(errors), False))
                else:
                    normalize_tool(data)
                    available = _binary_in_path(data["binary"])
                    self._entries.append((str(json_file), data, None, available))
            except RuntimeError as e:
                self._entries.append((str(json_file), None, str(e), False))

        # Sort: available tools first, then unavailable, then invalid — alphabetical within each group
        def _sort_key(entry):
            _, data, error, available = entry
            if error:
                priority = 2  # invalid last
            elif available:
                priority = 0  # available first
            else:
                priority = 1  # unavailable middle
            name = data["tool"].lower() if data else Path(entry[0]).name.lower()
            return (priority, name)

        self._entries.sort(key=_sort_key)
        self._populate_table()

    def _populate_table(self) -> None:
        """Render self._entries into the tool-picker table."""
        self.table.setRowCount(len(self._entries))

        for row, (path, data, error, available) in enumerate(self._entries):
            fname = Path(path).name

            # Status column
            if error:
                status_item = QTableWidgetItem("")
            elif available:
                status_item = QTableWidgetItem("\u2714")  # checkmark
                status_item.setForeground(QColor(COLOR_OK))
                status_item.setToolTip(f"'{data['binary']}' found in PATH — ready to use")
            else:
                status_item = QTableWidgetItem("\u2716")  # X mark
                status_item.setForeground(QColor(COLOR_ERR))
                status_item.setToolTip(
                    f"'{data['binary']}' not found in PATH. "
                    "Install it or add its location to your PATH."
                )
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if data:
                name_item = QTableWidgetItem(data["tool"])
                desc_item = QTableWidgetItem(data.get("description", ""))
            else:
                name_item = QTableWidgetItem(fname)
                desc_item = QTableWidgetItem(f"[invalid] {error}")
            path_item = QTableWidgetItem(fname)

            if error:
                for item in (status_item, name_item, desc_item, path_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setToolTip(error)
            elif not available:
                # Dim unavailable tools slightly but keep them selectable
                for item in (name_item, desc_item, path_item):
                    item.setForeground(QColor(COLOR_DIM))

            self.table.setItem(row, 0, status_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, desc_item)
            self.table.setItem(row, 3, path_item)

        has_items = len(self._entries) > 0
        self.table.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self.open_btn.setEnabled(False)
        self.search_bar.clear()
        self.search_bar.setFocus()

    def _on_filter(self, text: str) -> None:
        """Hide table rows that don't match the search text."""
        query = text.strip().lower()
        for row in range(self.table.rowCount()):
            if not query:
                self.table.setRowHidden(row, False)
                continue
            match = False
            for col in (1, 2, 3):  # tool name, description, path
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def keyPressEvent(self, event) -> None:
        """Handle Enter key to open the selected tool."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_open()
        else:
            super().keyPressEvent(event)

    def _on_selection(self) -> None:
        """Enable or disable Open/Delete buttons based on whether a valid tool row is selected."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.open_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
        row = rows[0].row()
        _, data, _, _ = self._entries[row]
        valid = data is not None
        self.open_btn.setEnabled(valid)
        self.delete_btn.setEnabled(valid)

    def _on_double_click(self, index) -> None:
        """Emit tool_selected for the double-clicked row if the tool is valid."""
        row = index.row()
        path, data, _, _ = self._entries[row]
        if data is not None:
            self.tool_selected.emit(path)

    def _on_open(self) -> None:
        """Emit tool_selected for the currently selected table row."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        path, data, _, _ = self._entries[row]
        if data is not None:
            self.tool_selected.emit(path)

    def _on_delete_tool(self) -> None:
        """Delete the selected tool schema (and optionally its presets) after confirmation."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._entries):
            return
        path_str, data, _, _ = self._entries[row]
        if data is None:
            return

        tool_name = data["tool"]
        tool_path = Path(path_str).resolve()
        tools_dir = _tools_dir().resolve()

        # Safety: ensure the file is inside the tools directory
        if tools_dir not in tool_path.parents:
            QMessageBox.warning(self, "Error", "File is not inside the tools directory.")
            return

        filename = tool_path.name
        presets_base = Path(__file__).parent / "presets"
        preset_dir = presets_base / tool_name
        preset_files = list(preset_dir.glob("*.json")) if preset_dir.is_dir() else []
        has_presets = len(preset_files) > 0

        if has_presets:
            msg = QMessageBox(self)
            msg.setWindowTitle("Delete Tool")
            msg.setText(
                f"Delete tool schema '{tool_name}'?\n\n"
                f"This will permanently remove {filename} from the tools directory.\n"
                f"This tool has {len(preset_files)} saved preset(s).\n\n"
                "Tip: Bundled files can be restored with:\n"
                f"  git checkout -- tools/{filename}\n"
                f"  git checkout -- presets/{tool_name}/"
            )
            btn_all = msg.addButton("Delete All", QMessageBox.ButtonRole.DestructiveRole)
            btn_schema = msg.addButton("Schema Only", QMessageBox.ButtonRole.AcceptRole)
            msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_all:
                delete_presets = True
            elif clicked == btn_schema:
                delete_presets = False
            else:
                return
        else:
            confirm = QMessageBox.question(
                self, "Delete Tool",
                f"Delete tool schema '{tool_name}'?\n\n"
                f"This will permanently remove {filename} from the tools directory.\n\n"
                "Tip: Bundled schemas can be restored with:\n"
                f"  git checkout -- tools/{filename}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            delete_presets = False

        # Delete the schema file
        try:
            tool_path.unlink()
        except OSError as e:
            QMessageBox.warning(self, "Delete Failed", f"Could not delete schema:\n{e}")
            return

        # Delete presets if requested
        if delete_presets and preset_dir.is_dir():
            resolved_preset = preset_dir.resolve()
            if presets_base.resolve() in resolved_preset.parents:
                try:
                    shutil.rmtree(resolved_preset)
                except OSError as e:
                    QMessageBox.warning(
                        self, "Partial Delete",
                        f"Schema deleted but failed to remove presets:\n{e}",
                    )

        self.scan()

    def _on_load_file(self) -> None:
        """Open a file-picker dialog and emit tool_selected for the chosen JSON."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Tool JSON", str(_tools_dir()), "JSON Files (*.json)"
        )
        if path:
            self.tool_selected.emit(path)


# ---------------------------------------------------------------------------
# Preset picker dialog
# ---------------------------------------------------------------------------

class PresetPicker(QDialog):
    """Modal dialog for selecting a preset, with favorite-star support."""

    def __init__(self, tool_name: str, presets_dir: Path, mode: str, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.presets_dir = presets_dir
        self.mode = mode  # "load", "delete", or "edit"
        self.selected_path: str | None = None
        self._presets: list[Path] = []  # ordered list matching table rows

        titles = {"load": "Load Preset", "delete": "Delete Preset", "edit": "Edit Preset"}
        self.setWindowTitle(f"{titles.get(mode, mode)} \u2014 {tool_name}")
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["\u2605", "Preset", "Description", "Last Modified"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self.table, 1)

        # Buttons — layout depends on mode
        btn_bar = QHBoxLayout()
        self.delete_btn = None  # only created in edit mode

        if mode == "edit":
            self.edit_desc_btn = QPushButton("Edit Description...")
            self.edit_desc_btn.setEnabled(False)
            self.edit_desc_btn.clicked.connect(self._on_edit_description)
            btn_bar.addWidget(self.edit_desc_btn)
            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setEnabled(False)
            self.delete_btn.clicked.connect(self._on_delete)
            btn_bar.addWidget(self.delete_btn)
            btn_bar.addStretch()
            self.action_btn = None  # no load/accept action in edit mode
            self.cancel_btn = QPushButton("Close")
            self.cancel_btn.clicked.connect(self.reject)
            btn_bar.addWidget(self.cancel_btn)
        else:
            btn_bar.addStretch()
            action_label = "Load" if mode == "load" else "Delete"
            self.action_btn = QPushButton(action_label)
            self.action_btn.setEnabled(False)
            self.action_btn.clicked.connect(self._on_action)
            btn_bar.addWidget(self.action_btn)
            self.edit_desc_btn = QPushButton("Edit Description...")
            self.edit_desc_btn.setEnabled(False)
            self.edit_desc_btn.clicked.connect(self._on_edit_description)
            btn_bar.addWidget(self.edit_desc_btn)
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self.reject)
            btn_bar.addWidget(self.cancel_btn)

        layout.addLayout(btn_bar)

        # Load favorites and populate
        self._favorites = self._load_favorites()
        self._populate()

    def _load_favorites(self) -> set[str]:
        """Read the favorites list for this tool from QSettings."""
        settings = QSettings("Scaffold", "Scaffold")
        raw = settings.value(f"favorites/{self.tool_name}", "[]")
        try:
            names = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(names, list):
                return set()
            return set(names)
        except (json.JSONDecodeError, TypeError):
            return set()

    def _save_favorites(self) -> None:
        """Write the favorites list for this tool to QSettings."""
        settings = QSettings("Scaffold", "Scaffold")
        settings.setValue(
            f"favorites/{self.tool_name}",
            json.dumps(sorted(self._favorites)),
        )

    def _populate(self) -> None:
        """Scan presets_dir and fill the table, cleaning stale favorites."""
        preset_files = sorted(self.presets_dir.glob("*.json"))

        # Clean stale favorites
        on_disk = {p.stem for p in preset_files}
        stale = self._favorites - on_disk
        if stale:
            self._favorites -= stale
            self._save_favorites()

        # Sort: favorites first, then alphabetical within each group
        def _sort_key(p: Path):
            is_fav = 0 if p.stem in self._favorites else 1
            return (is_fav, p.stem.lower())

        preset_files.sort(key=_sort_key)
        self._presets = preset_files

        self.table.setRowCount(len(preset_files))
        for row, p in enumerate(preset_files):
            name = p.stem
            is_fav = name in self._favorites

            # Column 0 — star
            star_item = QTableWidgetItem("\u2605" if is_fav else "\u2606")
            star_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, star_item)

            # Column 1 — name
            self.table.setItem(row, 1, QTableWidgetItem(name))

            # Column 2 — description (read _description from JSON)
            desc = ""
            try:
                pdata = json.loads(p.read_text(encoding="utf-8"))
                desc = pdata.get("_description", "") or ""
            except (json.JSONDecodeError, OSError):
                pass
            self.table.setItem(row, 2, QTableWidgetItem(desc))

            # Column 3 — last modified
            try:
                mtime = p.stat().st_mtime
                dt = datetime.datetime.fromtimestamp(mtime)
                date_str = dt.strftime("%b %d, %Y %I:%M %p")
            except OSError:
                date_str = "Unknown"
            self.table.setItem(row, 3, QTableWidgetItem(date_str))

        if self.action_btn is not None:
            self.action_btn.setEnabled(False)
        self.edit_desc_btn.setEnabled(False)
        if self.delete_btn is not None:
            self.delete_btn.setEnabled(False)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Toggle favorite star when column 0 is clicked."""
        if col != 0:
            return
        if row < 0 or row >= len(self._presets):
            return
        name = self._presets[row].stem
        if name in self._favorites:
            self._favorites.discard(name)
        else:
            self._favorites.add(name)
        self._save_favorites()

        # Remember selection, re-populate, try to re-select same preset
        self._populate()
        for r in range(len(self._presets)):
            if self._presets[r].stem == name:
                self.table.selectRow(r)
                break

    def _on_selection(self) -> None:
        """Enable/disable action buttons based on selection."""
        rows = self.table.selectionModel().selectedRows()
        has_selection = len(rows) > 0
        if self.action_btn is not None:
            self.action_btn.setEnabled(has_selection)
        self.edit_desc_btn.setEnabled(has_selection)
        if self.delete_btn is not None:
            self.delete_btn.setEnabled(has_selection)

    def _on_double_click(self, index) -> None:
        """Accept the dialog on double-click (load/delete modes only)."""
        if self.mode == "edit":
            return
        row = index.row()
        if 0 <= row < len(self._presets):
            self.selected_path = str(self._presets[row])
            self.accept()

    def _on_action(self) -> None:
        """Accept the dialog with the selected preset path."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if 0 <= row < len(self._presets):
            self.selected_path = str(self._presets[row])
            self.accept()

    def _on_edit_description(self) -> None:
        """Edit the _description field of the selected preset."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._presets):
            return
        preset_path = self._presets[row]

        # Read current preset
        try:
            text = preset_path.read_text(encoding="utf-8")
            data = json.loads(text)
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.warning(self, "Error", f"Cannot read preset file:\n{e}")
            return

        current_desc = data.get("_description", "")
        new_desc, ok = QInputDialog.getText(
            self, "Edit Description", "Description:", text=current_desc,
        )
        if not ok:
            return

        # Update only _description and write back
        data["_description"] = new_desc.strip()
        try:
            preset_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            QMessageBox.warning(self, "Error", f"Cannot write preset file:\n{e}")
            return

        # Update table cell in place
        desc_item = self.table.item(row, 2)
        if desc_item:
            desc_item.setText(new_desc.strip())
        titles = {"load": "Load Preset", "delete": "Delete Preset", "edit": "Edit Preset"}
        self.setWindowTitle(
            f"{titles.get(self.mode, self.mode)}"
            f" \u2014 {self.tool_name} \u2014 Description updated"
        )

    def _on_delete(self) -> None:
        """Delete the selected preset (edit mode). Confirms, removes file and table row."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._presets):
            return
        preset_path = self._presets[row]
        name = preset_path.stem

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete preset '{name}'?\n\n"
            "Tip: Bundled presets can be restored with:\n"
            f"  git checkout -- presets/{self.tool_name}/{name}.json",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            preset_path.unlink()
        except OSError as e:
            QMessageBox.warning(self, "Error", f"Cannot delete preset:\n{e}")
            return

        # Remove from internal list and table
        self._presets.pop(row)
        self._favorites.discard(name)
        self._save_favorites()
        self.table.removeRow(row)

        # If no presets remain, close the dialog
        if self.table.rowCount() == 0:
            self._deleted_last = True
            self.reject()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Main application window managing the tool picker, form view, and process execution."""

    def __init__(self, tool_path=None):
        super().__init__()
        self.data = None
        self.tool_path = None
        self.process = None
        self._killed = False
        self._timed_out = False
        self._elevated_run = False
        self._run_start_time: float | None = None
        self._force_kill_timer = QTimer(self)
        self._force_kill_timer.setSingleShot(True)
        self._force_kill_timer.setInterval(2000)
        self._force_kill_timer.timeout.connect(self._on_force_kill)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self.settings = QSettings("Scaffold", "Scaffold")

        # Restore geometry
        self.setMinimumSize(640, 400)
        geo = self.settings.value("window/geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        # Drag and drop
        self.setAcceptDrops(True)

        # Stacked central area: picker (index 0) and form container (index 1)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Picker
        self.picker = ToolPicker()
        self.picker.tool_selected.connect(self._load_tool_path)
        self.stack.addWidget(self.picker)

        # Form container (built on load)
        self.form_container = QWidget()
        self.form_container_layout = QVBoxLayout(self.form_container)
        self.form_container_layout.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.form_container)

        # Status bar
        if _check_already_elevated():
            self.statusBar().showMessage("Ready — Running as administrator")
        else:
            self.statusBar().showMessage("Ready")

        self._build_menu()
        self._build_shortcuts()

        if tool_path:
            self._load_tool_path(tool_path)
        else:
            # Try to reopen last tool
            last = self.settings.value("session/last_tool")
            if last and Path(last).exists():
                self._load_tool_path(last)
            else:
                self._show_picker()

    def _build_menu(self) -> None:
        """Build the menu bar with File, Presets, and View menus."""
        menu = self.menuBar().addMenu("File")

        self.act_load = menu.addAction("Load Tool...")
        self.act_load.setShortcut("Ctrl+O")
        self.act_load.triggered.connect(self._on_load_file)

        self.act_reload = menu.addAction("Reload Tool")
        self.act_reload.setShortcut("Ctrl+R")
        self.act_reload.triggered.connect(self._on_reload)
        self.act_reload.setEnabled(False)

        self.act_back = menu.addAction("Back to Tool List")
        self.act_back.setShortcut("Ctrl+B")
        self.act_back.triggered.connect(self._on_back)
        self.act_back.setEnabled(False)

        menu.addSeparator()

        act_exit = menu.addAction("Exit")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)

        # Presets menu (enabled when a tool is loaded)
        self.preset_menu = self.menuBar().addMenu("Presets")
        self.preset_menu.setEnabled(False)

        self.act_save_preset = self.preset_menu.addAction("Save Preset...")
        self.act_save_preset.setShortcut("Ctrl+S")
        self.act_save_preset.triggered.connect(self._on_save_preset)

        self.act_load_preset = self.preset_menu.addAction("Load Preset...")
        self.act_load_preset.setShortcut("Ctrl+L")
        self.act_load_preset.triggered.connect(self._on_load_preset)

        self.act_edit_preset = self.preset_menu.addAction("Edit Preset...")
        self.act_edit_preset.triggered.connect(self._on_edit_preset)

        self.preset_menu.addSeparator()

        self.act_import_preset = self.preset_menu.addAction("Import Preset...")
        self.act_import_preset.triggered.connect(self._on_import_preset)

        self.act_export_preset = self.preset_menu.addAction("Export Preset...")
        self.act_export_preset.triggered.connect(self._on_export_preset)

        self.preset_menu.addSeparator()

        self.act_reset = self.preset_menu.addAction("Reset to Defaults")
        self.act_reset.triggered.connect(self._on_reset_defaults)

        # View menu — theme selector
        view_menu = self.menuBar().addMenu("View")
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self.act_theme_light = QAction("Light", self, checkable=True)
        self.act_theme_light.setData("light")
        self.act_theme_dark = QAction("Dark", self, checkable=True)
        self.act_theme_dark.setData("dark")
        self.act_theme_system = QAction("System Default", self, checkable=True)
        self.act_theme_system.setData("system")
        for act in (self.act_theme_light, self.act_theme_dark, self.act_theme_system):
            theme_group.addAction(act)
            theme_menu.addAction(act)
        theme_group.triggered.connect(lambda act: self._set_theme(act.data()))
        self._sync_theme_checks()
        # Shortcut to toggle between light/dark
        toggle_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        toggle_shortcut.activated.connect(self._toggle_dark_mode)

        # Help menu
        help_menu = self.menuBar().addMenu("Help")
        act_about = help_menu.addAction("About Scaffold")
        act_about.triggered.connect(self._on_about)
        act_shortcuts = help_menu.addAction("Keyboard Shortcuts")
        act_shortcuts.triggered.connect(self._on_keyboard_shortcuts)

    def _sync_theme_checks(self) -> None:
        """Update View > Theme check marks to match the stored preference."""
        pref = self.settings.value("appearance/theme", "system")
        self.act_theme_light.setChecked(pref == "light")
        self.act_theme_dark.setChecked(pref == "dark")
        self.act_theme_system.setChecked(pref == "system")

    def _set_theme(self, pref: str) -> None:
        """Persist theme preference and apply it immediately."""
        self.settings.setValue("appearance/theme", pref)
        if pref == "dark":
            apply_theme(True)
        elif pref == "light":
            apply_theme(False)
        else:
            apply_theme(_detect_system_dark())
        self._apply_widget_theme()

    def _toggle_dark_mode(self) -> None:
        """Toggle between dark and light themes (Ctrl+D)."""
        self._set_theme("dark" if not _dark_mode else "light")
        self._sync_theme_checks()

    def _on_about(self) -> None:
        """Show the About Scaffold dialog."""
        QMessageBox.about(
            self,
            "About Scaffold",
            f"<b>Scaffold {__version__}</b><br><br>"
            "Dynamic GUI form generator for CLI tools.<br><br>"
            "<a href='https://github.com/Zencache/scaffold'>github.com/Zencache/scaffold</a>",
        )

    def _on_keyboard_shortcuts(self) -> None:
        """Show a list of keyboard shortcuts."""
        shortcuts = (
            "Ctrl+O          Load Tool...\n"
            "Ctrl+R          Reload Tool\n"
            "Ctrl+B          Back to Tool List\n"
            "Ctrl+Q          Exit\n"
            "\n"
            "Ctrl+S          Save Preset...\n"
            "Ctrl+L          Load Preset...\n"
            "\n"
            "Ctrl+D          Toggle Dark/Light Theme\n"
            "Ctrl+F          Find Field\n"
            "Ctrl+Shift+F    Search Output\n"
            "Ctrl+Enter      Run Command\n"
            "Escape          Stop Process / Close Search"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    def _apply_widget_theme(self) -> None:
        """Re-apply theme-sensitive inline stylesheets for output panel, preview bar, and warning bar."""
        # Output panel
        if hasattr(self, "output"):
            if _dark_mode:
                self.output.setStyleSheet(
                    f"QPlainTextEdit {{ background-color: {DARK_COLORS['output_bg']};"
                    f" color: {DARK_COLORS['output_text']}; }}"
                )
            else:
                self.output.setStyleSheet(
                    f"QPlainTextEdit {{ background-color: {OUTPUT_BG}; color: {OUTPUT_FG}; }}"
                )
        # Preview bar
        if hasattr(self, "preview"):
            if _dark_mode:
                self.preview.setStyleSheet(
                    f"QTextEdit {{ background-color: {DARK_COLORS['widget']};"
                    f" color: {DARK_COLORS['text']}; }}"
                )
            else:
                self.preview.setStyleSheet("")
            # Re-color preview with new theme colors
            if hasattr(self, "form") and self.form:
                self._update_preview()
        # Section labels and separators
        for attr in ("preview_label", "output_label"):
            if hasattr(self, attr):
                self._style_section_label(getattr(self, attr))
        # Form frame border
        if hasattr(self, "form_frame"):
            self._style_form_frame()
        # Drag handle
        if hasattr(self, "output_handle"):
            self.output_handle.update()
        # Run button
        if hasattr(self, "run_btn"):
            self._style_run_btn()
        # Warning bar
        if hasattr(self, "warning_bar") and self.warning_bar.isVisible():
            self._style_warning_bar()
        # Update required label colors in the form
        if hasattr(self, "form"):
            self.form.update_theme()
        # Force repaint
        QApplication.instance().setStyle(QApplication.instance().style().name())

    @staticmethod
    def _style_section_label(label: QLabel) -> None:
        """Apply theme-appropriate styling to a section header label."""
        color = DARK_COLORS["text_dim"] if _dark_mode else "#666666"
        label.setStyleSheet(
            "font-weight: bold; font-size: 11px; text-transform: uppercase;"
            f" letter-spacing: 1px; padding: 2px 0 1px 0; color: {color};"
        )


    def _style_form_frame(self) -> None:
        """Apply theme-appropriate border styling to the command options frame."""
        self.form_frame.setObjectName("form_frame")
        if _dark_mode:
            self.form_frame.setStyleSheet(
                f"QFrame#form_frame {{ border: 1px solid {DARK_COLORS['border']};"
                f" border-radius: 4px; background-color: {DARK_COLORS['window']}; }}"
            )
        else:
            self.form_frame.setStyleSheet(
                "QFrame#form_frame { border: 1px solid #999999;"
                " border-radius: 4px; }"
            )

    def _style_run_btn(self) -> None:
        """Apply green (Run), red (Stop), or amber (Stopping...) styling to the run button."""
        text = self.run_btn.text()
        if _dark_mode:
            if text == "Stop":
                self.run_btn.setStyleSheet(
                    f"QPushButton {{ background-color: #45272a; color: {DARK_COLORS['error']};"
                    f" border: 1px solid {DARK_COLORS['error']}; padding: 4px 16px;"
                    f" font-weight: bold; border-radius: 3px; }} "
                    f"QPushButton:hover {{ background-color: #5a3035; }}"
                )
            elif text == "Stopping...":
                self.run_btn.setStyleSheet(
                    f"QPushButton {{ background-color: #3a3020; color: {COLOR_WARN};"
                    f" border: 1px solid {COLOR_WARN}; padding: 4px 16px;"
                    f" font-style: italic; border-radius: 3px; }} "
                    f"QPushButton:disabled {{ background-color: #3a3020; color: {COLOR_WARN};"
                    f" border: 1px solid {COLOR_WARN}; padding: 4px 16px;"
                    f" font-style: italic; border-radius: 3px; }}"
                )
            else:
                self.run_btn.setStyleSheet(
                    f"QPushButton {{ background-color: #1e3a2a; color: {DARK_COLORS['success']};"
                    f" border: 1px solid {DARK_COLORS['success']}; padding: 4px 16px;"
                    f" font-weight: bold; border-radius: 3px; }} "
                    f"QPushButton:hover {{ background-color: #274d36; }}"
                )
        else:
            if text == "Stop":
                self.run_btn.setStyleSheet(
                    "QPushButton { background-color: #fdecea; color: #c62828;"
                    " border: 1px solid #ef9a9a; padding: 4px 16px;"
                    " font-weight: bold; border-radius: 3px; } "
                    "QPushButton:hover { background-color: #f9d0cd; }"
                )
            elif text == "Stopping...":
                self.run_btn.setStyleSheet(
                    f"QPushButton {{ background-color: #fdf5e6; color: #b8860b;"
                    f" border: 1px solid {COLOR_WARN}; padding: 4px 16px;"
                    f" font-style: italic; border-radius: 3px; }} "
                    f"QPushButton:disabled {{ background-color: #fdf5e6; color: #b8860b;"
                    f" border: 1px solid {COLOR_WARN}; padding: 4px 16px;"
                    f" font-style: italic; border-radius: 3px; }}"
                )
            else:
                self.run_btn.setStyleSheet(
                    "QPushButton { background-color: #e8f5e9; color: #2e7d32;"
                    " border: 1px solid #a5d6a7; padding: 4px 16px;"
                    " font-weight: bold; border-radius: 3px; } "
                    "QPushButton:hover { background-color: #c8e6c9; }"
                )

    def _style_warning_bar(self) -> None:
        """Apply theme-appropriate styling to the binary-not-found warning bar."""
        if _dark_mode:
            self.warning_bar.setStyleSheet(
                f"background-color: {DARK_COLORS['warning_bg']};"
                f" color: {DARK_COLORS['warning_text']};"
                f" padding: 6px 12px;"
                f" border: 1px solid {DARK_COLORS['warning_border']};"
                " font-weight: bold;"
            )
        else:
            self.warning_bar.setStyleSheet(
                f"background-color: {LIGHT_WARNING_BG}; color: {LIGHT_WARNING_FG};"
                f" padding: 6px 12px; border: 1px solid {LIGHT_WARNING_BORDER};"
                " font-weight: bold;"
            )

    def _build_shortcuts(self) -> None:
        """Register global keyboard shortcuts for Run (Ctrl+Enter), Stop (Escape), Find (Ctrl+F), Output Search (Ctrl+Shift+F)."""
        run_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_shortcut.activated.connect(self._shortcut_run)
        stop_shortcut = QShortcut(QKeySequence("Escape"), self)
        stop_shortcut.activated.connect(self._shortcut_stop)
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(self._shortcut_find)
        output_find_shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        output_find_shortcut.activated.connect(self._shortcut_output_find)

    def _shortcut_run(self) -> None:
        """Trigger Run via Ctrl+Enter when the form view is active and no process is running."""
        if self.data and self.stack.currentIndex() == 1:
            if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
                self._on_run_stop()

    def _shortcut_stop(self) -> None:
        """Trigger Stop via Escape — close output search first, then field search, then stop process."""
        if self._output_search_widget.isVisible() and self._output_search_bar.hasFocus():
            self._close_output_search()
            return
        if self.form and self.form._search_row_widget.isVisible():
            self.form.close_search()
            return
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._on_run_stop()

    def _shortcut_find(self) -> None:
        """Open field search bar via Ctrl+F when form view is active."""
        if self.form and self.stack.currentIndex() == 1:
            self.form.open_search()

    def _shortcut_output_find(self) -> None:
        """Open output search bar via Ctrl+Shift+F when form view is active."""
        if self.stack.currentIndex() == 1:
            self._output_search_widget.setVisible(True)
            self._output_search_bar.setFocus()
            self._output_search_bar.selectAll()

    # ------------------------------------------------------------------
    # Output search (Ctrl+Shift+F)
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        """Handle key events on the output search bar for Enter/Shift+Enter/Escape."""
        if obj is self._output_search_bar and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self._output_search_prev()
                else:
                    self._output_search_next()
                return True
            if key == Qt.Key.Key_Escape:
                self._close_output_search()
                return True
        return super().eventFilter(obj, event)

    def _close_output_search(self) -> None:
        """Hide output search bar and clear all highlights."""
        self._output_search_bar.clear()
        self._output_search_widget.setVisible(False)
        self._output_search_matches = []
        self._output_search_index = -1
        self._output_search_count_label.setText("")
        self.output.setExtraSelections([])
        self._output_search_bar.clearFocus()

    def _on_output_search_changed(self, text: str) -> None:
        """Recompute all matches and highlight them when search text changes."""
        self._output_search_matches = []
        self._output_search_index = -1
        query = text.strip()
        if not query:
            self._output_search_count_label.setText("")
            self.output.setExtraSelections([])
            return

        # Find all matches (case-insensitive)
        doc = self.output.document()
        cursor = QTextCursor(doc)
        flags = doc.FindFlag(0)  # no flags = forward, case-insensitive by default
        # QTextDocument.find is case-insensitive by default when no FindCaseSensitively flag is set
        while True:
            cursor = doc.find(query, cursor)
            if cursor.isNull():
                break
            start = cursor.selectionStart()
            length = cursor.selectionEnd() - start
            self._output_search_matches.append((start, length))

        if self._output_search_matches:
            self._output_search_index = 0
            self._output_search_count_label.setText(
                f"1 of {len(self._output_search_matches)}"
            )
        else:
            self._output_search_count_label.setText("0 matches")

        self._apply_output_search_highlights()

    def _apply_output_search_highlights(self) -> None:
        """Apply extraSelections to highlight all matches, current match in orange."""
        selections = []

        # Yellow for all matches
        yellow_fmt = QTextCharFormat()
        yellow_fmt.setBackground(QColor("#fff176"))
        yellow_fmt.setForeground(QColor("#000000"))

        # Orange for current match
        orange_fmt = QTextCharFormat()
        orange_fmt.setBackground(QColor("#ff9800"))
        orange_fmt.setForeground(QColor("#000000"))

        for i, (start, length) in enumerate(self._output_search_matches):
            sel = QTextEdit.ExtraSelection()
            cursor = QTextCursor(self.output.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor
            sel.format = orange_fmt if i == self._output_search_index else yellow_fmt
            selections.append(sel)

        self.output.setExtraSelections(selections)

        # Scroll to current match
        if self._output_search_index >= 0 and self._output_search_matches:
            start, length = self._output_search_matches[self._output_search_index]
            cursor = QTextCursor(self.output.document())
            cursor.setPosition(start)
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()

    def _output_search_next(self) -> None:
        """Jump to the next output search match (Enter key)."""
        if not self._output_search_matches:
            return
        self._output_search_index = (self._output_search_index + 1) % len(self._output_search_matches)
        total = len(self._output_search_matches)
        self._output_search_count_label.setText(
            f"{self._output_search_index + 1} of {total}"
        )
        self._apply_output_search_highlights()

    def _output_search_prev(self) -> None:
        """Jump to the previous output search match (Shift+Enter)."""
        if not self._output_search_matches:
            return
        self._output_search_index = (self._output_search_index - 1) % len(self._output_search_matches)
        total = len(self._output_search_matches)
        self._output_search_count_label.setText(
            f"{self._output_search_index + 1} of {total}"
        )
        self._apply_output_search_highlights()

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _clamp_output_height(self) -> None:
        """Ensure the output panel height fits within the current window."""
        max_h = min(OUTPUT_MAX_HEIGHT, self.height() // 2)
        cur_h = self.output.height()
        if cur_h > max_h:
            clamped = max(OUTPUT_MIN_HEIGHT, max_h)
            self.output.setFixedHeight(clamped)
            self.settings.setValue("output/height", clamped)

    def resizeEvent(self, event) -> None:
        """Clamp output panel height when the window shrinks."""
        super().resizeEvent(event)
        if hasattr(self, "output"):
            self._clamp_output_height()

    def showEvent(self, event) -> None:
        """Clamp restored output height against actual window size on first show."""
        super().showEvent(event)
        if hasattr(self, "output"):
            self._clamp_output_height()

    def closeEvent(self, event) -> None:
        """Persist window geometry and session state; kill any running process on exit."""
        self.settings.setValue("window/geometry", self.saveGeometry())
        if self.tool_path:
            self.settings.setValue("session/last_tool", self.tool_path)
        # Kill any running process
        self._stop_process()
        if self.process:
            self.process.waitForFinished(3000)
        event.accept()

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag events that contain at least one .json file URL."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".json"):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent) -> None:
        """Load the first .json file dropped onto the window."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".json"):
                self._load_tool_path(path)
                return

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_picker(self) -> None:
        """Switch to the tool-picker view and reset form-specific menu items."""
        self.picker.scan()
        self.stack.setCurrentIndex(0)
        self.setWindowTitle("Scaffold")
        self.act_reload.setEnabled(False)
        self.act_back.setEnabled(False)
        self.preset_menu.setEnabled(False)
        self.statusBar().showMessage("Ready")

    def _load_tool_path(self, path: str) -> None:
        """Load, validate, and display the tool at path; show an error dialog on failure."""
        try:
            data = load_tool(path)
        except RuntimeError as e:
            self._show_load_error(str(e))
            return

        # Three-tier _format check: correct → silent, missing → warn, wrong → reject
        fmt = data.get("_format")
        if fmt is not None and fmt != "scaffold_schema":
            QMessageBox.critical(
                self, "Wrong File Format",
                f'This file has "_format": "{fmt}" \u2014 '
                f"it appears to be a preset, not a tool schema."
                if fmt == "scaffold_preset"
                else f'This file has "_format": "{fmt}" \u2014 '
                f"it is not a Scaffold tool schema.",
            )
            return
        if fmt is None:
            btn = QMessageBox.warning(
                self, "Missing Format Marker",
                "This file doesn't contain a format marker. "
                "It may not be a Scaffold tool schema.\n\nLoad anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if btn != QMessageBox.StandardButton.Yes:
                return

        errors = validate_tool(data)
        if errors:
            self._show_load_error(
                f"Validation failed for {Path(path).name}:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
            return

        normalize_tool(data)
        self.data = data
        self.tool_path = path
        self._build_form_view()
        self.stack.setCurrentIndex(1)
        self.setWindowTitle(f"Scaffold \u2014 {data['tool']}")
        saved_timeout = int(self.settings.value(f"timeout/{data['tool']}", 0))
        self.timeout_spin.blockSignals(True)
        self.timeout_spin.setValue(saved_timeout)
        self.timeout_spin.blockSignals(False)
        self.act_reload.setEnabled(True)
        self.act_back.setEnabled(True)
        self.preset_menu.setEnabled(True)
        self.settings.setValue("session/last_tool", path)
        # Count fields and required fields for status message
        total_fields = len(data.get("arguments") or [])
        required_fields = sum(
            1 for a in (data.get("arguments") or []) if a.get("required")
        )
        if data.get("subcommands"):
            for sub in data["subcommands"]:
                total_fields += len(sub.get("arguments") or [])
                required_fields += sum(
                    1 for a in (sub.get("arguments") or []) if a.get("required")
                )
        self.statusBar().showMessage(
            f"Loaded {data['tool']} — {total_fields} fields ({required_fields} required)"
        )

        # Binary-in-PATH warning
        if not _binary_in_path(data["binary"]):
            self.warning_bar.setText(
                f"Warning: '{data['binary']}' not found in PATH"
            )
            self.warning_bar.setVisible(True)
        else:
            self.warning_bar.setVisible(False)

    def _show_load_error(self, msg: str) -> None:
        """Display a warning dialog for tool-load failures."""
        QMessageBox.warning(self, "Load Error", msg)

    def _build_form_view(self):
        """Tear down old form widgets and build fresh ones for self.data."""
        # Kill any running process
        self._elapsed_timer.stop()
        self._run_start_time = None
        self._stop_process()
        if self.process:
            self.process.waitForFinished(3000)
        self.process = None
        self._killed = False
        self._timed_out = False

        # Clear old contents
        layout = self.form_container_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Warning banner (non-blocking, at top)
        self.warning_bar = QLabel("")
        self._style_warning_bar()
        self.warning_bar.setVisible(False)
        layout.addWidget(self.warning_bar)

        # Form inside a bordered frame
        self.form = ToolForm(self.data)
        self.form_frame = QFrame()
        self.form_frame.setFrameShape(QFrame.Shape.Box)
        frame_layout = QVBoxLayout(self.form_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(self.form)
        self._style_form_frame()
        layout.addWidget(self.form_frame, 1)

        # -- Command Preview section --
        self.preview_label = QLabel("Command Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_section_label(self.preview_label)
        layout.addWidget(self.preview_label)

        preview_bar = QHBoxLayout()
        preview_bar.setContentsMargins(8, 0, 8, 0)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(_monospace_font())
        self.preview.setPlaceholderText("Command preview...")
        self.preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        line_height = self.preview.fontMetrics().lineSpacing()
        scrollbar_height = QApplication.style().pixelMetric(QApplication.style().PixelMetric.PM_ScrollBarExtent)
        self.preview.setFixedHeight(line_height + scrollbar_height + 12)
        if _dark_mode:
            self.preview.setStyleSheet(
                f"QTextEdit {{ background-color: {DARK_COLORS['widget']};"
                f" color: {DARK_COLORS['text']}; }}"
            )
        preview_bar.addWidget(self.preview, 1)

        self.copy_btn = QPushButton("Copy Command")
        self.copy_btn.clicked.connect(self._copy_command)
        preview_bar.addWidget(self.copy_btn)

        preview_widget = QWidget()
        preview_widget.setLayout(preview_bar)
        layout.addWidget(preview_widget)

        # Status label
        self.status = QLabel("")
        self.status.setStyleSheet("padding: 0 8px 0 8px;")
        layout.addWidget(self.status)

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status.setText(""))

        # Action buttons bar
        action_widget = QWidget()
        action_bar = QHBoxLayout(action_widget)
        action_bar.setContentsMargins(8, 0, 8, 0)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._on_run_stop)
        self._style_run_btn()
        action_bar.addWidget(self.run_btn)

        self.clear_btn = QPushButton("Clear Output")
        self.clear_btn.clicked.connect(self._clear_output)
        action_bar.addWidget(self.clear_btn)

        self.copy_output_btn = QPushButton("Copy Output")
        self.copy_output_btn.clicked.connect(self._copy_output)
        action_bar.addWidget(self.copy_output_btn)

        self.save_output_btn = QPushButton("Save Output...")
        self.save_output_btn.clicked.connect(self._save_output)
        action_bar.addWidget(self.save_output_btn)

        action_bar.addStretch()

        timeout_label = QLabel("Timeout (s):")
        action_bar.addWidget(timeout_label)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 99999)
        self.timeout_spin.setToolTip("Auto-kill after N seconds (0 = no timeout)")
        self.timeout_spin.setFixedWidth(80)
        self.timeout_spin.valueChanged.connect(self._on_timeout_changed)
        action_bar.addWidget(self.timeout_spin)

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout_fired)
        layout.addWidget(action_widget)

        # -- Output section --
        self.output_label = QLabel("Output")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_section_label(self.output_label)
        layout.addWidget(self.output_label)

        # Output search bar (Ctrl+Shift+F) — initially hidden
        self._output_search_bar = QLineEdit()
        self._output_search_bar.setPlaceholderText("Search output...  (Ctrl+Shift+F)")
        self._output_search_bar.textChanged.connect(self._on_output_search_changed)
        self._output_search_bar.installEventFilter(self)
        self._output_search_matches: list[tuple[int, int]] = []  # (start, length)
        self._output_search_index = -1
        self._output_search_count_label = QLabel("")
        self._output_search_count_label.setStyleSheet("margin-left: 4px;")
        output_search_row = QHBoxLayout()
        output_search_row.setContentsMargins(0, 0, 0, 0)
        output_search_row.addWidget(self._output_search_bar, 1)
        output_search_row.addWidget(self._output_search_count_label)
        self._output_search_widget = QWidget()
        self._output_search_widget.setLayout(output_search_row)
        self._output_search_widget.setVisible(False)
        layout.addWidget(self._output_search_widget)

        # Output panel (create first so DragHandle can reference it)
        saved_height = int(self.settings.value("output/height", OUTPUT_DEFAULT_HEIGHT))
        saved_height = max(OUTPUT_MIN_HEIGHT, min(OUTPUT_MAX_HEIGHT, saved_height))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(_monospace_font())
        self.output.setFixedHeight(saved_height)
        self.output.setMaximumBlockCount(OUTPUT_MAX_BLOCKS)

        # Drag handle to resize output panel
        self.output_handle = DragHandle(self.output, self.settings)
        layout.addWidget(self.output_handle)
        if _dark_mode:
            self.output.setStyleSheet(
                f"QPlainTextEdit {{ background-color: {DARK_COLORS['output_bg']};"
                f" color: {DARK_COLORS['output_text']}; }}"
            )
        else:
            self.output.setStyleSheet(
                f"QPlainTextEdit {{ background-color: {OUTPUT_BG}; color: {OUTPUT_FG}; }}"
            )
        layout.addWidget(self.output)

        # Output batching buffer — collect readyRead data and flush on a timer
        self._output_buffer: list[tuple[str, str]] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(OUTPUT_FLUSH_MS)
        self._flush_timer.timeout.connect(self._flush_output)

        # Connect live preview
        self.form.command_changed.connect(self._update_preview)
        self._update_preview()

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _on_load_file(self) -> None:
        """Open a file-picker dialog and load the chosen JSON tool schema."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Tool JSON", str(_tools_dir()), "JSON Files (*.json)"
        )
        if path:
            self._load_tool_path(path)

    def _on_reload(self) -> None:
        """Reload the current tool schema from disk."""
        if self.tool_path:
            self._load_tool_path(self.tool_path)

    def _on_back(self) -> None:
        """Return to the tool picker, stopping any running process first."""
        # Kill any running process before going back
        self._stop_process()
        if self.process:
            self.process.waitForFinished(3000)
        self.process = None
        self._show_picker()

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _on_save_preset(self) -> None:
        """Prompt for a name and save the current form state as a preset JSON file."""
        if not self.data:
            return
        name, ok = QInputDialog.getText(
            self, "Save Preset", "Preset name:",
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        description, ok2 = QInputDialog.getText(
            self, "Save Preset", "Description (optional):",
        )
        if not ok2:
            return
        description = description.strip()

        # Sanitize filename
        safe_name = re.sub(r'[^\w\-. ]', '_', name)
        preset_dir = _presets_dir(self.data["tool"])
        preset_path = preset_dir / f"{safe_name}.json"

        preset = self.form.serialize_values()
        preset["_description"] = description
        try:
            preset_path.write_text(
                json.dumps(preset, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            self.statusBar().showMessage(f"Error saving preset: {e}")
            return
        self.statusBar().showMessage(f"Preset saved: {safe_name}")

    def _on_load_preset(self) -> None:
        """Show a preset picker and restore the selected preset to the form."""
        if not self.data:
            return
        preset_dir = _presets_dir(self.data["tool"])
        presets = sorted(preset_dir.glob("*.json"))
        if not presets:
            QMessageBox.information(self, "No Presets", "No saved presets for this tool.")
            return

        picker = PresetPicker(self.data["tool"], preset_dir, mode="load", parent=self)
        if not picker.exec() or not picker.selected_path:
            return

        preset_path = Path(picker.selected_path)
        name = preset_path.stem

        # Size guard — same limit as tool schemas
        try:
            size = preset_path.stat().st_size
        except OSError:
            size = 0
        if size > MAX_SCHEMA_SIZE:
            QMessageBox.warning(
                self, "Preset Too Large",
                f"Preset file too large ({size:,} bytes, limit {MAX_SCHEMA_SIZE:,}).",
            )
            return

        try:
            preset = json.loads(preset_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            self.statusBar().showMessage(f"Error loading preset: {e}")
            return

        # Three-tier _format check: correct/missing → silent, wrong → reject
        fmt = preset.get("_format")
        if fmt is not None and fmt != "scaffold_preset":
            QMessageBox.critical(
                self, "Wrong File Format",
                f'This file has "_format": "{fmt}" \u2014 '
                f"it appears to be a tool schema, not a preset."
                if fmt == "scaffold_schema"
                else f'This file has "_format": "{fmt}" \u2014 '
                f"it is not a Scaffold preset.",
            )
            return

        # Validate preset structure
        verrors = validate_preset(preset)
        if verrors:
            QMessageBox.warning(
                self, "Invalid Preset",
                f"Preset '{name}' failed validation:\n"
                + "\n".join(f"  - {e}" for e in verrors),
            )
            return

        self.form.apply_values(preset)

        # Check schema hash for version mismatch
        saved_hash = preset.get("_schema_hash")
        if saved_hash is not None and saved_hash != schema_hash(self.data):
            self.statusBar().showMessage(
                f"Preset loaded: {name} \u2014 Note: This preset was saved with a different "
                "schema version. Some fields may not have loaded."
            )
        else:
            self.statusBar().showMessage(f"Preset loaded: {name}")

    def _on_edit_preset(self) -> None:
        """Open the preset picker in edit mode for managing descriptions and deleting."""
        if not self.data:
            return
        preset_dir = _presets_dir(self.data["tool"])
        presets = sorted(preset_dir.glob("*.json"))
        if not presets:
            self.statusBar().showMessage("No presets to edit")
            return
        picker = PresetPicker(self.data["tool"], preset_dir, mode="edit", parent=self)
        picker.exec()
        if getattr(picker, "_deleted_last", False):
            self.statusBar().showMessage("No presets remaining")

    def _on_import_preset(self) -> None:
        """Import a preset JSON file into the current tool's preset directory."""
        if not self.data:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Preset", "", "JSON files (*.json)",
        )
        if not path:
            return
        src = Path(path)

        # Size guard — same limit as tool schemas
        try:
            size = src.stat().st_size
        except OSError:
            size = 0
        if size > MAX_SCHEMA_SIZE:
            QMessageBox.warning(
                self, "Import Failed",
                f"Preset file too large ({size:,} bytes, limit {MAX_SCHEMA_SIZE:,}).",
            )
            return

        try:
            raw = src.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as e:
            self.statusBar().showMessage(f"Import failed: invalid JSON — {e}")
            return
        if not isinstance(data, dict):
            self.statusBar().showMessage("Import failed: file is not a JSON object")
            return

        # Validate preset structure before importing
        verrors = validate_preset(data)
        if verrors:
            QMessageBox.warning(
                self, "Import Failed",
                "Preset failed validation:\n"
                + "\n".join(f"  - {e}" for e in verrors),
            )
            return

        name = src.stem
        preset_dir = _presets_dir(self.data["tool"])
        dest = preset_dir / f"{name}.json"

        if dest.exists():
            answer = QMessageBox.question(
                self, "Overwrite Preset",
                f"Overwrite existing preset '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            dest.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            self.statusBar().showMessage(f"Import failed: {e}")
            return
        self.statusBar().showMessage(f"Preset imported: {name}")

    def _on_export_preset(self) -> None:
        """Export an existing preset to a user-chosen location."""
        if not self.data:
            return
        preset_dir = _presets_dir(self.data["tool"])
        presets = sorted(preset_dir.glob("*.json"))
        if not presets:
            self.statusBar().showMessage("No presets to export")
            return

        names = [p.stem for p in presets]
        name, ok = QInputDialog.getItem(
            self, "Export Preset", "Select preset:", names, 0, False,
        )
        if not ok:
            return

        preset_path = preset_dir / f"{name}.json"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Preset", f"{name}.json", "JSON files (*.json)",
        )
        if not dest:
            return

        try:
            content = preset_path.read_text(encoding="utf-8")
            Path(dest).write_text(content, encoding="utf-8")
        except OSError as e:
            self.statusBar().showMessage(f"Export failed: {e}")
            return
        self.statusBar().showMessage(f"Preset exported: {name}")

    def _on_reset_defaults(self) -> None:
        """Reset all form fields to their schema-defined defaults."""
        if self.data:
            self.form.reset_to_defaults()
            self.statusBar().showMessage("Reset to defaults")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        """Rebuild the command preview and toggle Run button availability."""
        missing = self.form.validate_required()
        cmd, display = self.form.build_command()
        extra_count = len(self.form.get_extra_flags())
        if self.form.is_elevation_checked():
            elev_cmd, _ = get_elevation_command(cmd)
            extra_count = len(self.form.get_extra_flags())
            cmd = elev_cmd
            display = _format_display(elev_cmd)
        sub = self.form.sub_combo.currentData() if self.form.sub_combo else None
        html = _colored_preview_html(cmd, extra_count, subcommand=sub)
        self.preview.setHtml(html)
        process_running = (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        )
        if missing:
            names = []
            for key in missing:
                field = self.form.fields.get(key)
                if field:
                    names.append(field["arg"]["name"])
            self._show_status(f"Required: {', '.join(names)}")
            # Keep Stop button clickable while a process is running
            self.run_btn.setEnabled(process_running)
        else:
            self.status.setText("")
            self.status.setStyleSheet("padding: 0 8px 4px 8px;")
            self.run_btn.setEnabled(True)

    def _copy_command(self) -> None:
        """Copy the current command (including elevation prefix if active) to the clipboard."""
        cmd, display = self.form.build_command()
        if self.form.is_elevation_checked():
            elev_cmd, _ = get_elevation_command(cmd)
            display = _format_display(elev_cmd)
        QApplication.clipboard().setText(display)
        color = DARK_COLORS["success"] if _dark_mode else "green"
        self._show_status("Copied to clipboard.", color)

    def _copy_output(self) -> None:
        """Copy the output panel's plain text to the clipboard."""
        text = self.output.toPlainText()
        if not text.strip():
            self._show_status("No output to copy")
            return
        QApplication.clipboard().setText(text)
        color = DARK_COLORS["success"] if _dark_mode else "green"
        self._show_status("Output copied to clipboard.", color)

    def _show_status(self, text: str, color: str | None = None) -> None:
        """Display a colored message in the status label below the command preview."""
        if color is None:
            color = DARK_COLORS["error"] if _dark_mode else "red"
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; padding: 0 8px 4px 8px;")
        self._status_timer.start(3000)

    # ------------------------------------------------------------------
    # Process execution
    # ------------------------------------------------------------------

    def _on_timeout_changed(self, value: int) -> None:
        """Persist the timeout value per tool in QSettings."""
        if self.data:
            self.settings.setValue(f"timeout/{self.data['tool']}", value)

    def _stop_process(self) -> None:
        """Stop the running process. Uses SIGTERM first, SIGKILL as fallback."""
        if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
            return
        self._killed = True
        self._timeout_timer.stop()
        self.process.terminate()  # SIGTERM — pkexec can forward this
        self._force_kill_timer.start()

    def _on_force_kill(self) -> None:
        """Escalate to SIGKILL if the process did not exit after SIGTERM."""
        if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
            return
        if not self._elevated_run and sys.platform != "win32":
            pid = self.process.processId()
            if pid > 0:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
        self.process.kill()

    def _on_timeout_fired(self) -> None:
        """Kill the running process because the timeout expired."""
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            timeout_val = self.timeout_spin.value()
            self._timed_out = True
            self._append_output(
                f"\n--- Process timed out after {timeout_val} seconds ---\n",
                COLOR_WARN,
            )
            self.run_btn.setText("Stopping...")
            self.run_btn.setEnabled(False)
            self._style_run_btn()
            QApplication.processEvents()  # Force repaint before kill
            self._stop_process()

    def _on_run_stop(self) -> None:
        """Run the command if idle, or stop the running process if one is active."""
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.run_btn.setText("Stopping...")
            self.run_btn.setEnabled(False)
            self._style_run_btn()
            QApplication.processEvents()  # Force repaint before kill
            self._stop_process()
            return

        # Validate required fields
        missing = self.form.validate_required()
        if missing:
            return

        cmd, display = self.form.build_command()
        if not cmd:
            return

        # Handle elevation
        self._elevated_run = False
        if self.form.is_elevation_checked():
            elev_cmd, error = get_elevation_command(cmd)
            if error:
                QMessageBox.warning(self, "Elevation Not Available", error)
                return
            cmd = elev_cmd
            display = _format_display(cmd)
            self._elevated_run = True

        program = cmd[0]
        arguments = cmd[1:]

        self.process = QProcess(self)
        self.process.setProgram(program)
        self.process.setArguments(arguments)
        self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self.process.readyReadStandardError.connect(self._on_stderr_ready)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        # Show what we're running
        self._append_output(f"$ {display}\n", COLOR_CMD)

        self._killed = False
        self._timed_out = False
        self._run_start_time = time.monotonic()
        self.run_btn.setText("Stop")
        self._style_run_btn()
        self.statusBar().showMessage("Running... (0s)")
        self._elapsed_timer.start()
        timeout_secs = self.timeout_spin.value()
        if timeout_secs > 0:
            self._timeout_timer.start(timeout_secs * 1000)
        self.process.start()

    def _on_stdout_ready(self) -> None:
        """Buffer available stdout data for the next flush cycle."""
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        self._output_buffer.append((text, OUTPUT_FG))
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _on_stderr_ready(self) -> None:
        """Buffer available stderr data for the next flush cycle."""
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        self._output_buffer.append((text, COLOR_WARN))
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush_output(self) -> None:
        """Flush buffered output to the panel in a single batch update."""
        self._flush_timer.stop()
        if not self._output_buffer:
            return
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        for text, color in self._output_buffer:
            text = _ANSI_RE.sub('', text)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.insertText(text, fmt)
        self._output_buffer.clear()
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _update_elapsed(self) -> None:
        """Tick the status bar with elapsed seconds while a process is running."""
        if self._run_start_time is not None:
            elapsed = int(time.monotonic() - self._run_start_time)
            self.statusBar().showMessage(f"Running... ({elapsed}s)")

    def _on_finished(self, exit_code: int, exit_status) -> None:
        """Handle process termination: print exit status and re-enable the Run button."""
        self._elapsed_timer.stop()
        self._timeout_timer.stop()
        self._force_kill_timer.stop()
        self._flush_output()
        elapsed_str = ""
        if self._run_start_time is not None:
            elapsed = time.monotonic() - self._run_start_time
            elapsed_str = f" ({elapsed:.1f}s)"
            self._run_start_time = None
        if self._timed_out:
            self.statusBar().showMessage(f"Timed out{elapsed_str}")
        elif self._killed:
            self._append_output("\n--- Process stopped ---\n", COLOR_WARN)
            self.statusBar().showMessage(f"Process stopped{elapsed_str}")
        elif self._elevated_run and exit_code in (126, 127):
            self._append_output(
                "\n--- Elevation was cancelled by the user. ---\n", COLOR_WARN
            )
            self.statusBar().showMessage("Elevation cancelled")
        elif exit_code == 0:
            self._append_output(f"\n--- Process exited with code {exit_code} ---\n", COLOR_OK)
            self.statusBar().showMessage(f"Exit 0{elapsed_str}")
        else:
            self._append_output(f"\n--- Process exited with code {exit_code} ---\n", COLOR_ERR)
            self.statusBar().showMessage(f"Exit {exit_code}{elapsed_str}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run")
        self._style_run_btn()
        self._update_preview()
        self.process = None

    def _on_error(self, error) -> None:
        """Handle QProcess errors, printing a descriptive message to the output panel."""
        if error == QProcess.ProcessError.Crashed and self._killed:
            return  # Handled by _on_finished
        error_messages = {
            QProcess.ProcessError.FailedToStart: (
                f"Error: '{self.data['binary']}' not found. "
                "Is it installed and in your PATH?"
                if not self._elevated_run else
                f"Error: Failed to start elevated command. "
                f"Check that '{self.data['binary']}' is installed and in your PATH."
            ),
            QProcess.ProcessError.Crashed: "Process crashed unexpectedly.",
            QProcess.ProcessError.Timedout: "Process timed out.",
            QProcess.ProcessError.WriteError: "Write error communicating with process.",
            QProcess.ProcessError.ReadError: "Read error communicating with process.",
        }
        msg = error_messages.get(error, f"Unknown process error ({error}).")
        self._append_output(f"\n--- {msg} ---\n", COLOR_ERR)
        self.statusBar().showMessage(msg)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run")
        self._style_run_btn()
        self._update_preview()
        # Clean up timers and process — needed for FailedToStart where
        # _on_finished() is never called.  Harmless double-set for Crashed.
        self._elapsed_timer.stop()
        self._force_kill_timer.stop()
        self._run_start_time = None
        self.process = None

    def _append_output(self, text: str, color: str) -> None:
        """Append text to the output panel in the given hex color string."""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text, fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _clear_output(self) -> None:
        """Clear all text from the output panel."""
        self.output.clear()

    def _save_output(self, path: str | None = None) -> None:
        """Save the output panel contents to a text file."""
        # clicked signal passes a bool — normalize to None
        if not isinstance(path, str):
            path = None
        text = self.output.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("No output to save", 3000)
            return

        if path is None:
            tool_name = self.data["tool"] if self.data else "output"
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"{tool_name}_output_{stamp}.txt"
            default_path = str(Path.home() / default_name)
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Output", default_path,
                "Text Files (*.txt);;All Files (*)"
            )
        if not path:
            return

        try:
            Path(path).write_text(text, encoding="utf-8")
            self.statusBar().showMessage(f"Output saved to {path}", 3000)
        except OSError as e:
            self.statusBar().showMessage(f"Error saving output: {e}", 5000)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def print_prompt() -> None:
    """Print the LLM schema-generation prompt from PROMPT.txt to stdout."""
    prompt_path = Path(__file__).parent / "PROMPT.txt"
    if not prompt_path.exists():
        print("Error: PROMPT.txt not found alongside scaffold.py", file=sys.stderr)
        sys.exit(1)
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading PROMPT.txt: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")


def main() -> None:
    """Entry point: handle --help / --prompt / --validate CLI flags, then launch the GUI."""
    if "--version" in sys.argv or "-V" in sys.argv:
        print(f"Scaffold {__version__}")
        sys.exit(0)

    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            f"Scaffold {__version__} - CLI-to-GUI Translation Layer\n"
            "\n"
            "Usage:\n"
            "  python scaffold.py                        Launch the tool picker GUI\n"
            "  python scaffold.py <tool.json>            Open a specific tool directly\n"
            "  python scaffold.py --validate <tool.json> Validate a schema (no GUI)\n"
            "  python scaffold.py --prompt               Print the LLM schema-generation prompt\n"
            "  python scaffold.py --version              Show version and exit\n"
            "  python scaffold.py --help                 Show this help and exit\n"
        )
        sys.exit(0)

    if "--prompt" in sys.argv:
        print_prompt()
        sys.exit(0)

    if "--validate" in sys.argv:
        idx = sys.argv.index("--validate")
        if idx + 1 >= len(sys.argv):
            print("Usage: python scaffold.py --validate <tool.json>", file=sys.stderr)
            sys.exit(1)
        path = sys.argv[idx + 1]

        try:
            data = load_tool(path)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        errors = validate_tool(data)
        if errors:
            print(f"Validation failed for {path}:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            normalize_tool(data)
            arg_count = len(data.get("arguments", []))
            sub_count = len(data.get("subcommands") or [])
            for sub in data.get("subcommands") or []:
                arg_count += len(sub.get("arguments", []))
            print(f"Valid: {data['tool']} ({arg_count} arguments, {sub_count} subcommands)")
            sys.exit(0)

    # GUI launch
    app = QApplication(sys.argv)

    # Apply theme from settings or system detection
    settings = QSettings("Scaffold", "Scaffold")
    theme_pref = settings.value("appearance/theme", "system")
    if theme_pref == "dark":
        apply_theme(True)
    elif theme_pref == "light":
        apply_theme(False)
    else:
        apply_theme(_detect_system_dark())

    # Direct launch with a JSON path
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        path = args[0]
        try:
            data = load_tool(path)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        errors = validate_tool(data)
        if errors:
            print(f"Validation failed for {path}:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

        window = MainWindow(tool_path=path)
    else:
        # No args — show tool picker
        window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
