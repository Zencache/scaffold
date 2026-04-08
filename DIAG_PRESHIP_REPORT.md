# Scaffold Pre-Ship Diagnostic Report

**Date:** 2026-04-07
**File:** `scaffold.py` (7442 lines)
**Diagnostic scope:** Four reported issues — QProcess orphan, HTML injection, PowerShell quoting, CMD quoting.

## Summary table

| ID | Issue | Verdict | Severity | Fix complexity |
|----|-------|---------|----------|----------------|
| 1 | QProcess orphan on tool switch | **CONFIRMED** | High | Medium — requires signal disconnect + deferred cleanup |
| 2 | HTML injection via schema fields | **CONFIRMED** (6 sites) | Medium | Low — add `html.escape()` at each site |
| 3 | PowerShell copy quoting gaps | **CONFIRMED** | High | Low — expand trigger set |
| 4 | CMD copy quoting gaps | **CONFIRMED** | High | Low–Medium — expand trigger set + handle newlines |

---

## Issue 1 — QProcess orphan

### Current code

| Function | Line | Role |
|----------|------|------|
| `_stop_process` | 6963–6970 | Sends SIGTERM, starts 2s force-kill timer |
| `_on_force_kill` | 6972–6983 | Escalates to SIGKILL if process still running |
| `_build_form_view` | 6307–6317 | Tears down old form; calls `_stop_process` then `waitForFinished(3000)` then `self.process = None` |
| `_on_back` | 6569–6576 | Returns to picker; same stop–wait–null pattern |
| `_on_finished` | 7130–7162 | Handles process exit; resets UI; sets `self.process = None` at line 7162 |
| `_on_error` | 7164–7193 | Handles QProcess errors; sets `self.process = None` at line 7193 |
| `closeEvent` | 6144–6161 | Persists state; same stop–wait pattern but no explicit `self.process = None` |
| Timer setup | 5430–5433 | `_force_kill_timer`: single-shot, 2000 ms, connected to `_on_force_kill` |

### Trace

Taking `_build_form_view` (line 6307) as the primary path:

1. **Line 6312:** `self._stop_process()` is called.
2. **Line 6969:** Inside `_stop_process`, `self.process.terminate()` sends SIGTERM.
3. **Line 6970:** `self._force_kill_timer.start()` arms the 2-second single-shot timer.
4. **Line 6313–6314:** Back in `_build_form_view`, `self.process.waitForFinished(3000)` blocks the main thread for up to 3 seconds. Because this is a synchronous blocking call on the event-loop thread, **no Qt timers can fire** during this window — including the force-kill timer.
5. **If the process ignores SIGTERM:** `waitForFinished` returns `False` after 3 seconds. The process is still alive.
6. **Line 6315:** `self.process = None` drops the Python reference. However, the QProcess was created with `QProcess(self)` (line 7041), so Qt's parent–child ownership keeps the C++ object alive as a child of `MainWindow`.
7. **Lines 6318+ (synchronous):** The rest of `_build_form_view` executes synchronously — the force-kill timer still cannot fire.
8. **Event loop resumes:** Control returns to the event loop. The 2-second timer expired long ago (during the 3-second block), so it fires immediately.
9. **Line 6972–6974:** `_on_force_kill` checks `if not self.process` → `True` (it was set to `None` in step 6) → **returns immediately without calling `kill()`**.
10. **The orphaned QProcess survives** as a Qt child of `MainWindow`. Its `finished` signal (connected at line 7046) still points at `self._on_finished`.

**What happens when the orphan eventually exits:**

11. The orphan's `finished` signal fires, invoking `self._on_finished(exit_code, exit_status)` on the MainWindow.
12. `_on_finished` is not guarded — it unconditionally:
    - Stops `_elapsed_timer`, `_timeout_timer`, `_force_kill_timer` (line 7132–7134) — these may now belong to a **new** process run.
    - Calls `_record_history_entry` (line 7157) — records a spurious history entry for a process the user already abandoned.
    - Resets `self.run_btn` to "Run" and re-enables it (lines 7158–7160) — corrupts button state if a new process is running.
    - Sets `self.process = None` (line 7162) — **overwrites the reference to any currently-active new process**, making it uncontrollable.
