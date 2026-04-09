# Scaffold — Your CLI Tools, but with Buttons

**Stop memorizing flags. Start clicking them.**

Scaffold turns command-line tools into native desktop GUIs. Any tool - public or internal, simple or complex. If it accepts flags and arguments, Scaffold can build a form for it. Fill in the fields, hit Run, done. It is secure by design and is written in 100% Python 3. Scaffold has a strict global NO SHELL policy with a dedicated security test suite (158 assertions) verifying this. (The security test suite is also available for the user to run at any time!) Scaffold strictly uses PySide6's QProcess to pass flags and arguments as literal strings directly to the target binary, making it immune to shell injection, and leaves no shell history!

This works with *any CLI tool* — not just well-known programs like nmap or ffmpeg. If your team has a custom deployment CLI, a database migration tool, or a build script with 30 flags that nobody can remember, write a schema and your team gets a GUI. Massive tools with hundreds of flags (like curl's 271-argument schema) work too.

Presets are what really make this powerful though. Save your perfectly-tuned nmap recon scan, your go-to ffmpeg encoding pipeline, or your favorite hashcat attack config as a named preset with a description. No more digging through shell history or old notes for that command you ran three weeks ago. Save it once, reload it anytime. Share preset files with your team. Build a personal library of ready-to-run commands for every tool you use. Don't want to build presets by hand? Use the built-in LLM preset generation — describe what you want in plain English, and drop the result into your presets folder.

Need to chain multiple tools together? The cascade system lets you line up sequential tool runs with per-step delays, loop mode, and runtime variables — all through the same secure QProcess pipeline. Save your chains as named cascade files and reuse them.

Under the hood, Scaffold generates interactive forms from simple JSON schema files — dropdowns, checkboxes, file pickers, a live syntax-colored command preview — all from a single schema that describes your tool's arguments. No custom UI code needed. Hand a tool's man page or official documentation to an LLM with the bundled `SCHEMA_PROMPT.txt` and get a working schema back. Collapsible sections, field search, and display groups keep large forms manageable. Simple. Powerful. Secure by design.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)
![Single File](https://img.shields.io/badge/single%20file-7%2C777%20lines-orange)

<p>
  <img src="nmap%20example.png" alt="Scaffold — nmap example" width="48%">
  <img src="hashcat%20example.png" alt="Scaffold — hashcat example" width="48%">
</p>

> **Disclaimer:** Most of the code was written by [Claude Code](https://claude.ai) (Opus 4.6), but the project was human-directed — designed, planned, tested, and iterated over many sessions. Not vibe-coded — every line of code and every command was manually reviewed and approved, with the author making direct edits where needed. This was a collaboration, not delegation. The author has 15 years of IT experience and multiple professional certifications. See [About This Project](#about-this-project) for the full story. The project has an automated test suite (1,889 assertions across 6 suites, including a dedicated security suite), but it has not been extensively tested in production environments. Scaffold should work with any CLI tool that accepts flags and arguments, but tools with very large man pages or hundreds of flags may exceed the LLM's context window during schema generation, resulting in incomplete or inaccurate output. On the UI side, complex tools with deeply nested subcommand trees (like OpenClaw with 70+ subcommands and 200+ arguments) can produce forms that are harder to navigate. Scaffold still gives you a command overview and prevents syntax errors, but for very large tools it may be more of a reference than a streamlined workflow. **Always review the generated commands before running them**, especially with tools that can modify files or systems. If you hit issues with a specific version, try rolling back. Use at your own risk. Contributions and bug reports welcome!
>
> **Tip:** If a specific flag or argument isn't behaving the way you expect in the form, you can type it directly into the Additional Flags box at the bottom of any tool form. It passes your input straight through to the command line and is handy for edge cases or flags the schema doesn't model perfectly.

---

## Getting Started

### Prerequisites

- **Windows, macOS, or Linux** — Scaffold has been tested on Windows. It should work on macOS and Linux as well (PySide6 is cross-platform), but these have not been extensively tested. If you run into platform-specific issues, please open an issue!
- **Python 3.10+** — make sure Python is installed and up to date (`python --version`)
- **pip** — should come with Python; update it with `pip install --upgrade pip`
- **The CLI tool you want to use** — Scaffold builds a GUI for tools already installed on your system. For example, if you want to use the nmap schema, you need nmap installed and available in your PATH.
- **A JSON schema for your tool** — Scaffold comes with bundled schemas for 18 tools (nmap, curl, git, ansible, docker, aircrack-ng, and more) in the `tools/` folder. To add your own, see [Creating Tool Schemas](#creating-tool-schemas) below.

### Install and Run

```bash
# 1. Clone the repo
git clone https://github.com/Zencache/scaffold.git
cd scaffold

# 2. Install the only dependency
pip install PySide6

# 3. Launch Scaffold
python scaffold.py
```

The tool picker will open showing all `.json` schemas in the `tools/` folder (including subfolders). Tools in subfolders appear at the top in collapsible folder groups — click a folder header to expand or collapse it. A green checkmark means the tool is installed and ready to use; a red X means it's not found in your PATH. Double-click any tool to open its form, fill in the fields, and hit **Run**.

> **Tip:** Toggle dark mode with **Ctrl+D** or from the **View > Theme** menu.

> **Linux users:** On some distros (e.g., Ubuntu 24.04+), `pip install PySide6` may fail because the system Python is externally managed. You can work around this with `pip install pyside6 --break-system-packages` — but **be careful**, this installs packages globally and can conflict with system packages. A safer alternative is to use a virtual environment (`python3 -m venv .venv && source .venv/bin/activate && pip install PySide6`).
>
> You may also need to install `libxcb-cursor0` for the Qt platform plugin to load:
> ```bash
> sudo apt install libxcb-cursor0
> ```
> Without it, PySide6 will crash on launch with `Could not load the Qt platform plugin "xcb"`.

---

## Features

- **Works with any CLI tool** — JSON schema in, native GUI out
- **Presets** — save, name, reload, and share form configurations
- **Immune to shell injection** — QProcess with list args, no shell
- **Typed input constraints** — widgets validate values at entry
- **LLM-powered schema generation** — paste SCHEMA_PROMPT.txt + docs, get a schema
- **Syntax-colored command preview** — live preview with color-coded tokens
- **Process execution** — run, stop, search output, copy or save results
- **10 widget types** — checkbox, text, spinbox, dropdown, file picker, and more
- **Subcommand support** — multi-level commands like `git clone` or `ansible-galaxy role install`
- **Command history** — browse and restore past runs per tool (Ctrl+H)
- **Auto-save & crash recovery** — form state saved automatically, restored on next launch
- **Collapsible display groups** — organize large forms into sections
- **Field search** — find any field by name or flag (Ctrl+F)
- **Process timeout** — optional auto-kill after N seconds, per tool
- **Mutual exclusivity & dependencies** — radio groups and conditional fields
- **Validation** — regex patterns and required field checking
- **Drag and drop** — drop a .json schema to load it
- **Portable mode** — run from USB with local settings
- **Cascade preset chaining** — chain multiple tool runs with per-step delays, loop mode, and saveable named cascade files. Same secure QProcess pipeline as regular execution
- **LLM-powered preset generation** — generate presets from natural language with `--preset-prompt` and `PRESET_PROMPT.txt`
- **Copy As shell formats** — Bash, PowerShell, or CMD via right-click
- **Single Python file** — one file, one dependency (PySide6), fully offline

See [Detailed Features](#detailed-features) below for full descriptions.

## Quick Start

### 1. Install

```bash
pip install PySide6
```

### 2. Run

```bash
python scaffold.py
```

The tool picker appears showing all `.json` schemas in the `tools/` folder. Double-click one to open its form.

### 3. Use

- Fill in the form fields
- Watch the live command preview update
- Click **Run** to execute (or **Ctrl+Enter**, or just **Enter** when not typing in a field)
- Click **Stop** to kill a running process (or **Escape**)
- Click **Copy Command** to copy to clipboard (or right-click the preview for Bash/PowerShell/CMD formats)
- Click **Copy Output** or **Save Output...** to capture command output

> **Important:** Always review the command preview before clicking Run. Scaffold assembles commands from your input and executes them directly on your system.

## Creating Tool Schemas

Each CLI tool is described by a JSON file placed in the `tools/` folder. Scaffold scans this folder on startup and displays all valid schemas in the tool picker.

### The Easy Way: Use an LLM

The included `SCHEMA_PROMPT.txt` file contains a detailed prompt that teaches any LLM (ChatGPT, Claude, Gemini, etc.) to generate schemas for you:

1. Copy the contents of `SCHEMA_PROMPT.txt`
2. Paste it into your LLM of choice
3. Then say: *"Generate a Scaffold schema for [tool name]"* and paste the tool's man page, official documentation, or other detailed reference. `--help` output alone is usually not enough — it provides flag names and brief summaries, but lacks the detail an LLM needs to infer correct types, write meaningful descriptions, populate example values, or identify dependencies between flags. The richer the input documentation, the better the schema. Use `--help` afterward to verify the generated schema covers all available flags
4. Save the JSON response as `tools/toolname.json`
5. Restart Scaffold (or use File > Reload) — the new tool appears in the picker

> **Note:** Generating schemas for complex tools (like curl or ffmpeg) with many flags requires a large context window and works best with frontier-level LLMs (Claude Opus, GPT-4, Gemini Pro, etc.). Smaller or older models may truncate output, miss fields, or produce invalid JSON. Always validate the result with `python scaffold.py --validate tools/toolname.json`.

> **Note:** LLM-generated schemas may contain errors. Always validate with `python scaffold.py --validate tools/toolname.json` and test the generated commands before relying on them.

> **Tip:** If validation fails, paste the error messages back into the LLM conversation and ask it to fix them. Most models can correct their own mistakes in one round when shown the specific validation errors. For example: *"The validator returned these errors: [paste errors]. Fix the JSON and return the corrected version."*

### Start from the Example Schema

The bundled `tools/example.json` is a complete reference schema that demonstrates every Scaffold feature: all 10 widget types, subcommands, display groups, dependencies, mutual exclusivity, min/max constraints, deprecated and dangerous flags, editable suggestions, validation patterns, and more. Copy it, rename it, and modify it for your tool — it's the fastest way to get started without reading the full spec.

### The Manual Way

Create a JSON file following this structure:

```json
{
  "_format": "scaffold_schema",
  "tool": "mytool",
  "binary": "mytool",
  "description": "What this tool does.",
  "subcommands": null,
  "arguments": [
    {
      "name": "Verbose",
      "flag": "-v",
      "type": "boolean",
      "description": "Enable verbose output",
      "required": false,
      "default": null,
      "choices": null,
      "group": null,
      "depends_on": null,
      "repeatable": false,
      "separator": "none",
      "positional": false,
      "validation": null
    },
    {
      "name": "Output File",
      "flag": "-o",
      "type": "file",
      "description": "Write output to file",
      "required": false,
      "default": null,
      "choices": null,
      "group": null,
      "depends_on": null,
      "repeatable": false,
      "separator": "space",
      "positional": false,
      "validation": null
    },
    {
      "name": "Target",
      "flag": "TARGET",
      "type": "string",
      "description": "The target to operate on",
      "required": true,
      "default": null,
      "choices": null,
      "group": null,
      "depends_on": null,
      "repeatable": false,
      "separator": "space",
      "positional": true,
      "validation": null
    }
  ]
}
```

You can validate a schema without launching the GUI:

```bash
python scaffold.py --validate tools/mytool.json
```

## Schema Reference

### Top-Level Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `_format` | string | Yes | Must be `"scaffold_schema"`. Format marker — must be the first key in the file |
| `tool` | string | Yes | Display name shown in the picker and form header |
| `binary` | string | Yes | The actual executable name (must be in PATH to run) |
| `description` | string | Yes | Short description of the tool |
| `arguments` | array | Yes | List of global argument objects |
| `subcommands` | array or null | No | List of subcommand objects (for tools like `git`) |
| `elevated` | string or null | No | Elevation mode: `"optional"`, `"always"`, or `null` (no elevation needed) |

### Argument Object

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | *required* | Human-readable label shown in the form |
| `flag` | string | *required* | The CLI flag (e.g., `-v`, `--output`, `TARGET`) |
| `type` | string | *required* | Widget type (see below) |
| `short_flag` | string | null | Alternative short flag (informational) |
| `description` | string | "" | Tooltip and placeholder text |
| `required` | bool | false | If true, field is bold with red asterisk; Run is disabled until filled |
| `default` | any | null | Initial value for the widget |
| `choices` | array | null | Required for `enum` and `multi_enum` types |
| `group` | string | null | Mutual exclusivity group name (at most one member can be active) |
| `depends_on` | string | null | Flag of parent field — this field is disabled until parent is active |
| `repeatable` | bool | false | For booleans: adds a count spinner (e.g., `-v -v -v`) |
| `separator` | string | "space" | How flag and value join: `"space"` (`-o file`), `"equals"` (`--out=file`), `"none"` (`-T4`) |
| `positional` | bool | false | If true, only the value appears (no flag), placed after all flags |
| `validation` | string | null | Regex pattern — field gets red border if input doesn't match |
| `examples` | array | null | Common values shown as editable suggestions for `string` fields (user can also type custom values) |
| `display_group` | string | null | Visual grouping label — arguments sharing the same value are rendered in a collapsible section |
| `min` | number | null | Minimum value for `integer`/`float` types — constrains the spinner range |
| `max` | number | null | Maximum value for `integer`/`float` types — constrains the spinner range |
| `deprecated` | string | null | Deprecation message — field gets strikethrough label + warning tooltip. Still functional |
| `dangerous` | bool | false | If true, field label gets a red caution symbol + warning tooltip |

### Widget Types

| Type | Widget | Value | Example |
|------|--------|-------|---------|
| `boolean` | Checkbox | checked/unchecked | `-v`, `--force` |
| `string` | Text input (or editable dropdown if `examples` is set) | free text | `-p 22,80`, `--name foo` |
| `text` | Multi-line text area | free text with newlines | `--script-args` |
| `integer` | Spin box | whole number | `--count 5`, `--depth 1` |
| `float` | Double spin box | decimal number | `--rate 1000.0` |
| `enum` | Dropdown | single choice | `-T 4` (from choices 0-5) |
| `multi_enum` | Checkable list | multiple choices | `--script auth,vuln` |
| `file` | Text input + Browse button | file path | `-o /tmp/out.txt` |
| `directory` | Text input + Browse button | directory path | `--datadir /opt/data` |
| `password` | Masked text input + Show toggle | sensitive string | `--api-key`, `--token` |

### Separator Modes

Controls how the flag and value are joined in the final command:

| Mode | Output | Use When |
|------|--------|----------|
| `"space"` | `-p 22,80` | Most flags (default) |
| `"equals"` | `--min-rate=1000.0` | Flags that use `=` syntax |
| `"none"` | `-T4` | Flag and value are concatenated directly |

### Subcommands

For tools like `git` that have subcommands, each subcommand has its own arguments:

```json
{
  "tool": "git",
  "binary": "git",
  "description": "Distributed version control system.",
  "arguments": [
    { "name": "Verbose", "flag": "--verbose", "type": "boolean", ... }
  ],
  "subcommands": [
    {
      "name": "clone",
      "description": "Clone a repository",
      "arguments": [
        { "name": "Depth", "flag": "--depth", "type": "integer", ... },
        { "name": "Repository", "flag": "REPOSITORY", "type": "string", "positional": true, "required": true, ... }
      ]
    },
    {
      "name": "commit",
      "description": "Record changes",
      "arguments": [
        { "name": "Message", "flag": "--message", "type": "string", ... }
      ]
    }
  ]
}
```

The command is assembled as: `binary [global flags] [subcommand] [subcommand flags] [positionals] [extra flags]`

For tools with multi-level subcommands like `ansible-galaxy` or `docker compose`, use the full chain as the name. Scaffold splits it into separate tokens: `ansible-galaxy role install --force` assembles correctly.

```json
{
  "subcommands": [
    { "name": "role install", "description": "Install a role", "arguments": [...] },
    { "name": "role remove", "description": "Remove a role", "arguments": [...] },
    { "name": "collection install", "description": "Install a collection", "arguments": [...] }
  ]
}
```

### Mutual Exclusivity Groups

Give multiple boolean arguments the same `group` name — only one can be checked at a time:

```json
{ "name": "TCP SYN Scan", "flag": "-sS", "type": "boolean", "group": "scan_type", ... },
{ "name": "TCP Connect",  "flag": "-sT", "type": "boolean", "group": "scan_type", ... },
{ "name": "UDP Scan",     "flag": "-sU", "type": "boolean", "group": "scan_type", ... }
```

### Dependencies

Use `depends_on` to link a child field to a parent. The child is grayed out until the parent has a value:

```json
{ "name": "Service Detection", "flag": "-sV", "type": "boolean", ... },
{ "name": "Version Intensity", "flag": "--version-intensity", "type": "integer", "depends_on": "-sV", ... }
```

### Examples (Editable Suggestions)

Use `examples` on `string` type fields to provide common value suggestions without restricting input. Unlike `enum` (which locks the user to a fixed set), `examples` renders an editable dropdown — the user can pick a suggestion OR type any custom value:

```json
{
  "name": "Video Codec",
  "flag": "-c:v",
  "type": "string",
  "description": "Video codec to use for encoding",
  "examples": ["copy", "libx264", "libx265", "libvpx-vp9", "libaom-av1", "hevc_nvenc"]
}
```

This is ideal for flags that accept well-known values but also allow others not listed in the docs. If the set of values is strictly closed (no other values are valid), use `enum` with `choices` instead.

### Display Groups (Collapsible Sections)

Use `display_group` to visually group related arguments into collapsible sections. Arguments sharing the same `display_group` value are rendered together inside a titled, clickable group box. Click the group header to collapse or expand the section.

```json
{ "name": "Host",     "flag": "--host",     "type": "string",  "display_group": "Network", ... },
{ "name": "Port",     "flag": "--port",     "type": "integer", "display_group": "Network", ... },
{ "name": "Protocol", "flag": "--protocol", "type": "enum",    "display_group": "Network", ... },
{ "name": "Verbose",  "flag": "-v",         "type": "boolean", "display_group": null, ... }
```

This renders Host, Port, and Protocol inside a collapsible "Network" section, while Verbose remains ungrouped. This is purely visual — it does not affect command assembly, presets, or mutual exclusivity (which uses `group`).

### Min/Max Constraints

Use `min` and `max` on `integer` or `float` arguments to constrain the spinner range in the GUI:

```json
{ "name": "Timing", "flag": "-T", "type": "integer", "min": 0, "max": 5, "separator": "none", ... }
{ "name": "Quality", "flag": "--quality", "type": "integer", "min": 1, "max": 100, "default": 85, ... }
```

When both are set, `min` must be `<=` `max`. When null (default), the spinner uses the full default range. Using `min`/`max` on non-numeric types produces a validation error.

### Deprecated & Dangerous Flags

Mark flags with visual indicators without disabling them:

```json
{ "name": "Old Output", "flag": "--old-output", "type": "string", "deprecated": "Use --output instead", ... },
{ "name": "Force Delete", "flag": "--force", "type": "boolean", "dangerous": true, ... }
```

- **`deprecated`** (string): Label gets strikethrough + amber "(deprecated)" suffix. The deprecation message appears in the tooltip. The field remains fully functional.
- **`dangerous`** (bool): Label gets a red caution symbol prefix. A warning appears in the tooltip. No behavioral change.

### Password Fields

Use `password` type for flags that accept sensitive values like passwords, API keys, or tokens:

```json
{ "name": "API Key", "flag": "--api-key", "type": "password", "description": "Your API key", ... }
```

The input is masked by default with a "Show" toggle to reveal the value. Works identically to `string` for command assembly and presets. The `examples` field should not be used with password type.

## Security

### No shell intermediary

Scaffold never uses `shell=True`. All command execution goes through `QProcess` with arguments passed as a Python list. There is no shell parsing, no string interpolation, and no command string assembly. Shell metacharacters in schemas or user input — pipes, semicolons, backticks, `$(...)`, glob patterns — are treated as literal strings because no shell ever interprets them. This eliminates shell injection by design, not by sanitization. The command preview shows exactly what will execute, token by token.

The `binary` field in every schema is validated at load time: shell metacharacters are rejected, relative paths with separators are rejected, and only bare executable names or absolute paths are accepted.

### Typed input constraints

Every argument passes through a typed widget that constrains values at the point of entry. A port number comes from a `QSpinBox` with defined bounds, not free text. Enum values come from a `QComboBox` with a fixed choice list. Boolean flags are checkboxes. File and directory arguments use native picker dialogs. The attack surface for malformed input is minimal because the GUI prevents it structurally — values are validated by widget type before they ever reach the command builder.

The **Additional Flags** field is the only free-text path to the command line. It uses `shlex.split()` for tokenization with visual feedback on malformed input (unclosed quotes, etc.), and the resulting tokens are passed as discrete list items to `QProcess` — never concatenated into a shell string.

### No dynamic code execution

The codebase contains no `eval()`, no `exec()`, and no dynamic imports. Schema files are parsed as JSON data and treated as static declarations. Loading a schema reads structured data; it never executes code.

### No runtime network access

Scaffold makes zero network calls. No telemetry, no update checks, no analytics, no external API dependencies. The application runs entirely offline.

### Verify it yourself

Scaffold ships with a dedicated security test suite (`test_security.py`) that any user can run at any time: static analysis for `shell=True`/`eval`/`exec`/`os.system`/`subprocess.*` patterns, shell metacharacter passthrough verification across every widget type, binary validation hardening, preset and extra-flags injection resistance, path traversal checks, recovery file safety, and direct QProcess contract verification. Run `python test_security.py` to confirm the no-shell claim and the rest of the hardening holds on your machine, with your Python, on your OS. Security here is a structural property of the code, not a promise — and it is testable.

## Detailed Features

### Works with any CLI tool

If a tool accepts flags and arguments, Scaffold can build a GUI for it. From simple utilities like `ping` to tools with hundreds of flags and nested subcommands like `curl` (271 arguments) or `ffmpeg` (123 arguments). Write a JSON schema — or have an LLM generate one from the tool's documentation — and Scaffold renders a native desktop form. No custom UI code needed.

### Presets

Save, name, and reload entire form configurations. Build a library of ready-to-run commands per tool. Share preset files with your team. Never reconstruct a complex command from memory again.

- **Save**: Presets > Save Preset (Ctrl+S) — enter a name and optional description
- **Load**: Presets > Preset List (Ctrl+L) — table-based picker with name, description, and last modified date
- **Edit**: Presets > Edit Preset — manage presets: edit descriptions, delete presets, toggle favorites
- **Reset**: Click "Reset to Defaults" in the command preview bar — clears everything back to schema defaults

The preset picker supports **favorites** — click the star column to pin frequently-used presets to the top. Presets are stored as JSON in `presets/{tool_name}/` and are portable. Schema changes are handled gracefully: removed fields are silently skipped, new fields get defaults.

### Immune to shell injection

Scaffold never invokes a shell. All execution uses `QProcess` with list-based arguments, so shell metacharacters in schemas or user input are treated as literal strings — there is nothing to inject into. See the [Security](#security) section for full details.

### Typed input constraints

Every argument passes through a typed widget (checkbox, spinbox, dropdown, file picker) that constrains values at entry, not after the fact. The attack surface for malformed input is minimal because the GUI prevents it structurally.

### LLM-powered schema generation

Paste the included `SCHEMA_PROMPT.txt` into any LLM along with a tool's man page or official documentation, and get a working schema back. Use `--help` output to verify flag coverage. Works with any model that can output JSON. Complex tools with many flags work best with frontier-level models (Claude Opus, GPT-4, Gemini Pro).

### Syntax-colored command preview

Watch the exact command build in real time as you change fields. Tokens are color-coded by type (binary, flags, values) in both light and dark modes. Right-click the preview to copy formatted for Bash, PowerShell, or Windows CMD with shell-appropriate quoting.

### Process execution

Run commands directly from the GUI with colored output (stdout in one color, stderr in another), exit codes, and timestamps. The output panel is searchable (Ctrl+Shift+F). Copy or save output to file. ANSI escape codes are automatically stripped. Process stop uses SIGTERM first with SIGKILL fallback for clean shutdown. Optional auto-kill timeout per tool.

### 10 widget types

Each CLI argument gets the right input control: checkboxes for booleans, text fields for strings, spin boxes for integers and floats, dropdowns for enums, checkable lists for multi-enums, file and directory browsers, password fields with show/hide toggle, and multi-line text areas.

### Subcommand support

Tools like `git` with multiple subcommands work seamlessly. Multi-word subcommand chains like `ansible-galaxy role install` or `docker compose up` are supported — each word becomes a separate token in the assembled command. Selecting a subcommand swaps the visible form fields while global flags remain.

### Command history

Every executed command is automatically recorded. Browse recent runs per tool via View > Command History (Ctrl+H), see exit codes and timestamps, and restore any past form state with one click.

### Auto-save and crash recovery

Form state is automatically saved 2 seconds after each change. If the app crashes, the next launch offers to restore your work. Unchanged forms are not saved.

### Cascade preset chaining

Chain multiple tool runs into sequential workflows from the cascade sidebar (`Ctrl+G`). Each cascade holds up to 20 numbered slots, each assignable to any loaded tool and an optional preset. Configure per-step delays (0–3600 seconds) to pace the chain, enable loop mode to repeat the full sequence indefinitely, or use stop-on-error mode to halt on the first non-zero exit code. Cascade variables let you define named parameters (with type hints: `string`, `file`, `directory`, `integer`, `float`) that are prompted at run time and injected into form fields across steps — useful for target IPs, output directories, or any value that changes between runs.

Cascade files can be saved, loaded, imported, exported, and deleted from the sidebar. State (slots, loop mode, stop-on-error, variables, and cascade name) persists across sessions. Cascades run through the same `QProcess` list-based execution pipeline as single-tool runs — no shell, no shortcuts, same security guarantees as the rest of the app. Two example cascade files are bundled: a basic nmap reconnaissance chain (`recon_basic.json`) and a ping-then-nmap workflow demonstrating cascade variables (`ping_then_nmap.json`).

### LLM-powered preset generation

Generate presets from natural language using `--preset-prompt` and `PRESET_PROMPT.txt`, mirroring the existing schema-generation workflow. Run `python scaffold.py --preset-prompt` to print the generation prompt, paste it alongside the target tool's schema into any frontier LLM (Claude, GPT-4, Gemini, etc.), describe the preset you want in plain English, and drop the returned JSON file into `presets/<tool>/`. Reload the tool to see it in the preset picker. This is especially useful for tools with many flags where manually configuring a preset would be tedious — describe the intent and let the LLM figure out the right flag combination.

### Collapsible display groups

Visually group related arguments into collapsible sections to tame tools with hundreds of flags. Arguments sharing the same `display_group` value are rendered together inside a titled, clickable group box.

### Field search

Ctrl+F to instantly find any field by name, flag, or description in large forms. The search bar highlights matching fields and scrolls them into view.

### Mutual exclusivity and dependencies

Radio-button groups for conflicting flags (only one can be active at a time). Dependency fields activate only when their parent field is set.

### Validation

Regex patterns on string fields give immediate visual feedback (red border) for invalid input. Required fields are bold with a red asterisk, and Run is disabled until all required fields are filled.

### Additional features

- **Deprecated and dangerous indicators** — schema flags can be marked `deprecated` (strikethrough + warning) or `dangerous` (red caution symbol) for visual heads-up without disabling them
- **Min/max constraints** — optional `min` and `max` on integer/float arguments constrain the spinner range in the GUI
- **Drag and drop** — drop a `.json` schema file onto the window to load it
- **Help menu** — About dialog with version info and GitHub link, cascade guide, keyboard shortcuts reference
- **Session persistence** — remembers window size, position, theme, and last opened tool
- **Format markers** — `_format` metadata key prevents accidentally loading presets as tool schemas or vice versa, with clear error messages
- **Bundled example schema** — `tools/example.json` demonstrates every feature in one file — copy and modify it to build schemas for your own tools
- **Portable mode** — place `portable.txt` next to `scaffold.py` to store all settings in a local INI file instead of the system registry. Run from a USB drive with fully isolated configuration
- **Bundled tool schemas (testing)** — 18 schemas for aircrack-ng, ansible (4 tools), curl, docker (3 tools), git, gobuster, hashcat, nikto, nmap, openclaw, ffmpeg, and ping. Some are mostly untested — contributions and bug reports welcome

## Presets

Presets save and restore the complete state of a form:

- **Save**: Presets > Save Preset (Ctrl+S) — enter a name and optional description
- **Load**: Presets > Preset List (Ctrl+L) — opens a table-based picker with preset name, description, and last modified date
- **Edit**: Presets > Edit Preset — manage presets: edit descriptions, delete presets, and toggle favorites from a single dialog
- **Reset**: Click "Reset to Defaults" in the command preview bar — clears everything back to schema defaults

The preset picker supports **favorites** — click the star column to pin frequently-used presets to the top of the list. Favorites are stored locally (not in preset files) and persist across sessions. You can also **edit a preset's description** after saving it via the "Edit Description..." button in the picker.

Presets are stored as JSON files in `presets/{tool_name}/` next to `scaffold.py`. They're portable — you can share preset files with others.

Presets handle schema changes gracefully:
- Fields removed from the schema are silently skipped
- New fields added to the schema get their default values
- Renamed fields: old name is skipped, new name gets its default

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Enter** | Run the command (when not typing in a field) |
| **Shift+Enter** | Run cascade chain (when not typing in a field) |
| **Ctrl+Enter** | Run the command |
| **Escape** | Stop a running process |
| **Ctrl+S** | Save preset |
| **Ctrl+L** | Preset list |
| **Ctrl+H** | Command history |
| **Ctrl+O** | Load tool from file |
| **Ctrl+R** | Reload current tool |
| **Ctrl+F** | Focus field search bar (type to find fields by name or flag) |
| **Ctrl+Shift+F** | Search within output panel (highlights matches, Enter/Shift+Enter to navigate) |
| **Ctrl+D** | Toggle dark mode |
| **Ctrl+G** | Toggle cascade panel |
| **Ctrl+B** | Tool list |
| **Ctrl+Q** | Quit |

## Command-Line Usage

```bash
# Launch the GUI (tool picker)
python scaffold.py

# Launch directly into a specific tool
python scaffold.py tools/nmap.json

# Validate a schema without launching the GUI
python scaffold.py --validate tools/mytool.json

# Print the LLM prompt for schema generation
python scaffold.py --prompt

# Print the LLM prompt for preset generation
python scaffold.py --preset-prompt

# Show version and exit
python scaffold.py --version
```

## Portable Mode

Scaffold can run fully self-contained from a USB drive or synced folder. To enable portable mode, create an empty file named `portable.txt` in the same directory as `scaffold.py`:

```bash
touch portable.txt
```

When portable mode is active, all settings (window size, theme, timeouts, favorites) are stored in `scaffold.ini` next to `scaffold.py` instead of the system registry (Windows) or config directory (Linux/macOS). Presets and tool schemas are already portable — they live in `presets/` and `tools/` next to the script.

To disable portable mode, delete both `portable.txt` and `scaffold.ini`.

## Included Example Schemas

| File | Tool | Highlights |
|------|------|------------|
| `tools/aircrack-ng.json` | aircrack-ng | 42 arguments, 6 display groups, 4 mutual exclusivity groups, dependencies, WEP/WPA attack modes |
| `tools/ansible/ansible.json` | ansible | Ad-hoc command runner, inventory/module/connection options |
| `tools/ansible/ansible-galaxy.json` | ansible-galaxy | Multi-word subcommands (`role install`, `collection init`), scoped arguments |
| `tools/ansible/ansible-playbook.json` | ansible-playbook | Playbook runner, inventory/vault/connection/privilege escalation options |
| `tools/ansible/ansible-vault.json` | ansible-vault | Vault subcommands (encrypt, decrypt, edit, view, rekey) |
| `tools/curl.json` | curl | HTTP client, string/boolean/file/integer fields |
| `tools/example.json` | example | **Reference schema** — every Scaffold feature in one file. Copy and modify for your own tools |
| `tools/ffmpeg.json` | FFmpeg | 123 arguments, string+examples for codecs/formats, equals separators |
| `tools/git.json` | git | 4 subcommands, scoped arguments, equals separators |
| `tools/gobuster.json` | gobuster | 7 subcommands with scoped flags, repeatable headers, file types |
| `tools/hashcat.json` | hashcat | Positional arg ordering, examples vs enum (-m vs -a), equals separators |
| `tools/nikto.json` | nikto | String+examples for code-concatenation flags, enum vs examples distinction |
| `tools/nmap.json` | nmap | 7 widget types, groups, dependencies, validation, repeatable flags |
| `tools/openclaw.json` | openclaw | AI agent platform, 10+ subcommands, gateway with auth/tailscale options |
| `tools/ping.json` | ping | Simple tool, mutual exclusivity group (IPv4/IPv6) |
| `tools/docker_test/docker.json` | docker | Container management, subcommands (run, build, exec, etc.) — mostly untested |
| `tools/docker_test/docker-buildx.json` | docker buildx | Extended build capabilities with BuildKit — mostly untested |
| `tools/docker_test/docker-compose.json` | docker compose | Multi-container orchestration, service management — mostly untested |

## Requirements

- **Python 3.10+**
- **PySide6** (`pip install PySide6`)
- That's it. No other dependencies.

## About This Project

Most of the code in Scaffold was written by [Claude Code](https://claude.ai) (Opus 4.6) with some minor edits from the author — but this was a collaboration, not delegation. The project was designed, directed, tested, and iterated by a human who manually audited every line of code and every command, and made direct edits where needed. This wasn't a one-shot generation.

Scaffold was built the way a real team would build software, just with an AI writing most of the code instead of a person:

1. **Architecture first** — started with a design document defining the widget type system, schema format, and command assembly pipeline before any code was written
2. **Staged deliverables** — the project was built in planned phases: core engine → widget rendering → command execution → presets → subcommands → dark mode → elevated execution → UI polish → schema generation prompt
3. **Tests alongside features** — test cases were planned with each stage, not bolted on after. The test suites (1,889 assertions across 6 suites) were written to validate each feature as it was delivered
4. **Code review cycles** — after the core was stable, the codebase went through a multi-part code review: cleanup and consistency, error handling audit, performance profiling, and a final linting pass
5. **Iteration, not generation** — most features took multiple rounds of "build it, test it, that's not right, try again." The dark mode scrollbar fix alone went through QSS, QProxyStyle, and finally native `setColorScheme` before it worked correctly
6. **Manual QA on every release** — every version was tested by hand on real tools before tagging, not just run through automated checks

The author has 15 years of professional IT experience and holds certifications in IT support, cybersecurity, ethical hacking, penetration testing, and Python development — not a software developer by trade, but far from starting from zero. Building this required real architectural thinking, problem decomposition, and knowing when the output was wrong. Claude Code is a powerful tool, but a tool still needs someone behind it who knows what they're building and why.

**Methodology: plain-English bug hunting.** Most of the bugs fixed in recent releases were found the same way: write a focused diagnostic prompt in plain English describing what's the bug or whats suspected, run it against the full codebase in a fresh context window, collect real measurements and code traces back, then write a targeted fix prompt grounded in the confirmed findings. No fix prompt is written from assumption. Every non-obvious bug gets a diagnostic pass first. It is slower than guessing, and it ships working code on the first try more often than not.

**Context switching and iteration.** Each Claude Code prompt runs in its own fresh context window. Large feature work is split across multiple windows by risk and theme — tests first, data layer second, small code changes third, UI last. Prompts include explicit "what NOT to do" guardrails and bootstrap context so the next window can orient itself from the files. This release rolled in 13 user-visible bugfixes across the cascade system, preset handling, and UI, each one discovered, diagnosed, and fixed in its own pass.

**Multi-model distillation.** External audits from Copilot, ChatGPT, and MiniMax M2.7 surface candidate findings, which are then fed back into Claude Opus Extended Thinking for architectural review and final judgment on what's real, what's noise, and what's over-engineering. The best fixes in recent releases came from this distillation loop — one model finds the lead, another model sanity-checks it, and Opus decides what actually ships.

**What's new in this release.** v2.8.0 adds cascade preset chaining (the big one — chain tool runs with delays, loops, and saveable named cascade files, all through the same QProcess pipeline as single runs) and LLM-powered preset generation (`--preset-prompt` + `PRESET_PROMPT.txt`, mirroring the existing schema-generation workflow). It also rolls in 13 bugfixes found through the plain-English diagnostic process described above.

The project has 1,889 passing test assertions across 6 suites, including a dedicated security suite that any user can run to verify the no-shell and input-handling claims directly. See the [Security](#security) section for how to run it. If you find bugs, have suggestions, or want to contribute, please open an issue or pull request!

## Support the Project

This project was built as a hobby by one person and an LLM with a lot of patience. It burned through quite a bit of token cost and mass amounts of personal time — but it was worth it. If Scaffold saves you some time or you just think it's cool, consider tossing a few sats my way. No pressure, but coffee and compute aren't free.

- **Star this repo** — it's free and it helps others find the project
- **Share your tool schemas** — submit a PR to add schemas for popular CLI tools
- **Crypto donations** — if you're feeling generous:

  | Currency | Address |
  |----------|---------|
  | **BTC** | `3MBq8n3zj58xCbdDykLdDW6PSFA9vXyRfa` |
  | **LTC** | `MQ1ZqNdS2ujMgdRvE8BUAGm3y7DV6ZKkas` |
  | **ETH** | `0xB08dFBa742487F22e47135aB734de5554262047D` |
  | **BCH** | `qrgjrpsfhfkgvwv5cd3j267tzcx5kkfzrgrngskj42` |
  | **SOL** | `5sFhB8Rs4zkFgXfLwdEt7tK2KbcnorfMjjFhgj5BYx9C` |

- **Contact** — kev@gurutechnology.services

## License

PolyForm Noncommercial 1.0.0 — free for personal and noncommercial use. For commercial licensing, contact kev@gurutechnology.services. See [LICENSE](LICENSE) for details.
