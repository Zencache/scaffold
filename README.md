Scaffold — Your CLI Tools, but with Buttons

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)
![Single File](https://img.shields.io/badge/architecture-single%20file-blue)
![Lines of Code](https://img.shields.io/badge/lines-8%2C500%2B-informational)
![Tests](https://img.shields.io/badge/tests-2%2C260%20assertions-brightgreen)
![Test Suites](https://img.shields.io/badge/test%20suites-6-brightgreen)
![Bundled Tools](https://img.shields.io/badge/bundled%20tools-13%20schemas-orange)
![No Shell](https://img.shields.io/badge/shell%3DTrue-never-critical)
![Fully Offline](https://img.shields.io/badge/network-fully%20offline-success)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-purple)

Stop memorizing flags. Start clicking them.

Scaffold turns command-line tools into native desktop GUIs. Any tool — public or internal, simple or complex. If it accepts flags and arguments, Scaffold can build a form for it. Fill in the fields, hit Run, done.

Secure by design. Scaffold enforces a strict global NO SHELL policy, verified by a dedicated security test suite (158 assertions) you can run yourself anytime. All execution goes through PySide6's QProcess, passing flags and arguments as literal strings directly to the target binary — immune to shell injection, and leaves no shell history behind.

This works with any CLI tool, not just well-known programs like nmap or ffmpeg. If your team has a custom deployment CLI, a database migration tool, or a build script with 30 flags nobody can remember, write a schema and your team gets a GUI. Massive tools with hundreds of flags (like curl's 271-argument schema) work too.

Presets are what really make this powerful. Save your perfectly-tuned nmap recon scan, your go-to ffmpeg encoding pipeline, or your favorite hashcat attack config as a named preset with a description. Save it once, reload it anytime. Share preset files with your team. Don't want to build them by hand? Use the built-in LLM preset generation — describe what you want in plain English and drop the result into your presets folder.

Need to chain multiple tools together? The cascade system lines up sequential tool runs with per-step delays, loop mode, and runtime variables — all through the same secure QProcess pipeline. Cascades can also be saved and shared!

Under the hood, Scaffold generates interactive forms from simple JSON schema files — dropdowns, checkboxes, file pickers, and a live syntax-colored command preview. Hand a tool's man page to an LLM with the bundled SCHEMA_PROMPT.txt and get a working schema back. Collapsible sections, field search, and display groups keep large forms manageable.

Simple. Powerful. Secure by design. No telemetry, no network calls, no BS.

<p>
  <img src="nmap%20example.png" alt="Scaffold running an nmap schema" width="48%">
  <img src="hashcat%20example.png" alt="Scaffold running a hashcat schema" width="48%">
</p>

> **Disclaimer:** Much of the code was written by [Claude Code](https://claude.ai) (Opus 4.6), but the project was human-directed — designed, planned, tested, and iterated over many sessions. Not vibe-coded — every line was manually reviewed and approved. The author is not a professional software developer, but has 15 years of IT experience and multiple professional certifications. See [About This Project](#about-this-project) for the full story. The project has an automated test suite (2,260 assertions across 6 suites, including a dedicated security suite), but it has not been extensively tested in production environments. **Always review the generated commands before running them**, especially with tools that can modify files or systems.
>
> **Tip:** If a specific flag or argument isn't behaving the way you expect in the form, you can type it directly into the Additional Flags box at the bottom of any tool form. It passes your input straight through to the command line.

---

## Getting Started

### Prerequisites

- **Windows, macOS, or Linux** — tested primarily on Windows. PySide6 is cross-platform, so macOS and Linux should work but have had less testing. If you hit platform-specific issues, please open an issue.
- **Python 3.10+** — make sure Python is installed and up to date (`python --version`)
- **The CLI tool you want to use** — Scaffold builds a GUI for tools already installed on your system. For example, if you want to use the nmap schema, you need nmap installed and available in your PATH.
- **A JSON schema for your tool** — Scaffold comes with bundled schemas for 19 tools in the `tools/` folder, plus example cascade files in `cascades/`. To add your own, see [Creating Tool Schemas](#creating-tool-schemas) below.

### Install and Run

```bash
# Clone the repo
git clone https://github.com/Zencache/scaffold.git
cd scaffold

# Install the only dependency
pip install PySide6

# Launch Scaffold
python scaffold.py
```

The tool picker opens showing all `.json` schemas in the `tools/` folder (including subfolders). Tools in subfolders appear at the top in collapsible folder groups. A green checkmark means the tool is installed and ready to use; a red X means it's not found in your PATH. Double-click any tool to open its form, fill in the fields, and hit **Run**.

> **Tip:** Toggle dark mode with **Ctrl+D** or from the **View > Theme** menu.

> **Linux note:** On some distros (Ubuntu 24.04+), `pip install PySide6` may fail because the system Python is externally managed. Use a virtual environment: `python3 -m venv .venv && source .venv/bin/activate && pip install PySide6`. You may also need `sudo apt install libxcb-cursor0` for the Qt platform plugin.

To launch directly into a specific tool: `python scaffold.py tools/nmap.json`

---

## Features

- **Works with any CLI tool** — JSON schema in, native GUI out
- **Presets** — save, name, reload, and share form configurations
- **Immune to shell injection** — QProcess with list args, no shell
- **Typed input constraints** — widgets validate values at entry
- **LLM-powered schema generation** — paste SCHEMA_PROMPT.txt + docs, get a schema
- **Syntax-colored command preview** — live preview with color-coded tokens
- **Process execution** — run, stop, search output, copy or save results
- **10 widget types** — checkbox, text, spinbox, dropdown, file picker, password with show/hide, and more
- **Subcommand support** — multi-level commands like `git clone` or `ansible-galaxy role install`
- **Command history** — browse and restore past runs per tool (Ctrl+H), with filter bar
- **Cascade history** — record, browse, and restore past cascade runs (Ctrl+Shift+H), with export
- **Password masking** — values replaced with `********` in command preview, output, history, and clipboard
- **Auto-save and crash recovery** — form state saved automatically, restored on next launch
- **Collapsible display groups** — organize large forms into sections
- **Field search** — find any field by name, flag, or description (Ctrl+F)
- **Output search** — search within command output (Ctrl+Shift+F) with match highlighting and navigation
- **Process timeout** — optional auto-kill after N seconds, per tool
- **Mutual exclusivity and dependencies** — radio groups and conditional fields
- **Validation** — regex patterns and required field checking
- **Drag and drop** — drop a `.json` schema to load it
- **Portable mode** — run from USB with local settings via `portable.txt`
- **Elevated execution** — optional `pkexec` (Linux) or `gsudo` (Windows) elevation per tool
- **Cascade chaining** — chain multiple tool runs (up to 20 slots) with per-step delays, loop mode, stop-on-error, runtime variables, cascade captures, and saveable cascade files
- **LLM-powered preset generation** — generate presets from natural language with `--preset-prompt` and `PRESET_PROMPT.txt`
- **Copy as shell formats** — Bash, PowerShell, or CMD via right-click
- **Single Python file** — one file, one dependency (PySide6), fully offline

See [Detailed Features](#detailed-features) below for full descriptions.

---

## How It Works

Each CLI tool is described by a JSON schema file in the `tools/` folder. Here's a minimal example:

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
      "description": "Enable verbose output"
    },
    {
      "name": "Target",
      "flag": "TARGET",
      "type": "string",
      "positional": true,
      "required": true,
      "description": "The target to operate on"
    }
  ]
}
```

Each argument declares its type (`boolean`, `string`, `integer`, `enum`, `file`, etc.), and Scaffold picks the right widget. Fields you don't specify fall back to sensible defaults. The full schema specification is in [schema.md](schema.md), and `tools/example.json` demonstrates every feature in one file.

### Creating Tool Schemas

**The easy way: use an LLM.** The included `SCHEMA_PROMPT.txt` contains a detailed prompt that teaches any LLM to generate schemas:

1. Copy the contents of `SCHEMA_PROMPT.txt`
2. Paste it into your LLM of choice
3. Say: *"Generate a Scaffold schema for [tool name]"* and paste the tool's man page or official documentation. `--help` output alone is usually not enough — it provides flag names but lacks the detail needed for correct types, descriptions, and dependencies. The richer the input, the better the schema.
4. Save the JSON response as `tools/toolname.json`
5. Restart Scaffold (or use File > Reload)

Always validate the result:

```bash
python scaffold.py --validate tools/toolname.json
```

If validation reports errors, paste them back into the LLM and ask it to fix them — most models correct their own mistakes in one round.

> **Note:** Complex tools with many flags work best with frontier-level LLMs (Claude Opus, GPT-4, Gemini Pro). Smaller models may truncate output or produce invalid JSON.

**The manual way:** Copy `tools/example.json`, rename it, and modify it for your tool. The example schema covers all 10 widget types, subcommands, display groups, dependencies, mutual exclusivity, min/max constraints, deprecated and dangerous flags, editable suggestions, and validation patterns.

---

## Security

### No shell intermediary

Scaffold never uses `shell=True`. All command execution goes through `QProcess` with arguments passed as a Python list. There is no shell parsing, no string interpolation, and no command string assembly. Shell metacharacters in schemas or user input — pipes, semicolons, backticks, `$(...)`, glob patterns — are treated as literal strings because no shell ever interprets them. This eliminates shell injection by design, not by sanitization. The command preview shows exactly what will execute, token by token.

The `binary` field in every schema is validated at load time: shell metacharacters are rejected, relative paths with separators are rejected, and only bare executable names or absolute paths are accepted.

### Typed input constraints

Every argument passes through a typed widget that constrains values at the point of entry. A port number comes from a `QSpinBox` with defined bounds, not free text. Enum values come from a `QComboBox` with a fixed choice list. Boolean flags are checkboxes. File and directory arguments use native picker dialogs. The attack surface for malformed input is minimal because the GUI prevents it structurally.

The **Additional Flags** field is the only free-text path to the command line. It uses `shlex.split()` for tokenization with visual feedback on malformed input (unclosed quotes, etc.), and the resulting tokens are passed as discrete list items to `QProcess` — never concatenated into a shell string.

### No dynamic code execution

The codebase contains no `eval()`, no `exec()`, and no dynamic imports. Schema files are parsed as JSON data and treated as static declarations. Loading a schema reads structured data; it never executes code.

### No runtime network access

Scaffold makes zero network calls. No telemetry, no update checks, no analytics, no external API dependencies. The application runs entirely offline.

### Additional hardening

- **Atomic writes** — preset, autosave, and cascade files are written to a temp file then atomically renamed, preventing corruption on crash
- **Password masking** — password-type values are masked in the command preview, output panel, history entries, and clipboard (with a one-time confirmation prompt before exposing to clipboard)
- **Capture injection guard** — cascade captures that resolve to flag-like strings are caught and halt the chain under stop-on-error, preventing argv confusion

### Verify it yourself

Scaffold ships with a dedicated security test suite (`test_security.py`) that any user can run: static analysis for `shell=True`/`eval`/`exec`/`os.system`/`subprocess.*` patterns, shell metacharacter passthrough verification across every widget type, binary validation hardening, preset and extra-flags injection resistance, path traversal checks, recovery file safety, and direct QProcess contract verification.

```bash
python test_security.py
```

The security model has been reviewed across multiple LLM-assisted audit cycles.

---

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

### Syntax-colored command preview

Watch the exact command build in real time as you change fields. Tokens are color-coded by type (binary, flags, values) in both light and dark modes. Right-click the preview to copy formatted for Bash, PowerShell, or Windows CMD with shell-appropriate quoting.

### Process execution

Run commands directly from the GUI with colored output (stdout in one color, stderr in another), exit codes, and timestamps. The output panel is searchable (Ctrl+Shift+F). Copy or save output to file. ANSI escape codes are automatically stripped. Process stop uses SIGTERM first with SIGKILL fallback for clean shutdown. Optional auto-kill timeout per tool.

### 10 widget types

Each CLI argument gets the right input control: checkboxes for booleans, text fields for strings, spin boxes for integers and floats, dropdowns for enums, checkable lists for multi-enums, file and directory browsers, password fields with show/hide toggle, and multi-line text areas.

### Subcommand support

Tools like `git` with multiple subcommands work seamlessly. Multi-word subcommand chains like `ansible-galaxy role install` or `docker compose up` are supported — each word becomes a separate token in the assembled command. Selecting a subcommand swaps the visible form fields while global flags remain.

### Command history

Every executed command is automatically recorded. Browse recent runs per tool via View > Command History (Ctrl+H), see exit codes and timestamps, and restore any past form state with one click. A filter bar lets you search across entries.

### Cascade history

Every cascade run is automatically recorded with its full configuration snapshot and each step's post-substitution command. Open the history dialog via View > Cascade History (Ctrl+Shift+H) to browse past runs. Restore Step reloads a single step's form state; Restore Cascade reloads the entire cascade configuration into the sidebar without auto-running it. Export saves one cascade's history to JSON; Export All saves everything. Up to 50 entries are retained (oldest evicted first). In loop mode, each iteration is a separate history entry, so loop-heavy runs fill history faster. Runs interrupted by a crash appear in history as "crashed" after the next startup.

### Auto-save and crash recovery

Form state is automatically saved 2 seconds after each change. If the app crashes, the next launch offers to restore your work. Unchanged forms are not saved. Stale recovery files are cleaned up on startup.

### Cascade chaining

Chain multiple tool runs into sequential workflows from the cascade sidebar (Ctrl+G). Each cascade holds up to 20 numbered slots, each assignable to any loaded tool and an optional preset. Configure per-step delays (0–3600 seconds) to pace the chain, enable loop mode to repeat the full sequence indefinitely, or use stop-on-error mode to halt on the first non-zero exit code. Cascade variables let you define named parameters (with type hints: `string`, `file`, `directory`, `integer`, `float`) that are prompted at run time and injected into form fields across steps — useful for target IPs, output directories, or any value that changes between runs.

**Cascade captures** let later steps reuse values extracted from earlier step output. A capture can pull data from stdout or stderr via regex, read a file path, grab an exit code, or take the full output stream, then inject it into subsequent steps as a `{name}` substitution.

Cascade files can be saved, loaded, imported, exported, and deleted from the sidebar. State persists across sessions. Cascades run through the same QProcess list-based execution pipeline as single-tool runs — no shell, no shortcuts, same security guarantees. Two example cascade files are bundled in `cascades/`.

<img src="nmap%20cascade%20example.png" alt="Scaffold cascade panel running an nmap workflow" width="75%">

### LLM-powered preset generation

Generate presets from natural language using `--preset-prompt` and `PRESET_PROMPT.txt`, mirroring the schema-generation workflow. Run `python scaffold.py --preset-prompt` to print the prompt, paste it alongside the target tool's schema into any LLM, describe the preset you want in plain English, and drop the returned JSON into `presets/<tool>/`. This is useful for tools with many flags where manually configuring a preset would be tedious.

### Additional features

- **Deprecated and dangerous indicators** — schema flags can be marked `deprecated` (strikethrough + warning) or `dangerous` (red caution symbol) for visual heads-up without disabling them
- **Min/max constraints** — optional `min` and `max` on integer/float arguments constrain the spinner range
- **Drag and drop** — drop a `.json` schema file onto the window to load it
- **Help menu** — About dialog with version info and GitHub link, cascade guide, keyboard shortcuts reference
- **Session persistence** — remembers window size, position, theme, and last opened tool
- **Format markers** — `_format` metadata key prevents accidentally loading presets as tool schemas or vice versa, with clear error messages
- **Bundled example schema** — `tools/example.json` demonstrates every feature in one file
- **Portable mode** — place `portable.txt` next to `scaffold.py` to store all settings in a local INI file instead of the system registry. Run from a USB drive with fully isolated configuration
- **Bundled tool schemas** — 20 schemas covering aircrack-ng, airodump-ng, ansible (4 tools), curl, docker (3 tools), ffmpeg, git, gobuster, hashcat, nikto, nmap, openclaw, ping, and rsync. Some are mostly untested — contributions and bug reports welcome

---

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
| **Ctrl+Shift+H** | Cascade history |
| **Ctrl+O** | Load tool from file |
| **Ctrl+R** | Reload current tool |
| **Ctrl+F** | Focus field search bar |
| **Ctrl+Shift+F** | Search within output panel |
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

---

## Limitations

- **Scaffold does not auto-generate schemas.** You write the JSON (or have an LLM generate it from documentation). There is no automatic flag detection from a binary.
- **Scaffold does not sandbox the target binary.** The security model prevents shell injection and constrains input, but once a command runs, the target program has whatever permissions the user has.
- **Schema generation quality depends on the LLM and the documentation.** `--help` output alone is usually not detailed enough. Man pages or official docs produce much better schemas. Very large tools may exceed an LLM's context window.
- **Tested primarily on Windows.** PySide6 is cross-platform and Scaffold should work on macOS and Linux, but those platforms have had less testing. If you hit platform-specific issues, please open an issue.
- **Requires PySide6.** There are no plans to support other GUI frameworks.
- **Large tools with deeply nested subcommand trees** (70+ subcommands, 200+ arguments) produce usable but dense forms. Scaffold helps with discoverability and prevents syntax errors, but for very large tools it's more of a reference than a streamlined workflow.

---

## About This Project

Much of the code in Scaffold was written by [Claude Code](https://claude.ai) (Opus 4.6) with edits from the author — but this was a collaboration, not delegation. The project was designed, directed, tested, and iterated by a human who audited every line of code and every command, and made direct edits where needed. This wasn't a one-shot generation, and took very careful planning and execution.

Scaffold was built the way a real team would build software, just with an AI writing most of the code:

1. **Architecture first** — started with a design document defining the widget type system, schema format, and command assembly pipeline before any code was written
2. **Staged deliverables** — the project was built in phases: core engine, widget rendering, command execution, presets, subcommands, dark mode, elevated execution, UI polish, schema generation prompt
3. **Tests alongside features** — test cases were planned with each stage, not bolted on after. The test suites (2,192 assertions across 6 suites) were written to validate each feature as it was delivered
4. **Code review cycles** — after the core was stable, the codebase went through multi-part review: cleanup, error handling audit, performance profiling, and linting
5. **Iteration, not generation** — most features took multiple rounds of build-test-fix. The dark mode scrollbar fix alone went through QSS, QProxyStyle, and finally native `setColorScheme` before it worked correctly
6. **Manual QA on every release** — every version was tested by hand on real tools before tagging

The author has 15 years of professional IT experience and holds certifications in cybersecurity, ethical hacking, penetration testing, and Python development — not a software developer by trade, but far from starting from zero. Claude Code is a useful tool, but a tool still needs someone behind it who knows what they're building and why.

**Methodology: plain-English bug hunting.** Most bugs in recent releases were found the same way: first I describe in as much detail as possible what the bug is either in the logic or in the UI. Then we write a focused diagnostic prompt describing the suspected issue, run it against the full codebase in a fresh context window, collect measurements and code traces, then write a targeted fix grounded in confirmed findings. No fix prompt is written from assumption — every non-obvious bug gets a diagnostic pass first before writing any fixes.

**Multi-model distillation.** External audits from Copilot, ChatGPT, and other models surface candidate findings, which are fed back into Claude Opus Extended Thinking for architectural review and final judgment on what's real, what's noise, and what's over-engineering.

---

## Support the Project

This project was built as a hobby by one person, a couple computers, and a couple of LLMs. It burned through quite a bit of token cost and mass amounts of personal time — but it was worth it. If Scaffold saves you some time or you just think it's cool, consider tossing a few sats my way. No pressure, but coffee and compute aren't free.

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