13. **No signal disconnection occurs** anywhere before `self.process = None` is set — not in `_build_form_view`, not in `_on_back`, not in `closeEvent`.

**`_on_back` (line 6569):** Identical pattern — `_stop_process()`, `waitForFinished(3000)`, `self.process = None`. Same orphan risk.

**`closeEvent` (line 6144):** Same pattern, but `event.accept()` at line 6161 triggers window destruction. Qt's `~QProcess` destructor calls `kill()` on the child process, so the orphan is cleaned up by Qt's parent–child teardown. The force-kill timer (restarted inside `_stop_process` at line 6970, despite being stopped at line 6152) never fires because the window is destroyed first. **Qt's destructor saves `closeEvent` from the orphan bug, but only by accident.**

### Verdict

**CONFIRMED.** The orphan path is reachable in both `_build_form_view` and `_on_back` whenever a process ignores SIGTERM for more than 3 seconds. The orphan's `finished` signal can corrupt the UI state and null out a subsequent active process reference.

### Reproduction plan

1. Create a test schema pointing at a shell script (Linux/macOS) or batch script (Windows) that traps/ignores SIGTERM:
   ```bash
   #!/bin/bash
   trap '' SIGTERM
   echo "I ignore SIGTERM"
   sleep 30
   ```
2. Load the schema in Scaffold and click **Run**.
3. While the process is running, click **Back** (or load a different tool via the picker).
4. Observe that `waitForFinished(3000)` blocks the UI for 3 seconds, then the picker appears.
5. Load any tool and click **Run** on the new tool.
6. Wait for the original script's `sleep 30` to finish (or kill it externally).
7. **Expected corruption:** The orphan's `finished` signal fires. The Run button resets to "Run" mid-execution of the new process, and `self.process` is set to `None`, making the new process unstoppable.

### Fix sketch (one paragraph, NO code)

Before setting `self.process = None`, disconnect all signals (`finished`, `errorOccurred`, `readyReadStandardOutput`, `readyReadStandardError`) from the QProcess object. If `waitForFinished` returns `False`, call `kill()` directly on the process reference *before* nulling it, rather than relying on the timer. Alternatively, replace the timer-based force-kill with a non-blocking approach: after `terminate()`, connect a single-shot `QTimer` that checks the process state and calls `kill()`, without any `waitForFinished` blocking call on the main thread.

---

## Issue 2 — HTML injection

### Injection site inventory

#### Site A — `_build_tooltip` (lines 1582–1604)

The method assembles an HTML string with `<p>` and `<br>` tags. The following schema fields are interpolated **without `html.escape()`**:

| Field | Line | Escaped? |
|-------|------|----------|
| `arg["flag"]` | 1589 | No |
| `arg["short_flag"]` | 1591 | No |
| `arg["deprecated"]` (message text) | 1586 | No |
| `arg["description"]` | 1601 | No |
| `arg["validation"]` | 1603 | No |

`arg["type"]` (line 1592) is unescaped but drawn from a validated fixed set (10 canonical types), so injection via type requires a schema that passes validation with a crafted type — unlikely but worth noting.

The return value at line 1604 is: `"<p>" + "<br>".join(lines) + "</p>"` — this is interpreted as HTML by Qt's tooltip renderer.

#### Site B — Label construction (lines 1336–1348)

```
label_text = arg["name"]  # line 1336, UNESCAPED
```

