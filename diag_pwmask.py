"""Diagnostic: _mask_passwords_for_display behaviour with overlapping flag names.

DIAGNOSTIC ONLY — does NOT modify scaffold.py.
Builds ToolForm instances, sets values, and reports raw vs masked command output.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent))
import scaffold

app = QApplication.instance() or QApplication(sys.argv)

GLOBAL = scaffold.ToolForm.GLOBAL

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def make_schema(name, arguments):
    return {
        "tool": name,
        "binary": name,
        "description": f"Test schema {name}",
        "arguments": arguments,
    }


def arg(name, flag, typ, separator="space", **kw):
    a = {"name": name, "flag": flag, "type": typ, "separator": separator}
    a.update(kw)
    return a


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

scenarios = {}

# P1: --pass (password, none) + --passive (string, space)
scenarios["P1"] = {
    "schema": make_schema("p1tool", [
        arg("Pass", "--pass", "password", separator="none"),
        arg("Passive", "--passive", "string", separator="space"),
    ]),
    "values": {
        (GLOBAL, "--pass"): "secret123",
        (GLOBAL, "--passive"): "mode",
    },
    "passwords": {"secret123"},
    "non_password_tokens": {"--passive", "mode"},
}

# P2: --pass (password, space) + --password (string, space)
scenarios["P2"] = {
    "schema": make_schema("p2tool", [
        arg("Pass", "--pass", "password", separator="space"),
        arg("Password", "--password", "string", separator="space"),
    ]),
    "values": {
        (GLOBAL, "--pass"): "secret123",
        (GLOBAL, "--password"): "hint",
    },
    "passwords": {"secret123"},
    "non_password_tokens": {"--password", "hint"},
}

# P3: --p (password, none) + --port (integer, space)
scenarios["P3"] = {
    "schema": make_schema("p3tool", [
        arg("P", "--p", "password", separator="none"),
        arg("Port", "--port", "integer", separator="space"),
    ]),
    "values": {
        (GLOBAL, "--p"): "x",
        (GLOBAL, "--port"): 8080,
    },
    "passwords": {"x"},
    "non_password_tokens": {"--port", "8080"},
}

# P4: --pw (password, equals) + --pwfile (file, equals)
scenarios["P4"] = {
    "schema": make_schema("p4tool", [
        arg("Pw", "--pw", "password", separator="equals"),
        arg("Pwfile", "--pwfile", "file", separator="equals"),
    ]),
    "values": {
        (GLOBAL, "--pw"): "x",
        (GLOBAL, "--pwfile"): "/tmp/file",
    },
    "passwords": {"x"},
    "non_password_tokens": {"--pwfile=/tmp/file"},
}

# P5: Single --pass (separator=none) value "secret" — control
scenarios["P5"] = {
    "schema": make_schema("p5tool", [
        arg("Pass", "--pass", "password", separator="none"),
    ]),
    "values": {
        (GLOBAL, "--pass"): "secret",
    },
    "passwords": {"secret"},
    "non_password_tokens": set(),
}

# ---------------------------------------------------------------------------
# Run scenarios
# ---------------------------------------------------------------------------

results = {}

for label, s in scenarios.items():
    form = scaffold.ToolForm(s["schema"])

    for key, val in s["values"].items():
        form._set_field_value(key, val)

    cmd, display = form.build_command()
    masked = form._mask_passwords_for_display(cmd)

    # Check (c): Does any password value appear in masked output?
    password_leaked = False
    leaked_details = []
    for pw in s["passwords"]:
        for i, token in enumerate(masked):
            if pw in token and token != "********" and not token.endswith("********"):
                password_leaked = True
                leaked_details.append(f"password {pw!r} found in masked token [{i}] {token!r}")
            # Also check: separator=none token where value is embedded
            # e.g. "--passsecret123" should become "--pass********"
            # If token contains password but also contains flag prefix + ********,
            # that's correct masking, not a leak.

    # More precise leak check: look for literal password value in the joined
    # masked string, but only where it is NOT preceded by the flag name.
    for pw in s["passwords"]:
        for token in masked:
            if pw in token:
                # It's a leak if the token isn't just "********" and doesn't
                # end with "********" (which would indicate proper masking)
                if "********" not in token:
                    password_leaked = True
                    if f"password {pw!r}" not in str(leaked_details):
                        leaked_details.append(
                            f"password {pw!r} appears unmasked in token {token!r}"
                        )

    # Check (d): Is any non-password value incorrectly masked?
    incorrect_mask = False
    incorrect_details = []
    for npt in s["non_password_tokens"]:
        # Check if this non-password token has been replaced or disappeared
        found_intact = False
        for token in masked:
            if npt == token or (npt in token and "********" not in token):
                found_intact = True
                break
        if not found_intact:
            # Token was either removed or masked
            incorrect_mask = True
            incorrect_details.append(f"non-password token {npt!r} missing or masked in output")

    results[label] = {
        "cmd": cmd,
        "masked": masked,
        "password_leaked": password_leaked,
        "leaked_details": leaked_details,
        "incorrect_mask": incorrect_mask,
        "incorrect_details": incorrect_details,
    }

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------

print("=" * 72)
print("DIAGNOSTIC: _mask_passwords_for_display with overlapping flag names")
print("=" * 72)

for label in sorted(results):
    r = results[label]
    print(f"\n{'-' * 72}")
    print(f"  {label}")
    print(f"{'-' * 72}")
    print(f"  Raw cmd:    {r['cmd']}")
    print(f"  Masked cmd: {r['masked']}")
    print(f"  (c) Password leaked?          {'YES — ' + '; '.join(r['leaked_details']) if r['password_leaked'] else 'No'}")
    print(f"  (d) Non-password incorrectly  {'YES — ' + '; '.join(r['incorrect_details']) if r['incorrect_mask'] else 'No'}")
    print(f"      masked?")

print(f"\n{'=' * 72}")
print("SUMMARY ANSWERS")
print(f"{'=' * 72}")

any_leak = any(r["password_leaked"] for r in results.values())
any_incorrect = any(r["incorrect_mask"] for r in results.values())

print(f"\n  Q1: Does any password value leak through masking in P1-P4?")
print(f"      {'YES' if any_leak else 'No'}")
for label in ["P1", "P2", "P3", "P4"]:
    r = results[label]
    if r["password_leaked"]:
        for d in r["leaked_details"]:
            print(f"        {label}: {d}")

print(f"\n  Q2: Does any non-password token get incorrectly replaced with ********?")
print(f"      {'YES' if any_incorrect else 'No'}")
for label in sorted(results):
    r = results[label]
    if r["incorrect_mask"]:
        for d in r["incorrect_details"]:
            print(f"        {label}: {d}")

# Q3: For separator=none, check if prefix-only match at line 2121 is triggered
# on a non-password flag
print(f"\n  Q3: For separator=none, is the prefix-only check at line 2121")
print(f"      actually triggerable with realistic flag pairs?")
# P1 (--pass/--passive) and P3 (--p/--port) are the test cases
p1_hit = results["P1"]["incorrect_mask"]
p3_hit = results["P3"]["incorrect_mask"]
if p1_hit or p3_hit:
    print(f"      YES -- the prefix check causes false positives:")
    if p1_hit:
        print(f"        P1: --passive starts with --pass -> incorrectly masked")
    if p3_hit:
        print(f"        P3: --port starts with --p -> incorrectly masked")
else:
    print(f"      No — prefix check did not cause false positives in tested cases")

print()
