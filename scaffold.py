"""Scaffold — CLI-to-GUI Translation Layer."""

import json
import re
import shlex
import shutil
import sys
from pathlib import Path

VALID_TYPES = {"boolean", "string", "text", "integer", "float", "enum", "multi_enum", "file", "directory"}
VALID_SEPARATORS = {"space", "equals", "none"}

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
}


# ---------------------------------------------------------------------------
# Phase 3 — JSON loader, validator, normalizer
# ---------------------------------------------------------------------------

def load_tool(path):
    """Read and parse a JSON tool file. Raises RuntimeError on failure."""
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"File not found: {p}")
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Cannot read file: {p} — {e}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {p} — {e}")


def validate_tool(data):
    """Validate a tool dict against the schema. Returns a list of error strings."""
    errors = []

    for key in ("tool", "binary", "description", "arguments"):
        if key not in data:
            errors.append(f"Missing required top-level key: \"{key}\"")

    if "arguments" in data and not isinstance(data["arguments"], list):
        errors.append("\"arguments\" must be a list")

    if "arguments" in data and isinstance(data["arguments"], list):
        _validate_args(data["arguments"], "top-level", errors)
        _check_duplicate_flags(data["arguments"], "top-level", errors)
        _check_groups(data["arguments"], "top-level", errors)

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

    return errors


def _validate_args(args, scope, errors):
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


def _check_duplicate_flags(args, scope, errors):
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


def _check_groups(args, scope, errors):
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


def normalize_tool(data):
    """Fill in missing optional fields with safe defaults."""
    data.setdefault("subcommands", None)
    data.setdefault("description", "")

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


# ---------------------------------------------------------------------------
# Phase 4 — GUI Renderer
# ---------------------------------------------------------------------------

from PySide6.QtCore import QProcess, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QKeySequence, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QInputDialog, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)


INVALID_STYLE = "border: 1px solid red;"


