# Diagnostic: `_mask_passwords_for_display` — Overlapping Flag Names

**Date:** 2026-04-07
**Script:** `diag_pwmask.py`
**Target:** `scaffold.py` lines 2082-2128, unmodified

---

## Scenario Results

### P1: `--pass` (password, separator=none) + `--passive` (string, separator=space)

Values: `--pass` = `"secret123"`, `--passive` = `"mode"`

```
Raw cmd:    ['p1tool', '--passsecret123', '--passive', 'mode']
Masked cmd: ['p1tool', '--pass********', '--pass********', 'mode']
```

- **(c) Password leaked?** No
- **(d) Non-password incorrectly masked?** YES — `--passive` was replaced with `--pass********`

**Root cause:** Line 2121 checks `token.startswith(flag) and len(token) > len(flag)`.
`"--passive".startswith("--pass")` is `True`, so the masker treats `--passive` as
if it were `--pass` + a password value.

---

### P2: `--pass` (password, separator=space) + `--password` (string, separator=space)

Values: `--pass` = `"secret123"`, `--password` = `"hint"`

```
Raw cmd:    ['p2tool', '--pass', 'secret123', '--password', 'hint']
Masked cmd: ['p2tool', '--pass', '********', '--password', 'hint']
```

- **(c) Password leaked?** No
- **(d) Non-password incorrectly masked?** No

**Why safe:** The `separator=space` path (line 2108) uses exact equality
(`token in pw_flags`), so `--password` does not match `--pass`.

---

### P3: `--p` (password, separator=none) + `--port` (integer, separator=space)

Values: `--p` = `"x"`, `--port` = `8080`

```
Raw cmd:    ['p3tool', '--px', '--port', '8080']
Masked cmd: ['p3tool', '--p********', '--p********', '8080']
```

- **(c) Password leaked?** No
- **(d) Non-password incorrectly masked?** YES — `--port` was replaced with `--p********`

**Root cause:** Same as P1. `"--port".startswith("--p")` is `True`, so the
`separator=none` branch falsely matches. The `--port` flag token itself gets
masked; its value `8080` passes through unmasked but is now misleadingly
orphaned in the output.

---

### P4: `--pw` (password, separator=equals) + `--pwfile` (file, separator=equals)

Values: `--pw` = `"x"`, `--pwfile` = `"/tmp/file"`

```
Raw cmd:    ['p4tool', '--pw=x', '--pwfile=/tmp/file']
Masked cmd: ['p4tool', '--pw=********', '--pwfile=/tmp/file']
```

- **(c) Password leaked?** No
- **(d) Non-password incorrectly masked?** No

**Why safe:** The `separator=equals` path (line 2117) checks
`token.startswith(f"{flag}=")`, i.e. `"--pw="`. The non-password token
`"--pwfile=/tmp/file"` starts with `"--pwfile="`, not `"--pw="`. The `=`
acts as a natural delimiter that prevents prefix collisions.

---

### P5: Single `--pass` (separator=none) value `"secret"` — control

```
Raw cmd:    ['p5tool', '--passsecret']
Masked cmd: ['p5tool', '--pass********']
```

- **(c) Password leaked?** No
- **(d) Non-password incorrectly masked?** No (no other flags present)

---

## Summary Answers

### Q1: Does any password value leak through masking in P1-P4?

**No.** In all five scenarios, every password value is replaced with `********`
in the masked output. The masking function is not under-masking.

### Q2: Does any non-password token get incorrectly replaced with `********`?

**Yes.** Two scenarios exhibit false-positive masking:

| Scenario | Token masked | Masker output | Cause |
|----------|-------------|---------------|-------|
| P1 | `--passive` | `--pass********` | `"--passive".startswith("--pass")` |
| P3 | `--port`    | `--p********`    | `"--port".startswith("--p")`       |

In both cases the `separator=none` branch at line 2121 fires on a non-password
flag that happens to share a prefix with the password flag.

### Q3: For separator=none, is the prefix-only check at line 2121 actually triggerable with realistic flag pairs?

**Yes.** Both P1 and P3 demonstrate this with realistic, commonly-seen flag
pairs:

- `--pass` / `--passive` — a password flag alongside a mode flag
- `--p` / `--port` — a short password flag alongside a port flag

The `separator=none` prefix check has no delimiter to distinguish "flag + value"
from "longer unrelated flag". The `separator=equals` path avoids this because
`=` is an unambiguous delimiter. The `separator=space` path avoids it because it
uses exact token matching rather than prefix matching.

**The bug is cosmetic (display only)** — it does not affect the actual command
that gets executed, only the masked preview shown to the user. However, it makes
the displayed command misleading: affected non-password flags appear masked, and
for `separator=space` flags like `--port 8080`, the flag disappears while the
value `8080` remains, producing a confusing preview.
