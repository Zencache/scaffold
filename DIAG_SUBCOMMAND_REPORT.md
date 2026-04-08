# Diagnostic: Subcommand Name Handling

**Date:** 2026-04-07
**Script:** `diag_subcommand.py`
**Scaffold version:** current HEAD

---

## Results Table

| Tag | Name (repr) | Validates? | Errors | cmd_output |
|-----|-------------|------------|--------|------------|
| N1 | `'list'` | YES | — | `['mytool', 'list']` |
| N2 | `'remote add'` | YES | — | `['mytool', 'remote', 'add']` |
| N3 | `'list --recursive'` | YES | — | `['mytool', 'list', '--recursive']` |
| N4 | `'list -r'` | YES | — | `['mytool', 'list', '-r']` |
| N5 | `'--rm container'` | YES | — | `['mytool', '--rm', 'container']` |
| N6 | `'list; rm -rf /'` | YES | — | `['mytool', 'list;', 'rm', '-rf', '/']` |
| N7 | `'list\nrm'` | YES | — | `['mytool', 'list', 'rm']` |
| N8 | `' list'` | NO | `"name" has leading/trailing whitespace` | (not built) |

---

## Answers

### Q1: Which of N1-N8 pass validation today?

**Pass:** N1, N2, N3, N4, N5, N6, N7 (7 of 8)
**Fail:** N8 only (leading whitespace)

The subcommand name validation (lines 208-215) only checks for:
1. Non-empty string
2. Leading/trailing whitespace (`name != name.strip()`)
3. Double spaces (`"  " in name`)

It does **not** check for shell metacharacters, flag-like tokens, or newlines. The `_SHELL_METACHAR` check at line 161 is only applied to the `"binary"` field.

### Q2: For names that pass, does `.split()` at line 2068 produce multiple tokens that look like injected flags?

**Yes.** Four names produce flag-like tokens after `sub.split()` in `build_command()`:

| Tag | Name | Flag-like tokens in cmd_output |
|-----|------|-------------------------------|
| N3 | `'list --recursive'` | `--recursive` |
| N4 | `'list -r'` | `-r` |
| N5 | `'--rm container'` | `--rm` (appears as first token after binary) |
| N6 | `'list; rm -rf /'` | `-rf` |

Since QProcess uses `argv`-style lists (no shell), the semicolons in N6 are passed literally (as `list;`) and do **not** cause shell injection. However, the injected flags (`--recursive`, `-r`, `--rm`, `-rf`) become real arguments to the target binary, which could alter behavior in unexpected ways.

N7 (`"list\nrm"`) splits on the newline into `['list', 'rm']` — no flag-like tokens, but the newline causes what appears to be one subcommand name to produce two argv entries.

### Q3: Does the `_SHELL_METACHAR` check cover newline?

**No.** `_SHELL_METACHAR` is:

```
frozenset("|;&$`(){}< >!~\x00")
```

It contains 15 characters. `\n` (newline) is **not** among them. However, this is moot for subcommand names because `_SHELL_METACHAR` is never checked against subcommand names at all — only against the `binary` field (line 161).

---

## Summary

The only subcommand name rejected today is N8 (leading whitespace). All other adversarial names — including flag injection (N3-N5), shell metacharacters (N6), and embedded newlines (N7) — pass validation and produce potentially surprising `cmd_output` lists via the `.split()` on line 2068.

No shell injection is possible (QProcess doesn't use a shell), but flag injection into the target binary's argv is straightforward for any schema author who puts flag-like content in a subcommand name.
