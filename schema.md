# CLGUI JSON Schema Specification

Version: 1.0

This document defines the JSON contract that LLMs produce and `scaffold.py` consumes.
Each CLI tool is described by a single `.json` file placed in the `tools/` directory.

---

## Top-Level Object

| Field         | Type             | Required | Description                                                                 |
|---------------|------------------|----------|-----------------------------------------------------------------------------|
| `_format`     | string           | yes      | Must be `"scaffold_schema"`. Format marker to distinguish tool schemas from presets and other JSON files. Must be the first key in the file. |
| `tool`        | string           | yes      | Human-readable tool name displayed in the window title.                     |
| `binary`      | string           | yes      | Executable name or absolute path (e.g. `"nmap"`, `"/usr/bin/nmap"`). For script-based tools, use the script's filename (e.g. `"rayhunter.py"`, `"deploy.sh"`, `"build.bat"`) — see note below. |
| `description` | string           | yes      | One-line description shown in the UI header.                                |
| `subcommands` | array or null    | no       | List of subcommand objects. `null` or omitted for tools without subcommands.|
| `arguments`   | array            | yes      | List of argument objects. For tools with subcommands, these are global flags.|
| `elevated`    | string or null   | no       | Elevation mode: `"optional"` (some features need root), `"always"` (tool requires root), or `null` (no elevation needed). |

```json
{
  "_format": "scaffold_schema",
  "tool": "nmap",
  "binary": "nmap",
  "description": "Network exploration tool and security/port scanner.",
  "subcommands": null,
  "arguments": [ ... ]
}
```

### Script-Based Binaries

For script-based tools, set `binary` to the script's filename (e.g. `rayhunter.py`, `deploy.sh`, `build.bat`) — a bare filename, not an absolute path. The user adds the script's directory to Scaffold's custom PATH directories (File > Custom PATH Directories) so the binary resolves at run time. Scripts must be independently executable: Unix scripts need a shebang line and execute bit; Windows `.bat`/`.cmd` files run natively; `.py` files run when Python is installed with `PATHEXT` configured (the default installer does this). `.ps1` PowerShell scripts cannot be executed directly — use `"binary": "powershell"` and pass the script as the first positional argument instead.

---

## Argument Object

| Field        | Type            | Required | Default   | Description                                                                                              |
|--------------|-----------------|----------|-----------|----------------------------------------------------------------------------------------------------------|
| `name`       | string          | yes      | —         | Human-readable label for the widget.                                                                     |
| `flag`       | string          | yes      | —         | Primary flag (e.g. `--top-ports`, `-p`). For positional args, use a descriptive placeholder like `"TARGET"` and set `positional: true`. |
| `short_flag` | string or null  | no       | `null`    | Alternate short form if one exists.                                                                      |
| `type`       | string          | yes      | —         | One of the valid type values listed below.                                                               |
| `description`| string          | no       | `""`      | Tooltip/help text shown on hover.                                                                        |
| `required`   | bool            | no       | `false`   | Whether the tool will not run without this argument.                                                     |
| `default`    | any or null     | no       | `null`    | Pre-populated value. Type should match the argument type.                                                |
| `choices`    | array or null   | no       | `null`    | Valid values for `enum` and `multi_enum` types.                                                          |
| `group`      | string or null  | no       | `null`    | Mutual exclusivity group name. Arguments sharing the same group string are radio-exclusive — only one can be active at a time. |
| `depends_on` | string or null  | no       | `null`    | Flag string of another argument this one depends on. Field is disabled/hidden until the dependency is active. |
| `repeatable` | bool            | no       | `false`   | Whether this flag can appear multiple times (e.g. `-v -v -v`).                                           |
| `separator`  | string          | no       | `"space"` | How flag and value are joined: `"space"`, `"equals"`, or `"none"`.                                       |
| `positional` | bool            | no       | `false`   | If `true`, the value is appended to the command without a flag.                                          |
| `validation` | string or null  | no       | `null`    | Optional regex pattern for string/password fields. GUI highlights invalid input inline.                  |
| `examples`   | array or null   | no       | `null`    | List of suggestion strings for `string` fields. Renders as an editable combobox. Not valid with `enum` or `password` types. |
| `display_group` | string or null | no     | `null`    | Visual grouping label. Arguments sharing the same value are rendered together in a collapsible section.  |
| `min`        | number or null   | no       | `null`    | Minimum value for `integer` and `float` types. Constrains the spinner.                                  |
| `max`        | number or null   | no       | `null`    | Maximum value for `integer` and `float` types. Constrains the spinner.                                  |
| `deprecated` | string or null   | no       | `null`    | Deprecation message. When set, the label is shown with strikethrough and a "(deprecated)" suffix.        |
| `dangerous`  | bool             | no       | `false`   | If `true`, the label is prefixed with a warning symbol. Use for flags with destructive or irreversible effects. |

### Separator Behavior

| Value    | Example              | Assembled as         |
|----------|----------------------|----------------------|
| `space`  | `--top-ports 100`    | `["--top-ports", "100"]` |
| `equals` | `--min-rate=1000`    | `["--min-rate=1000"]`    |
| `none`   | `-T4`                | `["-T4"]`                |

### Repeatable Behavior

When `repeatable` is `true`, the GUI provides a count spinner. A flag with count 3 emits the flag three times: `["-v", "-v", "-v"]`.

