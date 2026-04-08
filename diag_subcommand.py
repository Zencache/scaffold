"""Diagnostic: test subcommand name handling in validate_tool and build_command.

DIAGNOSTIC ONLY — does not modify scaffold.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
import scaffold

app = QApplication(sys.argv)

# --- Test names ---------------------------------------------------------------

NAMES = {
    "N1": "list",
    "N2": "remote add",
    "N3": "list --recursive",
    "N4": "list -r",
    "N5": "--rm container",
    "N6": "list; rm -rf /",
    "N7": "list\nrm",
    "N8": " list",
}


def make_schema(sub_name):
    """Minimal valid schema with one subcommand using the given name."""
    return {
        "tool": "diag-subcmd",
        "binary": "mytool",
        "description": "diagnostic",
        "arguments": [],
        "subcommands": [
            {
                "name": sub_name,
                "arguments": [
                    {
                        "name": "Verbose",
                        "flag": "--verbose",
                        "type": "boolean",
                        "description": "verbose",
                    }
                ],
            }
        ],
    }


results = []

for tag, name in NAMES.items():
    schema = make_schema(name)

    # Step 1: validate
    errors = scaffold.validate_tool(schema)

    cmd_output = None
    split_tokens = None

    if not errors:
        # Step 2: normalize + build form + build command
        normalized = scaffold.normalize_tool(schema)
        form = scaffold.ToolForm(normalized)

        # The first (only) subcommand should be auto-selected
        current = form.get_current_subcommand()
        cmd_list, display = form.build_command()
        cmd_output = cmd_list
        split_tokens = name.split()

    results.append(
        {
            "tag": tag,
            "name": name,
            "validates": len(errors) == 0,
            "errors": errors,
            "cmd_output": cmd_output,
            "split_tokens": split_tokens,
        }
    )

# --- Print results ------------------------------------------------------------

print("=" * 80)
print("SUBCOMMAND NAME DIAGNOSTIC")
print("=" * 80)
print()

for r in results:
    safe_name = repr(r["name"])
    print(f"{r['tag']}: {safe_name}")
    print(f"  validates: {r['validates']}")
    if r["errors"]:
        for e in r["errors"]:
            print(f"  error: {e}")
    if r["cmd_output"] is not None:
        print(f"  cmd_output: {r['cmd_output']}")
        print(f"  split tokens from name: {r['split_tokens']}")
    print()

# --- Answer the three questions -----------------------------------------------

print("=" * 80)
print("ANSWERS")
print("=" * 80)
print()

passing = [r["tag"] for r in results if r["validates"]]
failing = [r["tag"] for r in results if not r["validates"]]
print(f"Q1: Which pass validation? {', '.join(passing)}")
print(f"    Which fail? {', '.join(failing)}")
print()

print("Q2: For names that pass, does .split() produce injected-looking tokens?")
for r in results:
    if r["validates"] and r["split_tokens"]:
        suspicious = [t for t in r["split_tokens"] if t.startswith("-")]
        if suspicious:
            print(f"  {r['tag']} {repr(r['name'])}: YES — split produces flag-like tokens: {suspicious}")
            print(f"    cmd_output = {r['cmd_output']}")
        else:
            print(f"  {r['tag']} {repr(r['name'])}: no flag-like tokens in split")
print()

# Check if newline is in _SHELL_METACHAR
metachar_set = scaffold._SHELL_METACHAR
print(f"Q3: Does _SHELL_METACHAR contain newline (\\n)? {'\\n' in metachar_set}")
print(f"    _SHELL_METACHAR = {sorted(metachar_set)}")
print(f"    Note: subcommand name validation does NOT use _SHELL_METACHAR —")
print(f"    that check is only applied to the \"binary\" field (line ~161).")
print(f"    Subcommand names are only checked for: empty, leading/trailing whitespace, double spaces.")