class ToolForm(QWidget):
    """Dynamically renders a GUI form from a validated, normalized tool dict."""

    command_changed = Signal()

    # Scope constant for global (top-level) arguments
    GLOBAL = "__global__"

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        # (scope, flag) -> {arg, widget, label, radio, repeat_spin}
        self.fields = {}
        # (scope, group_name) -> list of (scope, flag) keys
        self.groups = {}
        # (scope, flag) -> compiled regex
        self.validators = {}

        self._build_ui()
        self._apply_groups()
        self._apply_dependencies()

    def _field_key(self, scope, flag):
        return (scope, flag)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        header = QLabel(self.data["tool"])
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(header)

        if self.data["description"]:
            desc = QLabel(self.data["description"])
            desc.setWordWrap(True)
            root.addWidget(desc)

        # Subcommand selector
        self.sub_combo = None
        if self.data["subcommands"]:
            row = QHBoxLayout()
            row.addWidget(QLabel("Subcommand:"))
            self.sub_combo = QComboBox()
            for sub in self.data["subcommands"]:
                label = sub["name"]
                if sub.get("description"):
                    label += f"  —  {sub['description']}"
                self.sub_combo.addItem(label, sub["name"])
            row.addWidget(self.sub_combo, 1)
            root.addLayout(row)
            self.sub_combo.currentIndexChanged.connect(self._on_subcommand_changed)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll, 1)

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

    def _build_extra_flags(self):
        group = QGroupBox("Additional Flags")
        group.setCheckable(True)
        group.setChecked(False)
        layout = QVBoxLayout()
        self.extra_flags_edit = QPlainTextEdit()
        self.extra_flags_edit.setMaximumHeight(80)
        self.extra_flags_edit.setToolTip(
            "Raw flags appended directly to the command. "
            "Use this for flags not covered by the form above."
        )
        self.extra_flags_edit.textChanged.connect(lambda: self.command_changed.emit())
        layout.addWidget(self.extra_flags_edit)
        group.setLayout(layout)
        self.scroll_layout.addWidget(group)
        self.extra_flags_group = group

    def _add_args(self, args, form_layout, scope):
        for arg in args:
            flag = arg["flag"]
            key = self._field_key(scope, flag)
            widget = self._build_widget(arg, key)
            label_text = arg["name"]
            if arg["required"]:
                label_text = f"<b>{label_text} <span style='color:red;'>*</span></b>"
            label = QLabel(label_text)
            label.setTextFormat(Qt.TextFormat.RichText)

            # Repeatable: add a count spinner next to the widget
            repeat_spin = None
            if arg["repeatable"] and arg["type"] == "boolean":
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(widget, 1)
                repeat_spin = QSpinBox()
                repeat_spin.setRange(1, 10)
                repeat_spin.setValue(1)
                repeat_spin.setPrefix("x")
                repeat_spin.setToolTip("Number of times to repeat this flag")
                repeat_spin.setMaximumWidth(60)
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

    def _build_widget(self, arg, key):
        t = arg["type"]

        if t == "boolean":
            w = QCheckBox()
            if arg["default"] is True:
                w.setChecked(True)
            w.stateChanged.connect(lambda _: self.command_changed.emit())

        elif t == "string":
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

        elif t == "text":
            w = QPlainTextEdit()
            w.setMaximumHeight(80)
            if arg["default"] is not None:
                w.setPlainText(str(arg["default"]))
            w.textChanged.connect(lambda: self.command_changed.emit())

        elif t == "integer":
            w = QSpinBox()
            w.setRange(-999999, 999999)
            if arg["default"] is not None:
                w.setValue(int(arg["default"]))
            else:
                w.setValue(0)
                w.setSpecialValueText(" ")
                w.setRange(0, 999999)
            w.valueChanged.connect(lambda _: self.command_changed.emit())

        elif t == "float":
            w = QDoubleSpinBox()
            w.setRange(-999999.0, 999999.0)
            w.setDecimals(2)
            if arg["default"] is not None:
                w.setValue(float(arg["default"]))
            else:
                w.setValue(0.0)
                w.setSpecialValueText(" ")
                w.setRange(0.0, 999999.0)
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
            w.setMaximumHeight(120)
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
            btn.clicked.connect(lambda checked, l=line: self._browse_file(l))
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
            btn.clicked.connect(lambda checked, l=line: self._browse_directory(l))
            layout.addWidget(line, 1)
            layout.addWidget(btn)
            line.textChanged.connect(lambda _: self.command_changed.emit())
            w._line_edit = line

        else:
            w = QLabel(f"[unsupported type: {t}]")

        if arg["description"]:
            w.setToolTip(arg["description"])

        return w

    # ------------------------------------------------------------------
    # Browse dialogs
    # ------------------------------------------------------------------

    def _browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            line_edit.setText(path)

    def _browse_directory(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            line_edit.setText(path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_input(self, widget, regex, text):
        if text and not regex.search(text):
            widget.setStyleSheet(INVALID_STYLE)
        else:
            widget.setStyleSheet("")

    # ------------------------------------------------------------------
    # Group exclusivity
    # ------------------------------------------------------------------

    def _apply_groups(self):
        for group_key, field_keys in self.groups.items():
            for fk in field_keys:
                field = self.fields[fk]
                widget = field["widget"]
                if isinstance(widget, QCheckBox):
                    widget.stateChanged.connect(
                        lambda state, active=fk, gk=group_key: self._on_group_toggled(gk, active, state)
                    )

    def _on_group_toggled(self, group_key, active_key, state):
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

    def _apply_dependencies(self):
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
                continue
            parent_field = self.fields[parent_key]
            # Set initial disabled state
            field["widget"].setEnabled(self._is_field_active(parent_key))
            field["label"].setEnabled(self._is_field_active(parent_key))
            # Connect parent changes
            self._connect_dependency(parent_key, parent_field, child_field=field)

    def _connect_dependency(self, parent_key, parent_field, child_field):
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

    def _update_dependent(self, parent_key, child_field):
        active = self._is_field_active(parent_key)
        child_field["widget"].setEnabled(active)
        child_field["label"].setEnabled(active)

    def _is_field_active(self, key):
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
            return bool(w.currentData())
        if isinstance(w, QSpinBox) or isinstance(w, QDoubleSpinBox):
            return w.value() != 0
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

    def _on_subcommand_changed(self, index):
        for i, section in enumerate(self.sub_sections):
            section.setVisible(i == index)
        self.command_changed.emit()

    # ------------------------------------------------------------------
    # Value reading (for command assembly in Phase 5)
    # ------------------------------------------------------------------

    def get_current_subcommand(self):
        if self.sub_combo is not None:
            return self.sub_combo.currentData()
        return None

    def get_extra_flags(self):
        if not self.extra_flags_group.isChecked():
            return []
        text = self.extra_flags_edit.toPlainText().strip()
        if not text:
            return []
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()

    def get_field_value(self, key):
        """Return the current widget value for a field key, or None if empty/unchecked."""
        field = self.fields.get(key)
        if not field:
            return None
        w = field["widget"]
        if not w.isEnabled():
            return None
        arg = field["arg"]
        t = arg["type"]

        if t == "boolean":
            if isinstance(w, QCheckBox) and w.isChecked():
                count = 1
                if field["repeat_spin"]:
                    count = field["repeat_spin"].value()
                return count
            return None

        elif t == "string":
            v = w.text().strip()
            return v if v else None

        elif t == "text":
            v = w.toPlainText().strip()
            return v if v else None

        elif t == "integer":
            if arg["default"] is None and w.value() == 0:
                return None
            return w.value()

        elif t == "float":
            if arg["default"] is None and w.value() == 0.0:
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
    # Phase 8 — Preset serialization
    # ------------------------------------------------------------------

    def _raw_field_value(self, key):
        """Like get_field_value but ignores enabled state (reads widget regardless)."""
        field = self.fields.get(key)
        if not field:
            return None
        w = field["widget"]
        arg = field["arg"]
        t = arg["type"]

        if t == "boolean":
            if isinstance(w, QCheckBox) and w.isChecked():
                if field["repeat_spin"]:
                    return field["repeat_spin"].value()
                return True
            return None

        elif t == "string":
            v = w.text().strip()
            return v if v else None

        elif t == "text":
            v = w.toPlainText().strip()
            return v if v else None

        elif t == "integer":
            if arg["default"] is None and w.value() == 0:
                return None
            return w.value()

        elif t == "float":
            if arg["default"] is None and w.value() == 0.0:
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

    def serialize_values(self):
        """Serialize all current field values to a flat dict for preset storage."""
        preset = {}
        preset["_subcommand"] = self.get_current_subcommand()
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

    def apply_values(self, preset):
        """Apply a preset dict to the form, resetting unmentioned fields to defaults."""
        self.blockSignals(True)

        # Subcommand
        sub = preset.get("_subcommand")
        if self.sub_combo is not None and sub:
            idx = self.sub_combo.findData(sub)
            if idx >= 0:
                self.sub_combo.setCurrentIndex(idx)

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

    def reset_to_defaults(self):
        """Reset all fields to their schema defaults."""
        self.blockSignals(True)

        if self.sub_combo is not None:
            self.sub_combo.setCurrentIndex(0)

        self.extra_flags_group.setChecked(False)
        self.extra_flags_edit.clear()

        for key, field in self.fields.items():
            arg = field["arg"]
            default = arg["default"]
            t = arg["type"]
            if t == "boolean":
                self._set_field_value(key, True if default is True else None)
            elif t in ("integer", "float"):
                self._set_field_value(key, default)
            else:
                self._set_field_value(key, default)

        self.blockSignals(False)
        self.command_changed.emit()

    def _set_field_value(self, key, value):
        """Set a widget's value. None resets to empty/default."""
        field = self.fields.get(key)
        if not field:
            return
        w = field["widget"]
        arg = field["arg"]
        t = arg["type"]

        if t == "boolean":
            if isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            if field["repeat_spin"] and isinstance(value, int) and value > 1:
                field["repeat_spin"].setValue(value)
            elif field["repeat_spin"]:
                field["repeat_spin"].setValue(1)

        elif t == "string":
            w.setText(str(value) if value is not None else "")

        elif t == "text":
            w.setPlainText(str(value) if value is not None else "")

        elif t == "integer":
            if value is not None:
                w.setValue(int(value))
            elif arg["default"] is not None:
                w.setValue(int(arg["default"]))
            else:
                w.setValue(0)

        elif t == "float":
            if value is not None:
                w.setValue(float(value))
            elif arg["default"] is not None:
                w.setValue(float(arg["default"]))
            else:
                w.setValue(0.0)

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
    # Phase 5 — Command assembly
    # ------------------------------------------------------------------

    def build_command(self):
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

    def _assemble_args(self, args, scope, cmd, positional):
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

    def validate_required(self):
        """Check required fields. Returns list of (key, name) tuples that are missing."""
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
                        w._line_edit.setStyleSheet(INVALID_STYLE)
                    elif hasattr(w, 'setStyleSheet'):
                        w.setStyleSheet(INVALID_STYLE)
                else:
                    if key not in self.validators:
                        if hasattr(w, '_line_edit'):
                            w._line_edit.setStyleSheet("")
                        elif hasattr(w, 'setStyleSheet'):
                            w.setStyleSheet("")

        return missing


def _format_display(cmd):
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


def _monospace_font():
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def _tools_dir():
    """Return the tools/ directory next to this script, creating it if needed."""
    d = Path(__file__).parent / "tools"
    d.mkdir(exist_ok=True)
    return d


def _presets_dir(tool_name):
    """Return the presets/{tool_name}/ directory, creating it if needed."""
    d = Path(__file__).parent / "presets" / tool_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _binary_in_path(binary):
    """Check if binary is found in PATH."""
    return shutil.which(binary) is not None


# ---------------------------------------------------------------------------
# Phase 7 — Tool Picker
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

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Tool", "Description", "Path"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
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
        layout.addLayout(btn_bar)

        self._entries = []  # list of (path, data_or_none, error_or_none)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)
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
                    self._entries.append((str(json_file), None, "; ".join(errors)))
                else:
                    normalize_tool(data)
                    self._entries.append((str(json_file), data, None))
            except RuntimeError as e:
                self._entries.append((str(json_file), None, str(e)))

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self._entries))

        for row, (path, data, error) in enumerate(self._entries):
            fname = Path(path).name
            if data:
                name_item = QTableWidgetItem(data["tool"])
                desc_item = QTableWidgetItem(data.get("description", ""))
            else:
                name_item = QTableWidgetItem(fname)
                desc_item = QTableWidgetItem(f"[invalid] {error}")
            path_item = QTableWidgetItem(fname)

            if error:
                for item in (name_item, desc_item, path_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    item.setToolTip(error)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, desc_item)
            self.table.setItem(row, 2, path_item)

        has_items = len(self._entries) > 0
        self.table.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self.open_btn.setEnabled(False)

    def _on_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.open_btn.setEnabled(False)
            return
        row = rows[0].row()
        _, data, _ = self._entries[row]
        self.open_btn.setEnabled(data is not None)

    def _on_double_click(self, index):
        row = index.row()
        path, data, _ = self._entries[row]
        if data is not None:
            self.tool_selected.emit(path)

    def _on_open(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        path, data, _ = self._entries[row]
        if data is not None:
            self.tool_selected.emit(path)

    def _on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Tool JSON", str(_tools_dir()), "JSON Files (*.json)"
        )
        if path:
            self.tool_selected.emit(path)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, tool_path=None):
        super().__init__()
        self.data = None
        self.tool_path = None
        self.process = None
        self._killed = False
        self.settings = QSettings("Scaffold", "Scaffold")

        # Restore geometry
        geo = self.settings.value("window/geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(700, 750)

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

    def _build_menu(self):
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

        self.act_delete_preset = self.preset_menu.addAction("Delete Preset...")
        self.act_delete_preset.triggered.connect(self._on_delete_preset)

        self.preset_menu.addSeparator()

        self.act_reset = self.preset_menu.addAction("Reset to Defaults")
        self.act_reset.triggered.connect(self._on_reset_defaults)

    def _build_shortcuts(self):
        # Ctrl+Enter to Run
        run_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_shortcut.activated.connect(self._shortcut_run)
        # Escape to Stop
        stop_shortcut = QShortcut(QKeySequence("Escape"), self)
        stop_shortcut.activated.connect(self._shortcut_stop)

    def _shortcut_run(self):
        if self.data and self.stack.currentIndex() == 1:
            if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
                self._on_run_stop()

    def _shortcut_stop(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._on_run_stop()

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.settings.setValue("window/geometry", self.saveGeometry())
        if self.tool_path:
            self.settings.setValue("session/last_tool", self.tool_path)
        # Kill any running process
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(2000)
        event.accept()

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".json"):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".json"):
                self._load_tool_path(path)
                return

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_picker(self):
        self.picker.scan()
        self.stack.setCurrentIndex(0)
        self.setWindowTitle("Scaffold")
        self.act_reload.setEnabled(False)
        self.act_back.setEnabled(False)
        self.preset_menu.setEnabled(False)
        self.statusBar().showMessage("Ready")

    def _load_tool_path(self, path):
        try:
            data = load_tool(path)
        except RuntimeError as e:
            self._show_load_error(str(e))
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
        self.act_reload.setEnabled(True)
        self.act_back.setEnabled(True)
        self.preset_menu.setEnabled(True)
        self.settings.setValue("session/last_tool", path)
        self.statusBar().showMessage(f"Loaded {data['tool']}")

        # Binary-in-PATH warning
        if not _binary_in_path(data["binary"]):
            self.warning_bar.setText(
                f"Warning: '{data['binary']}' not found in PATH"
            )
            self.warning_bar.setVisible(True)
        else:
            self.warning_bar.setVisible(False)

    def _show_load_error(self, msg):
        QMessageBox.warning(self, "Load Error", msg)

    def _build_form_view(self):
        """Tear down old form widgets and build fresh ones for self.data."""
        # Kill any running process
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(2000)
        self.process = None
        self._killed = False

        # Clear old contents
        layout = self.form_container_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Warning banner (non-blocking, at top)
        self.warning_bar = QLabel("")
        self.warning_bar.setStyleSheet(
            "background-color: #fff3cd; color: #856404; padding: 6px 12px;"
            " border: 1px solid #ffc107; font-weight: bold;"
        )
        self.warning_bar.setVisible(False)
        layout.addWidget(self.warning_bar)

        # Form
        self.form = ToolForm(self.data)
        layout.addWidget(self.form, 1)

        # Preview bar
        preview_bar = QHBoxLayout()
        preview_bar.setContentsMargins(8, 4, 8, 0)

        self.preview = QLineEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(_monospace_font())
        self.preview.setPlaceholderText("Command preview...")
        preview_bar.addWidget(self.preview, 1)

        self.copy_btn = QPushButton("Copy Command")
        self.copy_btn.clicked.connect(self._copy_command)
        preview_bar.addWidget(self.copy_btn)

        preview_widget = QWidget()
        preview_widget.setLayout(preview_bar)
        layout.addWidget(preview_widget)

        # Status label
        self.status = QLabel("")
        self.status.setStyleSheet("padding: 0 8px 4px 8px;")
        layout.addWidget(self.status)

        # Action buttons bar
        action_widget = QWidget()
        action_bar = QHBoxLayout(action_widget)
        action_bar.setContentsMargins(8, 0, 8, 4)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._on_run_stop)
        action_bar.addWidget(self.run_btn)

        self.clear_btn = QPushButton("Clear Output")
        self.clear_btn.clicked.connect(self._clear_output)
        action_bar.addWidget(self.clear_btn)

        action_bar.addStretch()
        layout.addWidget(action_widget)

        # Output panel
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(_monospace_font())
        self.output.setMinimumHeight(150)
        self.output.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        layout.addWidget(self.output)

        # Connect live preview
        self.form.command_changed.connect(self._update_preview)
        self._update_preview()

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Tool JSON", str(_tools_dir()), "JSON Files (*.json)"
        )
        if path:
            self._load_tool_path(path)

    def _on_reload(self):
        if self.tool_path:
            self._load_tool_path(self.tool_path)

    def _on_back(self):
        # Kill any running process before going back
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(2000)
        self.process = None
        self._show_picker()

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _on_save_preset(self):
        if not self.data:
            return
        name, ok = QInputDialog.getText(
            self, "Save Preset", "Preset name:",
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        # Sanitize filename
        safe_name = re.sub(r'[^\w\-. ]', '_', name)
        preset_dir = _presets_dir(self.data["tool"])
        preset_path = preset_dir / f"{safe_name}.json"

        preset = self.form.serialize_values()
        preset_path.write_text(
            json.dumps(preset, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.statusBar().showMessage(f"Preset saved: {safe_name}")

    def _on_load_preset(self):
        if not self.data:
            return
        preset_dir = _presets_dir(self.data["tool"])
        presets = sorted(preset_dir.glob("*.json"))
        if not presets:
            self.statusBar().showMessage("No presets found for this tool")
            return

        names = [p.stem for p in presets]
        name, ok = QInputDialog.getItem(
            self, "Load Preset", "Select preset:", names, 0, False,
        )
        if not ok:
            return

        preset_path = preset_dir / f"{name}.json"
        try:
            preset = json.loads(preset_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            self.statusBar().showMessage(f"Error loading preset: {e}")
            return

        self.form.apply_values(preset)
        self.statusBar().showMessage(f"Preset loaded: {name}")

    def _on_delete_preset(self):
        if not self.data:
            return
        preset_dir = _presets_dir(self.data["tool"])
        presets = sorted(preset_dir.glob("*.json"))
        if not presets:
            self.statusBar().showMessage("No presets to delete")
            return

        names = [p.stem for p in presets]
        name, ok = QInputDialog.getItem(
            self, "Delete Preset", "Select preset to delete:", names, 0, False,
        )
        if not ok:
            return

        preset_path = preset_dir / f"{name}.json"
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            preset_path.unlink(missing_ok=True)
            self.statusBar().showMessage(f"Preset deleted: {name}")

    def _on_reset_defaults(self):
        if self.data:
            self.form.reset_to_defaults()
            self.statusBar().showMessage("Reset to defaults")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _update_preview(self):
        missing = self.form.validate_required()
        cmd, display = self.form.build_command()
        self.preview.setText(display)
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

    def _copy_command(self):
        _, display = self.form.build_command()
        QApplication.clipboard().setText(display)
        self._show_status("Copied to clipboard.", "green")

    def _show_status(self, text, color="red"):
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; padding: 0 8px 4px 8px;")

    # ------------------------------------------------------------------
    # Phase 6 — Process execution
    # ------------------------------------------------------------------

    def _on_run_stop(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._killed = True
            self.process.kill()
            return

        # Validate required fields
        missing = self.form.validate_required()
        if missing:
            return

        cmd, display = self.form.build_command()
        if len(cmd) < 1:
            return

        program = cmd[0]
        arguments = cmd[1:]

        self.process = QProcess(self)
        self.process.setProgram(program)
        self.process.setArguments(arguments)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        # Show what we're running
        self._append_output(f"$ {display}\n", "#569cd6")

        self._killed = False
        self.run_btn.setText("Stop")
        self.statusBar().showMessage("Running...")
        self.process.start()

    def _read_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        self._append_output(text, "#d4d4d4")

    def _read_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        self._append_output(text, "#e8a838")

    def _on_finished(self, exit_code, exit_status):
        if self._killed:
            self._append_output("\n--- Process stopped ---\n", "#e8a838")
            self.statusBar().showMessage("Process stopped")
        elif exit_code == 0:
            self._append_output(f"\n--- Process exited with code {exit_code} ---\n", "#4ec94e")
            self.statusBar().showMessage("Process exited with code 0")
        else:
            self._append_output(f"\n--- Process exited with code {exit_code} ---\n", "#e05555")
            self.statusBar().showMessage(f"Process exited with code {exit_code}")
        self.run_btn.setText("Run")
        self._update_preview()

    def _on_error(self, error):
        if error == QProcess.ProcessError.Crashed and self._killed:
            return  # Handled by _on_finished
        error_messages = {
            QProcess.ProcessError.FailedToStart: (
                f"Error: '{self.data['binary']}' not found. "
                "Is it installed and in your PATH?"
            ),
            QProcess.ProcessError.Crashed: "Process crashed unexpectedly.",
            QProcess.ProcessError.Timedout: "Process timed out.",
            QProcess.ProcessError.WriteError: "Write error communicating with process.",
            QProcess.ProcessError.ReadError: "Read error communicating with process.",
        }
        msg = error_messages.get(error, f"Unknown process error ({error}).")
        self._append_output(f"\n--- {msg} ---\n", "#e05555")
        self.statusBar().showMessage(msg)
        self.run_btn.setText("Run")
        self._update_preview()

    def _append_output(self, text, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text, fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _clear_output(self):
        self.output.clear()


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def print_prompt():
    prompt_path = Path(__file__).parent / "PROMPT.txt"
    if not prompt_path.exists():
        print("Error: PROMPT.txt not found alongside scaffold.py", file=sys.stderr)
        sys.exit(1)
    print(prompt_path.read_text(encoding="utf-8"))


def main():
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