`arg["name"]` is embedded directly into an HTML string via the `required`, `dangerous`, and `deprecated` decorators (lines 1337–1346), then rendered with `label.setTextFormat(Qt.TextFormat.RichText)` at line 1348. A schema with `"name": "<img src=x onerror=alert(1)>"` would inject arbitrary rich-text HTML into the form label. (Qt's RichText subset does not support `<script>` or JS event handlers, but supports `<img>`, `<table>`, `<font>`, arbitrary styling — enough for UI spoofing.)

#### Site C — Tool picker description tooltip (line 2721)

```python
desc_item.setToolTip(f"<p style='max-width:400px;'>{desc_text}</p>")
```

`desc_text` comes from `data.get("description", "")` — the schema's top-level `description` field. **Not escaped.**

#### Site D — Tool picker binary tooltip (lines 2706, 2710–2712)

```python
status_item.setToolTip(f"'{data['binary']}' found in PATH — ready to use")  # line 2706
status_item.setToolTip(
    f"<p>'{data['binary']}' not found in PATH. ..."  # line 2710-2712
)
```

Line 2706 is plain text (no HTML wrapper), so Qt may auto-detect and treat it as plain text — **low risk**. Line 2710 wraps in `<p>` tags with `data['binary']` **unescaped** — injectable.

#### Site E — Preset picker description tooltip (line 3173)

```python
desc_item.setToolTip(f"<p style='max-width:400px;'>{desc}</p>")
```

`desc` comes from preset JSON `_description` field. **Not escaped.**

#### Site F — Fallback widget tooltip (line 1396)

```python
w.setToolTip(f"<p>This field could not be rendered as '{arg.get('type', '?')}' ...")
```

`arg.get('type', '?')` is **unescaped** inside `<p>` tags. In the fallback path, the type value triggered an exception, so it may be an unexpected/crafted string. **Low severity** — requires a type that fails widget construction but passes initial validation.

#### Contrast case — `_colored_preview_html` (line 2371)

```python
return f"<span style='{style}'>{_html.escape(text)}</span>"
```

Uses `html.escape()` correctly, proving the pattern is known in this codebase.

### Verdict per site

| Site | Location | Verdict | Severity |
|------|----------|---------|----------|
| A | `_build_tooltip` (1582–1604) | **CONFIRMED** | Medium — 5 unescaped fields in HTML tooltip |
| B | Label construction (1336–1348) | **CONFIRMED** | Medium — `arg["name"]` as RichText |
| C | Tool picker desc tooltip (2721) | **CONFIRMED** | Medium — top-level description in HTML |
| D | Tool picker binary tooltip (2710) | **CONFIRMED** | Low — `binary` field in HTML |
| E | Preset picker desc tooltip (3173) | **CONFIRMED** | Low — preset description in HTML |
| F | Fallback widget tooltip (1396) | **CONFIRMED** | Low — type value in fallback HTML |

### Fix sketch

Apply `html.escape()` to every schema-derived or user-derived value before interpolation into HTML strings. For Site A, escape `flag`, `short_flag`, `deprecated`, `description`, and `validation` in `_build_tooltip`. For Site B, escape `arg["name"]` before wrapping in HTML decorators. For Sites C–F, escape the interpolated values. The `import html` already exists in the file (used as `_html` inside `_colored_preview_html`); a module-level `import html` or reuse of the existing local import pattern is sufficient.

---

## Issue 3 — PowerShell copy quoting

### Current code

`_format_powershell` at lines 2308–2326:

```python
def _format_powershell(cmd: list[str]) -> str:
    if not cmd:
        return ""
    parts = []
    for i, token in enumerate(cmd):
        needs_quote = " " in token or "\t" in token or "$" in token or "`" in token or "'" in token
        if i == 0 and needs_quote:
            parts.append(f"& '{token}'")
        elif needs_quote:
            if "'" in token:
                escaped = token.replace("'", "''")
                parts.append(f"'{escaped}'")
            else:
                parts.append(f"'{token}'")
        else:
            parts.append(token)
    return " ".join(parts)
```

**Current trigger set:** `{' ', '\t', '$', '`', "'"}`

**Single-quote escape handling:** Correct — `'` → `''` inside single-quoted strings (line 2320).

### Missing metacharacters (table)

| Character | PowerShell meaning | In trigger set? | Risk |
|-----------|--------------------|-----------------|------|
| `;` | Command separator | **No** | **Critical** — executes next command |
| `\|` | Pipeline operator | **No** | **Critical** — pipes to arbitrary command |
| `&` | Call/background operator | **No** | **Critical** — invokes command |
| `(` `)` | Subexpression grouping | **No** | **High** — triggers expression evaluation |
| `{` `}` | Script block delimiters | **No** | **High** — defines executable block |
| `#` | Comment character | **No** | **Medium** — truncates rest of line |
| `@` | Splatting / array literal | **No** | **Medium** — changes argument parsing |
| `>` | Output redirection | **No** | **Medium** — writes to arbitrary file |
| `<` | Input redirection | **No** | **Low** — input redirect |
| `"` | Double-quote (interpolating) | **No** | **Medium** — changes string parsing context |
| `\n` | Newline | **No** | **Critical** — new command on next line |
| `\r` | Carriage return | **No** | **Critical** — same as newline |
| `,` | Array element separator | **No** | **Low** — changes argument shape |
| ` ` (space) | Token separator | Yes | — |
| `\t` (tab) | Token separator | Yes | — |
| `$` | Variable/subexpr prefix | Yes | — |
| `` ` `` | Escape character | Yes | — |
| `'` | Literal string delimiter | Yes | — |

### Injectable test inputs (table)

| # | Input string | Current output | PowerShell behavior on paste |
|---|-------------|----------------|------------------------------|
| 1 | `test;whoami` | `test;whoami` (unquoted) | Runs `test`, then runs `whoami` |
| 2 | `foo\|Out-File C:\pwned.txt` | `foo\|Out-File C:\pwned.txt` (unquoted) | Pipes `foo` output to `Out-File`, writing to disk |
| 3 | `val & calc` | `val & calc` — **note:** triggers on space, so quoted as `'val & calc'` | **Safe** (space triggers quoting). But `val&calc` (no space) → unquoted → calls `calc` |
| 4 | `val&calc` | `val&calc` (unquoted, no trigger chars) | Runs `val` then calls `calc` |
| 5 | `test#ignored` | `test#ignored` (unquoted) | `#ignored` becomes a comment; `test` alone is executed |
| 6 | `a{Write-Host pwned}` | `a{Write-Host pwned}` (unquoted) | Script block parsed |
| 7 | `hello\nwhoami` (literal newline) | `hello` + newline + `whoami` (unquoted, newline not in trigger set) | `hello` runs, then `whoami` runs on next line |
| 8 | `>C:\pwned.txt` | `>C:\pwned.txt` (unquoted) | Redirects empty output to file, creating/truncating it |
| 9 | `value"test` | `value"test` (unquoted, `"` not in trigger set) | Unclosed double quote changes parsing of everything after |
| 10 | `@{a=1}` | `@{a=1}` (unquoted) | PowerShell hashtable literal — changes argument semantics |

### Verdict

**CONFIRMED.** The trigger set covers 5 of 18+ PowerShell metacharacters. Critical injection vectors (`;`, `|`, `&` without spaces, newlines) are completely unprotected. The quoting strategy (single quotes with `''` escape) is correct once triggered — the problem is purely that the trigger condition is too narrow.

### Fix sketch

Expand the `needs_quote` condition to include all PowerShell metacharacters: `;`, `|`, `&`, `(`, `)`, `{`, `}`, `#`, `@`, `>`, `<`, `"`, `\n`, `\r`, and `,`. A whitelist approach (quote unless the token matches `^[A-Za-z0-9_./:=-]+$`) would be more robust than a blacklist of special characters.

---

## Issue 4 — CMD copy quoting

### Current code

`_format_cmd` at lines 2329–2341:

```python
def _format_cmd(cmd: list[str]) -> str:
    if not cmd:
        return ""
    _cmd_special = set(' &|<>^%!')
    parts = []
    for token in cmd:
        if any(c in _cmd_special for c in token):
            escaped = token.replace('"', '""')
            parts.append(f'"{escaped}"')
        else:
            parts.append(token)
    return " ".join(parts)
```

**Current special set:** `{' ', '&', '|', '<', '>', '^', '%', '!'}`

**Double-quote escape handling:** `"` → `""` (line 2337). This is acceptable for most external programs' CRT argument parsing, though CMD's own parser sometimes requires `\"` or `^"`. The `""` convention is the more common choice.

### Missing characters (table)

| Character | CMD meaning | In special set? | Risk |
|-----------|-------------|-----------------|------|
| `\n` (LF) | Line break — new command | **No** | **Critical** — executes arbitrary command on next line |
| `\r` (CR) | Line break | **No** | **Critical** — same effect as LF |
| `(` `)` | Grouping operators (in IF/FOR/chained contexts) | **No** | **Low–Medium** — can break parsing in some contexts |
| `@` | Echo suppression prefix | **No** | **Low** — `@echo off` is dangerous only at line start |
| `;` | Not a separator in CMD (unlike bash) | N/A | Not a risk in CMD |
| ` ` | Token separator | Yes | — |
| `&` | Command chaining | Yes | — |
| `\|` | Pipeline | Yes | — |
| `<` `>` | Redirection | Yes | — |
| `^` | Escape character | Yes | — |
| `%` | Variable expansion | Yes | — |
| `!` | Delayed expansion variable | Yes | — |

**Key finding:** The `text` type (line 1472) uses `QPlainTextEdit`, which is a multi-line editor. Users can type or paste newlines into text fields. The `get_field_value` for text type (line 1851) calls `w.toPlainText().strip()` — `strip()` removes leading/trailing whitespace including newlines, but **preserves interior newlines**.

**Newlines inside CMD double-quotes:** Even when a value is double-quoted in CMD, a literal newline inside the quotes breaks the command. CMD does not support multi-line quoted strings. So even if the trigger set included `\n`, the `"..."` quoting strategy would not contain the injection. Newlines in CMD copy output require either replacement (e.g., space) or escaping.

### Injectable test inputs (table)

| # | Input string | Current output | CMD behavior on paste |
|---|-------------|----------------|----------------------|
| 1 | `hello\nwhoami` (literal newline in text field) | `hello` + LF + `whoami` (no trigger chars matched) | `hello` runs, then `whoami` runs as separate command |
| 2 | `hello\r\ndir C:\` (CRLF) | `hello` + CRLF + `dir C:\` (no trigger chars matched) | `hello` runs, then `dir C:\` runs |
| 3 | `foo(bar)` | `foo(bar)` (unquoted, parens not in set) | Usually works, but breaks inside `IF`/`FOR` compound commands |
| 4 | `test\nnet user hacker P@ss /add` (newline) | `test` + LF + `net user hacker P@ss /add` | Creates a new Windows user account |
| 5 | `@echo off` | `@echo off` (no trigger chars) | Suppresses echo — low risk standalone, but changes shell state |
| 6 | `value\n del /q C:\important\*` (newline) | Unquoted, split across lines | Deletes files in `C:\important\` |

### Verdict

**CONFIRMED.** The primary gap is newlines (`\n`, `\r`), which are **critical** because:
1. The `text` type widget (`QPlainTextEdit`) legitimately accepts multi-line input.
2. Newlines are not in the `_cmd_special` set, so the token passes through unquoted.
3. Even if they were in the set, CMD's double-quoting cannot contain newlines — they always break the line.

The `()` and `@` omissions are secondary concerns with lower severity.

### Fix sketch

For newlines: detect `\n` and `\r` in tokens and either replace them with spaces (lossy but safe), strip them, or refuse to copy with a warning. Double-quoting alone cannot neutralize newlines in CMD. For `(`, `)`, and `@`: add them to the `_cmd_special` set. Note that `_format_powershell` has the same newline problem (Issue 3) — single-quoting in PowerShell also cannot contain literal newlines.

---

## Cross-cutting

### Existing test coverage

| Area | Test suite | Sections | What is covered | What is NOT covered |
|------|-----------|----------|-----------------|---------------------|
| QProcess lifecycle | test_functional.py | 39b, 39e, 46p, 58f–h, 80 | `_stop_process` safe calls (no process, already stopped); `closeEvent` timer stops; `_on_finished` callback chain | Orphan scenario (SIGTERM-resistant process + tool switch); signal disconnection; force-kill timer blocked by `waitForFinished` |
| QProcess lifecycle | test_security.py | 8a–8d | QProcess contract (program, arguments) | No orphan/lifecycle tests |
| QProcess lifecycle | test_smoke.py | 3 | Basic `waitForFinished` after ping | No adversarial process tests |
| HTML injection | test_functional.py | 21a–f, 37c–g, 40a, 43a, 53a, 54a, 85–C, 86b | Tooltip content presence (flag, type, description) | No tests for HTML metacharacters in schema values; no tests verifying escaping |
| PowerShell format | test_functional.py | 51b, 51i–m, 74, 81b–c | Spaces, single quotes, `$`, backtick, empty/single | No tests for `;`, `\|`, `&`, `()`, `{}`, `#`, `@`, `>`, newlines |
| CMD format | test_functional.py | 51c, 51n–r, 81a, 92g–i | Spaces, `&`, `\|`, embedded `"`, `!` | No tests for newlines, `()`, `@` |
| Copy format setting | test_functional.py | 59c–e, 59v | Attribute existence, default, persistence | N/A |

### Recommended test locations

| Issue | Recommended suite | Rationale |
|-------|-------------------|-----------|
| 1 — QProcess orphan | `test_functional.py` (new section) | Lifecycle/state management is functional behavior. Could also add a focused case to `test_security.py` for the signal-corruption angle. |
| 2 — HTML injection | `test_security.py` (new section) | Injection from untrusted schema input is a security concern. |
| 3 — PowerShell quoting | `test_functional.py` (extend section 51 or new section) | Formatter correctness is functional. A cross-reference in `test_security.py` for the injection angle. |
| 4 — CMD quoting | `test_functional.py` (extend section 51 or new section) | Same as Issue 3. |

### Bonus findings

**Bonus 1 — `_format_powershell` has the same newline vulnerability as `_format_cmd`.**
PowerShell single-quoted strings also cannot contain literal newlines (a newline terminates the string). A text field value with `\n` injected into a PowerShell single-quoted string would break out of the string and execute the remainder as a new command. Severity: **High** (same as Issue 4).

**Bonus 2 — `_format_powershell` does not quote `"` (double quote).**
A token containing `"` without any trigger character (e.g., `val"test`) passes through unquoted. In PowerShell, an unmatched double quote changes the parsing mode for everything after it. Severity: **Medium**.

**Bonus 3 — Tool picker `data['binary']` in HTML tooltip (line 2710) is injectable.**
While listed under Issue 2 Site D, this is worth highlighting separately: the `binary` field from a crafted schema can inject HTML into the "not found in PATH" tooltip. The `binary` field is validated by `_binary_in_path()` but not for HTML content. Severity: **Low** (binary field is typically simple).

**Bonus 4 — Preset description tooltip (line 3173) shares the same class of bug as Issue 2.**
Preset JSON files are typically user-created or distributed alongside schemas. A malicious preset with `"_description": "<b><font size=72>CLICK HERE</font></b>"` would render oversized HTML in the preset picker tooltip. Severity: **Low**.

**Bonus 5 — `_on_back` and `_build_form_view` do not stop `_force_kill_timer` before `_stop_process`.**
In `closeEvent` (line 6152), `_force_kill_timer.stop()` is called before `_stop_process()` — but this is pointless because `_stop_process` restarts it (line 6970). In `_on_back` and `_build_form_view`, the timer is not stopped at all before `_stop_process`. This is not a separate bug (it's the same Issue 1 mechanism) but confirms the pattern is inconsistent across all three call sites.
