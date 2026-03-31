# Scaffold — Your CLI Tools, but with Buttons

**Stop memorizing flags. Start clicking them.**

Scaffold turns command-line tools into native desktop GUIs. Any tool — public or internal, simple or complex. If it accepts flags and arguments, Scaffold can build a form for it. Fill in the fields, hit Run, done.

This works with **any CLI tool** — not just well-known programs like nmap or ffmpeg. If your team has a custom deployment CLI, a database migration tool, or a build script with 30 flags that nobody can remember, write a schema and your team gets a GUI. Massive tools with hundreds of flags (like curl's 271-argument schema) work too.

And then there are **presets**. Save your perfectly-tuned nmap recon scan, your go-to ffmpeg encoding pipeline, or your favorite hashcat attack config as a named preset with a description. No more digging through shell history or old notes for that command you ran three weeks ago. Save it once, reload it anytime. Share preset files with your team. Build a personal library of ready-to-run commands for every tool you use.

Under the hood, Scaffold generates interactive forms from simple JSON schema files — dropdowns, checkboxes, file pickers, a live syntax-colored command preview — all from a single schema that describes your tool's arguments. No custom UI code needed. Hand the `--help` output or man page to an LLM with the bundled `PROMPT.txt` and get a working schema back. Collapsible sections, field search, and display groups keep large forms manageable.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Single File](https://img.shields.io/badge/single%20file-3%2C748%20lines-orange)

<p>
  <img src="nmap%20example.png" alt="Scaffold — nmap example" width="48%">
  <img src="hashcat%20example.png" alt="Scaffold — hashcat example" width="48%">
</p>

> **Disclaimer:** This is an early-stage hobby project. All code was written by [Claude Code](https://claude.ai) (Opus 4.6), but the project was human-directed — designed, planned, tested, and iterated over many sessions. Not vibe-coded — every line of code and every command was manually reviewed and approved, with the author making direct edits where needed. This was a collaboration, not delegation. The author has 15 years of IT experience and multiple professional certifications. See [About This Project](#about-this-project) for the full story. While it has an automated test suite (662 assertions across 5 suites), it has not been extensively tested in production environments. Scaffold should work with any CLI tool that accepts flags and arguments, but tools with very large man pages or hundreds of flags may exceed the LLM's context window during schema generation, resulting in incomplete or inaccurate output. On the UI side, complex tools with deeply nested subcommand trees (like OpenClaw with 70+ subcommands and 200+ arguments) can produce forms that are harder to navigate. Scaffold still gives you a command overview and prevents syntax errors, but for very large tools it may be more of a reference than a streamlined workflow. **Always review the generated commands before running them**, especially with tools that can modify files or systems. If you hit issues with a specific version, try rolling back. Use at your own risk. Contributions and bug reports welcome!

---

## Getting Started

### Prerequisites

- **Windows, macOS, or Linux** — Scaffold has been tested on Windows. It should work on macOS and Linux as well (PySide6 is cross-platform), but these have not been extensively tested. If you run into platform-specific issues, please open an issue!
- **Python 3.10+** — make sure Python is installed and up to date (`python --version`)
- **pip** — should come with Python; update it with `pip install --upgrade pip`
- **The CLI tool you want to use** — Scaffold builds a GUI for tools already installed on your system. For example, if you want to use the nmap schema, you need nmap installed and available in your PATH.
- **A JSON schema for your tool** — Scaffold comes with example schemas (nmap, ping, git, curl) in the `tools/` folder. To add your own, see [Creating Tool Schemas](#creating-tool-schemas) below.

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

The tool picker will open showing all `.json` schemas in the `tools/` folder. A green checkmark means the tool is installed and ready to use; a red X means it's not found in your PATH. Double-click any tool to open its form, fill in the fields, and hit **Run**.

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

- **Works with any CLI tool** — if it accepts flags and arguments, Scaffold can build a GUI for it. From simple utilities to tools with hundreds of flags and nested subcommands. Write a JSON schema (or have an LLM generate one from the docs) and you're done
- **Presets** — save, name, and reload entire form configurations. Build a library of ready-to-run commands per tool. Share preset files with your team. Never reconstruct a complex command from memory again
- **LLM-powered schema generation** — paste the included `PROMPT.txt` into any LLM along with a tool's `--help` output or man page, and get a working schema back. Works with any model that can output JSON
- **Syntax-colored command preview** — watch the exact command build in real time as you change fields, with color-coded tokens (binary, flags, values) in both light and dark modes
- **Process execution** — run commands directly with colored output (stdout, stderr, exit codes), searchable output panel, and one-click export to file
- **9 widget types** — checkboxes, text fields, spinners, dropdowns, multi-select lists, file/directory browsers, and more — each CLI argument gets the right input control
- **Subcommand support** — tools like `git` with multiple subcommands work seamlessly
- **Collapsible display groups** — visually group related arguments into collapsible sections to tame tools with hundreds of flags
- **Field search** — Ctrl+F to instantly find any field by name or flag in large forms
- **Process timeout** — optional auto-kill after N seconds, saved per tool
- **Mutual exclusivity & dependencies** — radio-button groups for conflicting flags, fields that activate only when their parent is set
- **Validation** — regex patterns and required field checking, catch mistakes before you run
- **Drag and drop** — drop a `.json` schema onto the window to load it
- **Session persistence** — remembers window size, position, theme, and last opened tool
- **Single Python file** — just `scaffold.py`, one dependency (PySide6), runs entirely offline

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
- Click **Run** to execute (or **Ctrl+Enter**)
- Click **Stop** to kill a running process (or **Escape**)
- Click **Copy Command** to copy to clipboard

> **Important:** Always review the command preview before clicking Run. Scaffold assembles commands from your input and executes them directly on your system.

## Creating Tool Schemas

Each CLI tool is described by a JSON file placed in the `tools/` folder. Scaffold scans this folder on startup and displays all valid schemas in the tool picker.

### The Easy Way: Use an LLM

The included `PROMPT.txt` file contains a detailed prompt that teaches any LLM (ChatGPT, Claude, Gemini, etc.) to generate schemas for you:

1. Copy the contents of `PROMPT.txt`
2. Paste it into your LLM of choice
3. Then say: *"Generate a Scaffold schema for [tool name]"* and paste the tool's `--help` output, man page, or other relevant documentation
4. Save the JSON response as `tools/toolname.json`
5. Restart Scaffold (or use File > Reload) — the new tool appears in the picker

> **Note:** Generating schemas for complex tools (like curl or ffmpeg) with many flags requires a large context window and works best with frontier-level LLMs (Claude Opus, GPT-4, Gemini Pro, etc.). Smaller or older models may truncate output, miss fields, or produce invalid JSON. Always validate the result with `python scaffold.py --validate tools/toolname.json`.

> **Note:** LLM-generated schemas may contain errors. Always validate with `python scaffold.py --validate tools/toolname.json` and test the generated commands before relying on them.

> **Tip:** If validation fails, paste the error messages back into the LLM conversation and ask it to fix them. Most models can correct their own mistakes in one round when shown the specific validation errors. For example: *"The validator returned these errors: [paste errors]. Fix the JSON and return the corrected version."*

### The Manual Way

Create a JSON file following this structure:

```json
{
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
| `tool` | string | Yes | Display name shown in the picker and form header |
| `binary` | string | Yes | The actual executable name (must be in PATH to run) |
| `description` | string | Yes | Short description of the tool |
| `arguments` | array | Yes | List of global argument objects |
| `subcommands` | array or null | No | List of subcommand objects (for tools like `git`) |

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

## Presets

Presets save and restore the complete state of a form:

- **Save**: Presets > Save Preset (Ctrl+S) — enter a name
- **Load**: Presets > Load Preset (Ctrl+L) — pick from saved presets
- **Delete**: Presets > Delete Preset
- **Reset**: Presets > Reset to Defaults — clears everything back to schema defaults

Presets are stored as JSON files in `presets/{tool_name}/` next to `scaffold.py`. They're portable — you can share preset files with others.

Presets handle schema changes gracefully:
- Fields removed from the schema are silently skipped
- New fields added to the schema get their default values
- Renamed fields: old name is skipped, new name gets its default

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+Enter** | Run the command |
| **Escape** | Stop a running process |
| **Ctrl+S** | Save preset |
| **Ctrl+L** | Load preset |
| **Ctrl+O** | Load tool from file |
| **Ctrl+R** | Reload current tool |
| **Ctrl+F** | Focus field search bar (type to find fields by name or flag) |
| **Ctrl+Shift+F** | Search within output panel (highlights matches, Enter/Shift+Enter to navigate) |
| **Ctrl+D** | Toggle dark mode |
| **Ctrl+B** | Back to tool picker |
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
```

## Included Example Schemas

| File | Tool | Highlights |
|------|------|------------|
| `tools/nmap.json` | nmap | All 9 widget types, groups, dependencies, validation, repeatable flags |
| `tools/ping.json` | ping | Simple tool, mutual exclusivity group (IPv4/IPv6) |
| `tools/git.json` | git | 4 subcommands, scoped arguments, equals separators |
| `tools/curl.json` | curl | HTTP client, string/boolean/file/integer fields |
| `tools/nikto.json` | nikto | String+examples for code-concatenation flags, enum vs examples distinction |
| `tools/gobuster.json` | gobuster | 7 subcommands with scoped flags, repeatable headers, file types |
| `tools/hashcat.json` | hashcat | Positional arg ordering, examples vs enum (-m vs -a), equals separators |
| `tools/openclaw.json` | openclaw | AI agent platform, 10+ subcommands, gateway with auth/tailscale options |
| `tools/ffmpegv2.json` | FFmpeg | 123 arguments, string+examples for codecs/formats, equals separators |

## Requirements

- **Python 3.10+**
- **PySide6** (`pip install PySide6`)
- That's it. No other dependencies.

## About This Project

Every line of code in Scaffold was written by [Claude Code](https://claude.ai) (Opus 4.6) — but this was a collaboration, not delegation. The project was designed, directed, tested, and iterated by a human who manually audited every line of code and every command, and made direct edits where needed. This wasn't a one-shot generation.

Scaffold was built the way a real team would build software, just with an AI writing the code instead of a second person:

1. **Architecture first** — started with a design document defining the widget type system, schema format, and command assembly pipeline before any code was written
2. **Staged deliverables** — the project was built in planned phases: core engine → widget rendering → command execution → presets → subcommands → dark mode → elevated execution → UI polish → schema generation prompt
3. **Tests alongside features** — test cases were planned with each stage, not bolted on after. The test suites (662 assertions across 5 suites) were written to validate each feature as it was delivered
4. **Code review cycles** — after the core was stable, the codebase went through a multi-part code review: cleanup and consistency, error handling audit, performance profiling, and a final linting pass
5. **Iteration, not generation** — most features took multiple rounds of "build it, test it, that's not right, try again." The dark mode scrollbar fix alone went through QSS, QProxyStyle, and finally native `setColorScheme` before it worked correctly
6. **Manual QA on every release** — every version was tested by hand on real tools before tagging, not just run through automated checks

The author has 15 years of professional IT experience and holds certifications in IT support, cybersecurity, ethical hacking, penetration testing, and Python development — not a software developer by trade, but far from starting from zero. Building this required real architectural thinking, problem decomposition, and knowing when the output was wrong. Claude Code is a powerful tool, but a tool still needs someone behind it who knows what they're building and why.

The project has 662 passing test assertions across 5 suites, but should still be considered early-stage software. If you find bugs, have suggestions, or want to contribute, please open an issue or pull request!

## Support the Project

This project was built as a hobby by one person and an LLM with a lot of patience. It burned through more than $100 in API credits and mass amounts of personal time — but it was worth it. If Scaffold saves you some time or you just think it's cool, consider tossing a few sats my way. No pressure, but coffee and compute aren't free.

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

MIT — free to use, modify, and distribute. See [LICENSE](LICENSE) for details.
