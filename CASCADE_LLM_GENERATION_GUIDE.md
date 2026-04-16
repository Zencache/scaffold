# Cascade Generation (Experimental)

> ⚠️ **EXPERIMENTAL FEATURE** — This is a documentation-only workflow for generating Scaffold cascade files via an LLM with persistent access to your tool schemas and presets. It has not been extensively validated. Results depend heavily on the quality and coverage of your preset library. Expect rough edges. Feedback welcome.

## What This Is

Scaffold already supports LLM-powered schema and preset generation via `SCHEMA_PROMPT.txt` and `PRESET_PROMPT.txt` — you paste a prompt plus source material into any frontier LLM and get JSON back. Cascades are harder because they reference *multiple* tools, and pasting several full tool schemas into one chat window quickly exhausts usable context.

This guide describes a workaround: configure a Claude Project (or equivalent LLM environment with persistent file access) that already has your `tools/` and `presets/` directories loaded. Then ask it to generate cascades in natural language. No pasting schemas per request — the LLM reads from project knowledge.

## Prerequisites

- A Claude.ai account with Projects enabled (Pro or Team tier), or an equivalent LLM environment supporting persistent document context
- Your populated `tools/` directory with the schemas you want to chain
- Your populated `presets/` directory — **this is load-bearing**; see below
- Familiarity with Scaffold's cascade format (see `schema.md` and existing files in `cascades/`)

## Why Presets Matter More Than Schemas Here

The generated cascade quality is bounded by preset coverage. Presets are pre-validated flag combinations with human-written descriptions — the LLM can reason about "which preset fits this step" far more reliably than "which flags from 200 options should I combine." Schemas are the fallback when no suitable preset exists.

Before using this workflow seriously, invest in presets:

- Every tool you want to chain should have at least 2–3 presets covering common use cases
- Every preset should have a clear `_description` field
- Preset names should be intent-describing (`ping_sweep`, not `preset_1`)

Thin preset libraries produce thin cascades.

## Setup

1. **Create a new Claude Project.** Name it something like "Scaffold Cascade Generator."
2. **Upload your tool schemas.** Drag every `.json` file from your `tools/` directory into the project knowledge.
3. **Upload your presets.** Drag every `.json` file from your `presets/<tool>/` subdirectories into the project knowledge. If you have many, zip them by tool and upload — Claude Projects will index the contents.
4. **Paste the instructions block.** Copy everything below the divider at the bottom of this file and paste it into the project's **Custom Instructions** field.
5. **Test with a simple request.** Start with a two-step cascade you already know works — it validates the setup before you trust it with something novel.

### Keeping the Project Synced

When you add new schemas or presets to Scaffold, re-upload them to the Project. There is no automatic sync. A good habit: after each Scaffold session where you created a new preset, update the Project before your next cascade-generation session.

## Usage

In the configured Project, describe the cascade you want in plain English. Be specific about:

- Which tools to use (or let the LLM pick from available schemas)
- What data should flow between steps (captures)
- Whether the chain should loop, stop on error, etc.

Example requests:

- *"Generate a cascade that uses nmap to find live hosts on 192.168.1.0/24, then runs a service scan against each live host."*
- *"Chain curl to fetch an auth token from our staging API, then use that token in a follow-up POST."*
- *"Two-step cascade: `which python3` then `ls -la` on the discovered path."*

The LLM returns cascade JSON. Save it to `cascades/<name>.json` and open it in Scaffold's cascade sidebar.

## Known Limitations

- **Context drift over long Project lifetimes.** If you've uploaded hundreds of files, the LLM may retrieve irrelevant ones. Mitigation: start fresh Projects periodically, or scope Projects to specific tool families.
- **Capture regexes are best-effort.** The LLM doesn't run your tools; it guesses output format from documentation it may or may not have in context. Always review generated capture patterns against real output before trusting them.
- **No validation loop.** The generated JSON may reference flags that don't exist in a specific schema version, or captures with colliding names. Scaffold's loader will catch most of these, but not all. Test every generated cascade before relying on it.
- **Multi-level subcommands.** Tools with nested subcommands (`docker compose up`, `ansible-galaxy role install`) are harder for the LLM to reason about. Presets help a lot here because they pin the subcommand scope.
- **No multi-cascade array output.** Unlike `PRESET_PROMPT.txt`, this workflow generates one cascade at a time. Ask for multiple in sequence if needed.

## Feedback

If you try this and hit issues — generated JSON that won't load, captures that don't extract, presets the LLM ignored — please open an issue with the request you made, the JSON you got back, and what went wrong. This feature is experimental precisely because the edge cases aren't mapped yet.

