# Diagnostic 5 — Elevation Tool Cache & Module Globals

**Tags:** C4, M3, TG8
**Date:** 2026-04-07
**Script:** `diag_elevation.py` (12/12 checks pass)

---

## Code Under Investigation

```
scaffold.py lines 526–597
```

| Global | Type | Initial | Set by |
|---|---|---|---|
| `_elevation_tool` | `str \| None` | `None` | `_find_elevation_tool()` |
| `_already_elevated` | `bool \| None` | `None` | `_check_already_elevated()` |

Both use the same pattern: `if cached is not None: return cached`. This means
**any** non-`None` value — including `""` (empty string) and `False` — is
treated as "already resolved" and short-circuits all future lookups.

---

## Q1: Once `_find_elevation_tool()` returns `""`, does it ever retry?

**No.** Confirmed by `diag_elevation.py` Step 5.

The guard is `if _elevation_tool is not None`, and `"" is not None` evaluates
to `True`. Once the cache holds `""`, every subsequent call returns `""`
immediately without calling `shutil.which()` again.

The same applies to `_check_already_elevated()`: once it caches `False`, it
never re-checks even if the process later gains privileges (hypothetically
impossible in practice, but the pattern is identical).

## Q2: Are there any tests polluted by or dependent on the cached value?

**No.** Zero test coverage of the elevation cache exists.

- `test_functional.py`: The string `"elevated"` appears only as a schema
  field value (always `None`). No test references `_elevation_tool`,
  `_already_elevated`, `_find_elevation_tool`, `get_elevation_command`, or
  `_check_already_elevated`.
- `test_security.py`: No matches for any elevation identifier.
- No test resets either global between runs.
- Running `test_functional.py` produces no elevation-related output. The
  single failure (`window width restored`) is an unrelated GUI flake.

**Conclusion:** Test ordering cannot matter because no test touches the cache.
There is no cross-test pollution, but also no test protection — the cache
logic is entirely untested.

## Q3: Is the cache an actual UX bug or a non-issue?

**Non-issue in practice.** The "install mid-session" scenario is not a
realistic user flow, and the failure mode is graceful.

### Why:

1. **Schema-driven visibility.** The elevation checkbox only appears when a
   schema declares `"elevated": "optional"` or `"elevated": "always"` AND
   the app is not already running elevated. If neither condition holds, the
   entire elevation code path is unreachable.

2. **Late binding.** `get_elevation_command()` is called at button-click
   time (Run, Copy, etc.), not at form-build time. The cache is populated
   on first click, not at startup.

3. **Graceful error.** If the tool isn't found, `get_elevation_command()`
   returns an error message with install instructions (`winget install
   gerardog.gsudo` / `brew install polkit` / package manager). The user
   sees a `QMessageBox.warning` dialog — not a crash or silent failure.

4. **Restart is natural.** A user who installs `gsudo` or `pkexec` after
   seeing the error message will almost certainly restart their terminal
   (and thus Scaffold) to pick up PATH changes anyway. The cache aligns
   with this natural workflow.

5. **No production caller cares about hot-detection.** All four call sites
   for `get_elevation_command()` (lines 6800, 6836, 6874, 6983) are
   triggered by user actions (run button, copy button). None loop or poll
   for a newly-installed tool.

### The only theoretical gap:

A user who:
- Opens Scaffold with a schema that has `elevated: "optional"`
- Clicks Run, sees the "install gsudo" error
- Installs gsudo in another terminal without restarting Scaffold
- Clicks Run again in the same session

...would still see the error. They'd need to restart Scaffold. This is a
minor papercut at worst, affecting a rare edge case with an obvious
workaround.

---

## Architecture Notes

The caching pattern (`None` = unresolved, `""` = resolved-to-nothing) is
sound but slightly unusual. A sentinel like `_UNSET = object()` would be
more explicit and avoid the `"" is not None` subtlety. However, this is a
style observation, not a bug.

The `_already_elevated` cache is even less of a concern: privilege level
cannot change within a running process on any supported platform.

---

## Summary

| Question | Answer |
|---|---|
| Cache prevents retry after `""`? | Yes — confirmed, by design |
| Tests affected by cache? | No — zero test coverage of elevation cache |
| UX bug? | No — graceful error + restart is natural workflow |
