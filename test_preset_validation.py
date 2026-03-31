"""Tests for validate_preset() — Phase 1 of Import Validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

import scaffold

passed = 0
failed = 0
errors = []


def check(condition, name):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  FAIL: {name}")


# =====================================================================
print("\n=== Preset Validation: Basic Structure ===")
# =====================================================================

# 1. Valid preset dict passes
result = scaffold.validate_preset({"__global__:--verbose": True, "__global__:--output": "/tmp/out"})
check(result == [], f"1: valid preset passes (got {result})")

# 2. Empty dict passes (user saved with all defaults)
result = scaffold.validate_preset({})
check(result == [], f"2: empty dict passes (got {result})")

# 3. Non-dict: list
result = scaffold.validate_preset([1, 2, 3])
check(len(result) > 0 and "dict" in result[0].lower(), f"3: list rejected (got {result})")

# 4. Non-dict: string
result = scaffold.validate_preset("not a dict")
check(len(result) > 0 and "dict" in result[0].lower(), f"4: string rejected (got {result})")

# 5. Non-dict: None
result = scaffold.validate_preset(None)
check(len(result) > 0, f"5: None rejected (got {result})")

# 6. Non-dict: integer
result = scaffold.validate_preset(42)
check(len(result) > 0, f"6: integer rejected (got {result})")


# =====================================================================
print("\n=== Preset Validation: Key Checks ===")
# =====================================================================

# 7. Dict with non-string key fails
result = scaffold.validate_preset({123: "value"})
check(any("key must be a string" in e.lower() for e in result), f"7: non-string key rejected (got {result})")

# 8. Keys starting with _ are allowed
result = scaffold.validate_preset({"_schema_hash": "abc12345", "_subcommand": "push"})
check(result == [], f"8: underscore meta keys pass (got {result})")

# 9. Absurdly long key fails
long_key = "x" * 10_001
result = scaffold.validate_preset({long_key: "val"})
check(any("too long" in e.lower() for e in result), f"9: long key rejected (got {result})")


# =====================================================================
print("\n=== Preset Validation: Value Type Checks ===")
# =====================================================================

# 10. Nested dict value fails
result = scaffold.validate_preset({"key": {"nested": "dict"}})
check(any("unsupported type" in e.lower() for e in result), f"10: nested dict rejected (got {result})")

# 11. List of strings passes (multi_enum)
result = scaffold.validate_preset({"__global__:--tags": ["a", "b", "c"]})
check(result == [], f"11: list of strings passes (got {result})")

# 12. List of ints fails
result = scaffold.validate_preset({"key": [1, 2, 3]})
check(any("must be a string" in e.lower() for e in result), f"12: list of ints rejected (got {result})")

# 13. List with mixed types fails
result = scaffold.validate_preset({"key": ["ok", 42]})
check(any("must be a string" in e.lower() for e in result), f"13: mixed list rejected (got {result})")

# 14. Absurdly long string value fails
long_val = "x" * 10_001
result = scaffold.validate_preset({"key": long_val})
check(any("too long" in e.lower() for e in result), f"14: long value rejected (got {result})")

# 15. None value is allowed
result = scaffold.validate_preset({"key": None})
check(result == [], f"15: None value passes (got {result})")

# 16. Int value is allowed
result = scaffold.validate_preset({"key": 42})
check(result == [], f"16: int value passes (got {result})")

# 17. Float value is allowed
result = scaffold.validate_preset({"key": 3.14})
check(result == [], f"17: float value passes (got {result})")

# 18. Bool value is allowed
result = scaffold.validate_preset({"key": True})
check(result == [], f"18: bool value passes (got {result})")


# =====================================================================
print("\n=== Preset Validation: Schema-as-Preset Detection ===")
# =====================================================================

# 19. Dict that looks like a schema warns
result = scaffold.validate_preset({"binary": "nmap", "arguments": [{"name": "x"}]})
check(any("tool schema" in e.lower() for e in result), f"19: schema-as-preset detected (got {result})")

# 20. Dict with only "binary" is fine (could be a valid preset key)
result = scaffold.validate_preset({"binary": "nmap"})
check(not any("tool schema" in e.lower() for e in result), f"20: only-binary key is fine (got {result})")


# =====================================================================
print("\n=== Preset Validation: tool_data Cross-Check ===")
# =====================================================================

tool_data = {
    "tool": "test",
    "binary": "test",
    "description": "test",
    "arguments": [
        {"name": "verbose", "flag": "--verbose", "type": "boolean"},
        {"name": "output", "flag": "--output", "type": "string"},
    ],
}

# 21. Valid keys matching schema pass
result = scaffold.validate_preset(
    {"__global__:--verbose": True, "__global__:--output": "/tmp"},
    tool_data=tool_data,
)
check(result == [], f"21: matching keys pass with tool_data (got {result})")

# 22. Unknown keys produce warning
result = scaffold.validate_preset(
    {"__global__:--verbose": True, "__global__:--nonexistent": "x"},
    tool_data=tool_data,
)
check(any("unknown" in e.lower() for e in result), f"22: unknown key warned (got {result})")

# 23. Meta keys are not flagged as unknown
result = scaffold.validate_preset(
    {"_schema_hash": "abc12345", "__global__:--verbose": True},
    tool_data=tool_data,
)
check(result == [], f"23: meta keys not flagged as unknown (got {result})")


# =====================================================================
# Final results
# =====================================================================
print(f"\n{'='*60}")
print(f"PRESET VALIDATION TEST RESULTS: {passed}/{passed+failed} passed, {failed} failed")
if errors:
    print(f"\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)