---

=== PASTE EVERYTHING BELOW THIS LINE INTO PROJECT CUSTOM INSTRUCTIONS ===

You are a cascade-file generator for Scaffold, a Python desktop app that runs chained CLI tool invocations. Your job is to convert natural-language requests into valid Scaffold cascade JSON files.

## Hard Rules

1. Return ONLY raw JSON. No markdown fences, no preamble, no trailing explanation.
2. Only reference tools whose schemas exist in project knowledge. Never invent tools.
3. Only use flags that exist in the referenced tool's schema. Verify against the schema file before emitting.
4. **Prefer presets over raw flag combinations.** If a preset in project knowledge matches the step's intent, reference it by name and override only what's necessary.
5. Fall back to full-schema flag selection only when no suitable preset exists.
6. Capture names must match `[A-Za-z_][A-Za-z0-9_]*` and must not collide with cascade variable names.
7. Captures are forward-only. Step N can only reference captures from steps 1 through N-1.
8. Every flag key must exist in the schema at the correct scope (global vs subcommand-scoped).
9. For enum/multi_enum fields, values must come from the schema's `choices` array.
10. Respect `depends_on` chains — if flag B depends on flag A, include A.
11. Only one flag per mutual-exclusivity `group`.

## Cascade JSON Shape

```json
{
  "_format": "scaffold_cascade",
  "name": "short-kebab-case-name",
  "description": "One-line human description of the cascade's purpose",
  "loop_mode": false,
  "stop_on_error": true,
  "variables": [
    {
      "name": "display_name",
      "flag": "--flag-name",
      "type_hint": "string",
      "apply_to": "all"
    }
  ],
  "steps": [
    {
      "tool": "tools/toolname.json",
      "preset": "presets/toolname/preset.json",
      "delay": 0,
      "captures": [ /* see capture shape below */ ]
    }
  ]
}
```

`preset` is a relative path string (e.g. `"presets/nmap/quick.json"`) or `null`. There is no inline-preset mechanism. If no suitable preset exists for a step, tell the user to generate one via `PRESET_PROMPT.txt` first.

`variables` may be an empty array if no user-defined variables are needed. Each variable has: `name` (display label), `flag` (the CLI flag it maps to), `type_hint` (`"string"`, `"integer"`, `"float"`, etc.), and `apply_to` (`"all"`, `"none"`, or a list of 0-based step indices like `[0, 2]`).

## Capture Shape

```json
{
  "name": "<identifier, [A-Za-z_][A-Za-z0-9_]*>",
  "source": "stdout | stderr | file | exit_code | stdout_tail | stderr_tail",
  "pattern": "<regex, max 200 chars, required for stdout/stderr sources>",
  "group": 1,
  "path": "<literal filesystem path, required for source 'file'>"
}
```

Source reference:
- `stdout` / `stderr` — regex match against the step's output (last 64KB). Use `pattern` + `group`.
- `file` — the literal filesystem path string from the capture's `path` key, passed through unchanged. Does NOT read the file's contents. Use when one tool writes a file (e.g. `nmap -oX out.xml`) and a later tool consumes that path as an argument.
- `exit_code` — the step's exit code as a string.
- `stdout_tail` / `stderr_tail` — last 64KB of the stream contents, no regex needed. Use these when you want the whole tail of output captured into a variable.

## Substitution Syntax

Later steps reference captured values with `{name}` tokens inside preset field values. Example: step 1 captures `target_host`, step 2's preset sets `"TARGET": "{target_host}"`.

## Generation Workflow

1. Read the user's request. Identify the sequence of tools needed.
2. For each step, search project knowledge for presets matching that step's intent. Prefer matches.
3. If a preset fits, reference it and only override fields that must change for the cascade (usually targets or captured-value substitutions).
4. If no preset fits, select flags from the schema directly. Keep the set minimal.
5. Wire captures between steps. For each capture, write a regex against the tool's documented output format. If output format is unclear from the schema, prefer `stdout_tail` over a guessed regex.
6. Set `stop_on_error: true` by default unless the user specifies otherwise.
7. Validate your output against the Hard Rules before returning.

## Self-Check Before Returning

- Is `_format` exactly `"scaffold_cascade"`?
- Does every `tool` value match an actual schema binary name?
- Does every flag key exist in the referenced schema?
- Are all capture names unique within the cascade and within each step?
- Do all `{name}` substitution tokens reference captures defined in earlier steps?
- Are enum/multi_enum values from the schema's `choices` array?
- Is the output valid JSON — no trailing commas, no comments, no markdown fences?

If any check fails, fix it before returning.