### Positional Arguments

Positional arguments (`positional: true`) are appended to the command in the order they appear in the `arguments` array, after all flag-based arguments. The `flag` field serves as a display label only and is not included in the assembled command.

### Mutual Exclusivity Groups

All arguments sharing the same `group` string are presented as radio-exclusive. Activating one deactivates the others in the same group. Each grouped argument still has its own widget for value entry — the group only controls which one is active.

### Dependencies

When `depends_on` names another argument's `flag`, the dependent argument is disabled (greyed out) until the parent argument is active (checked/filled). Circular dependencies are invalid and should be rejected at load time.

---

## Valid Types and Widget Mappings

| Type         | Widget                                    | Notes                                      |
|--------------|-------------------------------------------|--------------------------------------------|
| `boolean`    | `QCheckBox`                               | Emits the flag when checked, nothing when unchecked. |
| `string`     | `QLineEdit`                               | Single-line text input.                    |
| `text`       | `QPlainTextEdit`                          | Multi-line text input.                     |
| `integer`    | `QSpinBox`                                | Whole numbers. Respects `default`.         |
| `float`      | `QDoubleSpinBox`                          | Decimal numbers. Respects `default`.       |
| `enum`       | `QComboBox`                               | Single selection from `choices`.           |
| `multi_enum` | `QListWidget` with checkboxes             | Multiple selections from `choices`.        |
| `password`   | `QLineEdit` (masked) + Show toggle        | Input masked with dots. A "Show" checkbox toggles visibility. |
| `file`       | `QLineEdit` + Browse button               | Opens `QFileDialog.getOpenFileName`.       |
| `directory`  | `QLineEdit` + Browse button               | Opens `QFileDialog.getExistingDirectory`.  |

---

## Subcommand Object

Used for tools like `git`, `docker`, `ansible-galaxy` that have distinct subcommands each with their own arguments.

| Field        | Type   | Required | Description                                      |
|--------------|--------|----------|--------------------------------------------------|
| `name`       | string | yes      | Subcommand name as typed on the command line. Multi-word names like `"role install"` are supported — each word becomes a separate token in the assembled command. |
| `description`| string | no       | One-line description shown in the subcommand dropdown. |
| `arguments`  | array  | yes      | List of argument objects specific to this subcommand. |

When `subcommands` is non-null, the GUI shows a subcommand dropdown at the top. Selecting a subcommand swaps the visible form fields. The top-level `arguments` array holds global flags that apply regardless of which subcommand is selected (e.g. `docker --debug run ...`).

```json
{
  "_format": "scaffold_schema",
  "tool": "docker",
  "binary": "docker",
  "description": "Container runtime and management tool.",
  "subcommands": [
    {
      "name": "run",
      "description": "Run a command in a new container",
      "arguments": [ ... ]
    }
  ],
  "arguments": [
    {
      "name": "Debug Mode",
      "flag": "--debug",
      "short_flag": null,
      "type": "boolean",
      "description": "Enable debug mode",
      "required": false,
      "default": null,
      "choices": null,
      "group": null,
      "depends_on": null,
      "repeatable": false,
      "separator": "none",
      "positional": false,
      "validation": null,
      "examples": null,
      "display_group": null,
      "min": null,
      "max": null,
      "deprecated": null,
      "dangerous": false
    }
  ]
}
```

### Command Assembly with Subcommands

The assembled command follows this order:

```
<binary> [global arguments] <subcommand> [subcommand arguments] [positional arguments]
```

For multi-word subcommand names (e.g. `"role install"`), each word becomes a separate token:

```
ansible-galaxy --verbose role install --force geerlingguy.docker
```

---

## File Organization

```
tools/
  nmap.json
  docker.json
  ffmpeg.json
  ...
```

Each file is a standalone, self-contained description of one tool. No file references other files.

---

## Preset Files

Presets live under `presets/<tool>/<name>.json` and capture a saved form configuration. Scaffold writes a small set of `_`-prefixed meta keys alongside the flag entries.

| Field           | Type           | Required | Description                                                                                              |
|-----------------|----------------|----------|----------------------------------------------------------------------------------------------------------|
| `_format`       | string         | no       | Must be `"scaffold_preset"` when present. Format marker used to distinguish presets from tool schemas and cascades. |
| `_tool`         | string         | no       | The tool name this preset was made for (copied from the schema's `tool` field). When present and non-matching, Scaffold warns before loading or importing so flags from a different tool don't get applied silently. Absent in legacy presets — treated as unknown and silently allowed. |
| `_schema_hash`  | string         | no       | Hash of the schema at save time. When present and non-matching, Scaffold warns that some fields may not have loaded. |
| `_subcommand`   | string or null | no       | Subcommand name this preset targets, or `null` for global-only presets.                                  |
| `_description`  | string         | no       | Short human-readable summary shown in the preset picker.                                                 |
| `_elevated`     | bool           | no       | Whether the preset was saved with elevation enabled.                                                     |
| `_extra_flags`  | string         | no       | Raw extra-flags text for flags not covered by the schema.                                                |

All other keys are flag entries. Global flags use the bare flag name as the key (e.g. `"--verbose"`). Subcommand-scoped flags use `"subcommand:flag"` format (e.g. `"clone:--depth"`).
