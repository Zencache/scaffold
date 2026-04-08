#!/usr/bin/env python3
"""Diagnostic 5 — Elevation tool cache & module globals (C4, M3, TG8).

Investigates the caching behavior of scaffold._elevation_tool,
scaffold._already_elevated, and scaffold._find_elevation_tool().

DO NOT modify scaffold.py.
"""

import shutil
import sys
from unittest.mock import patch

# ── helpers ──────────────────────────────────────────────────────────────────
passed = 0
failed = 0


def report(label, value):
    print(f"  {label}: {value!r}")


def section(n, title):
    print(f"\n{'='*60}")
    print(f"  Step {n}: {title}")
    print(f"{'='*60}")


def check(label, condition):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {label}")
    return condition


# ── Need QApplication before importing scaffold (it imports PySide6) ─────────
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

import scaffold  # noqa: E402

# ═════════════════════════════════════════════════════════════════════════════
# Step 1: Report initial module-level values
# ═════════════════════════════════════════════════════════════════════════════
section(1, "Initial module globals after import")
report("scaffold._elevation_tool", scaffold._elevation_tool)
report("scaffold._already_elevated", scaffold._already_elevated)
check("_elevation_tool starts as None", scaffold._elevation_tool is None)
check("_already_elevated starts as None", scaffold._already_elevated is None)

# ═════════════════════════════════════════════════════════════════════════════
# Step 2: Call _find_elevation_tool(), observe caching
# ═════════════════════════════════════════════════════════════════════════════
section(2, "First call to _find_elevation_tool()")
result1 = scaffold._find_elevation_tool()
report("return value", result1)
report("scaffold._elevation_tool after call", scaffold._elevation_tool)
check("Return matches cached value", result1 == scaffold._elevation_tool)
check("Cache is now a string (possibly empty)", isinstance(scaffold._elevation_tool, str))

# Record whether a real tool was found
real_tool_found = bool(result1)
print(f"  (Real elevation tool found on this system: {real_tool_found})")

# ═════════════════════════════════════════════════════════════════════════════
# Step 3: Monkey-patch shutil.which -> "/usr/bin/pkexec", call again
# ═════════════════════════════════════════════════════════════════════════════
section(3, "Patch shutil.which to always return '/usr/bin/pkexec', call again")

# Cache is already set from Step 2 — the patch should NOT matter
with patch.object(shutil, "which", return_value="/usr/bin/pkexec"):
    result2 = scaffold._find_elevation_tool()
    report("return value (cache should win)", result2)
    check(
        "Cache prevents re-lookup (returns same as Step 2)",
        result2 == result1,
    )

# ═════════════════════════════════════════════════════════════════════════════
# Step 4: Reset cache to None, call with patch still simulated
# ═════════════════════════════════════════════════════════════════════════════
section(4, "Reset _elevation_tool = None, then call with pkexec patch")

scaffold._elevation_tool = None  # force cache miss
with patch.object(shutil, "which", return_value="/usr/bin/pkexec"):
    result3 = scaffold._find_elevation_tool()
    report("return value (should find pkexec now)", result3)
    report("scaffold._elevation_tool after call", scaffold._elevation_tool)
    # On Windows, _find_elevation_tool checks for "gsudo", not "pkexec",
    # but our patch returns "/usr/bin/pkexec" for ANY input.
    check("Fresh lookup honors the patch", result3 == "/usr/bin/pkexec")

# ═════════════════════════════════════════════════════════════════════════════
# Step 5: Simulate user installing pkexec mid-session
#         First call: which returns None (not installed)
#         Second call: which returns a path (now installed)
# ═════════════════════════════════════════════════════════════════════════════
section(5, "Simulate mid-session tool installation")

scaffold._elevation_tool = None  # reset cache

call_count = 0
def staged_which(name):
    """First call returns None, subsequent calls return a path."""
    global call_count
    call_count += 1
    if call_count == 1:
        return None
    return "/usr/bin/pkexec"

with patch.object(shutil, "which", side_effect=staged_which):
    # First call — tool not found
    result4a = scaffold._find_elevation_tool()
    report("1st call return (not installed yet)", result4a)
    report("scaffold._elevation_tool", scaffold._elevation_tool)
    check("First call caches empty string", result4a == "")
    check("Module global is empty string", scaffold._elevation_tool == "")

    # Second call — tool is now "installed", but cache is set
    result4b = scaffold._find_elevation_tool()
    report("2nd call return (installed, but cache blocks)", result4b)
    check(
        "Cache returns '' even though tool is now available",
        result4b == "",
    )
    check(
        "shutil.which was only called once (first call cached '')",
        call_count == 1,
    )

# ═════════════════════════════════════════════════════════════════════════════
# Step 6: Verify _check_already_elevated caching too
# ═════════════════════════════════════════════════════════════════════════════
section("6", "_check_already_elevated caching")

scaffold._already_elevated = None  # reset
result_elev1 = scaffold._check_already_elevated()
report("First call result", result_elev1)
report("scaffold._already_elevated", scaffold._already_elevated)
check("Cached after first call", scaffold._already_elevated is not None)

# Flip the cached value — next call should return the cached (wrong) value
scaffold._already_elevated = not result_elev1
result_elev2 = scaffold._check_already_elevated()
check(
    "Returns cached value even when flipped",
    result_elev2 == (not result_elev1),
)

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  RESULTS: {passed} passed, {failed} failed")
print(f"{'='*60}")

# ── Key findings ─────────────────────────────────────────────────────────────
print("""
KEY FINDINGS:
  Q1 (retry after ""): Once _find_elevation_tool() caches "" (empty string),
      it never retries. The guard `if _elevation_tool is not None` is true
      for "" (a non-None string), so subsequent calls return "" immediately.

  Q2 (test pollution): No test in test_functional.py or test_security.py
      references _elevation_tool or _already_elevated. The "elevated" key
      appears only as schema field data (always None). Zero risk of
      cross-test cache pollution because no test exercises the cache.

  Q3 (hot-detection UX): The cache is a non-issue in practice.
      - The elevation checkbox only appears when schema.elevated is
        "optional" or "always" AND the app is NOT already elevated.
      - get_elevation_command() is called at run-time (button click),
        not at startup.
      - A user who installs pkexec/gsudo mid-session would need to
        restart the app for it to be detected. But this is a rare edge
        case: the schema explicitly marks tools that need elevation,
        and users almost always have the tool installed before launching.
      - The error message in get_elevation_command() tells the user
        exactly how to install the tool, so the failure is graceful.
""")

sys.exit(1 if failed else 0)
