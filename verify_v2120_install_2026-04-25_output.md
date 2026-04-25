# v2.12.0 — Local install verification (Phase 5)

Captured 2026-04-25. Documents the build + clean-venv install steps that
verify the pip-installable packaging works end-to-end. Companion to the
Phase 5 commit that adds `pyproject.toml`.

Platform: Windows 11 Pro (10.0.26200), Python 3.14.3, pip 25.3,
build 1.4.4. Tested in git-bash with PowerShell-launched venv.

---

## 1. Build wheel and sdist

Cleaned prior artifacts, then `python -m build` from the repo root.

```
$ rm -rf dist/ build/ *.egg-info scaffold_gui.egg-info
$ python -m pip install --user --upgrade build
Successfully installed build-1.4.4 pyproject_hooks-1.2.0
$ python -m build
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - setuptools>=68
  - wheel
* Getting build dependencies for sdist...
running egg_info
writing scaffold_gui.egg-info\PKG-INFO
writing dependency_links to scaffold_gui.egg-info\dependency_links.txt
writing entry points to scaffold_gui.egg-info\entry_points.txt
writing requirements to scaffold_gui.egg-info\requires.txt
writing top-level names to scaffold_gui.egg-info\top_level.txt
reading manifest file 'scaffold_gui.egg-info\SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'scaffold_gui.egg-info\SOURCES.txt'
* Building sdist...
* Building wheel from sdist
...
adding 'scaffold.py'
adding 'scaffold_data/CASCADE_LLM_GENERATION_GUIDE.md'
adding 'scaffold_data/PRESET_PROMPT.txt'
adding 'scaffold_data/SCHEMA_PROMPT.txt'
adding 'scaffold_data/__init__.py'
[... 53 default_presets/ json files ...]
[... 28 tools/ json files ...]
adding 'scaffold_gui-2.12.0.dist-info/licenses/LICENSE'
adding 'scaffold_gui-2.12.0.dist-info/METADATA'
adding 'scaffold_gui-2.12.0.dist-info/WHEEL'
adding 'scaffold_gui-2.12.0.dist-info/entry_points.txt'
adding 'scaffold_gui-2.12.0.dist-info/top_level.txt'
adding 'scaffold_gui-2.12.0.dist-info/RECORD'
removing build\bdist.win-amd64\wheel
Successfully built scaffold_gui-2.12.0.tar.gz and scaffold_gui-2.12.0-py3-none-any.whl
```

```
$ ls -la dist/
-rw-r--r-- 1 kev 197121 294421 Apr 25 17:10 scaffold_gui-2.12.0-py3-none-any.whl
-rw-r--r-- 1 kev 197121 290166 Apr 25 17:10 scaffold_gui-2.12.0.tar.gz
```

### Build warnings

setuptools emitted one `SetuptoolsDeprecationWarning` about
`project.license` as a TOML table:

> Please use a simple string containing a SPDX expression for
> `project.license`. ... By 2027-Feb-18, you need to update your
> project and remove deprecated calls or your builds will no longer
> be supported.

PolyForm Noncommercial 1.0.0 is not in the SPDX license list, so
keeping the `license = { file = "LICENSE" }` table form is the
correct choice today. Migration to the new `project.license-files`
form is a future task — well before the 2027 deadline.

## 2. Wheel contents (sanity check)

`python -m zipfile -l dist/scaffold_gui-2.12.0-py3-none-any.whl`

Top-level layout:

```
scaffold.py                                            489027
scaffold_data/__init__.py                                   0
scaffold_data/CASCADE_LLM_GENERATION_GUIDE.md           10095
scaffold_data/PRESET_PROMPT.txt                          5011
scaffold_data/SCHEMA_PROMPT.txt                         12846
scaffold_data/default_presets/<10 tool subdirs>/<53 .json files>
scaffold_data/tools/<28 .json files including ansible/, docker_test/>
scaffold_gui-2.12.0.dist-info/licenses/LICENSE
scaffold_gui-2.12.0.dist-info/METADATA
scaffold_gui-2.12.0.dist-info/WHEEL
scaffold_gui-2.12.0.dist-info/entry_points.txt          43
scaffold_gui-2.12.0.dist-info/top_level.txt             23
scaffold_gui-2.12.0.dist-info/RECORD
```

`entry_points.txt`:

```
[console_scripts]
scaffold = scaffold:main
```

`top_level.txt`:

```
scaffold
scaffold_data
```

All 28 bundled tool schemas (including `ansible/` and `docker_test/`
subdirs) and all 53 default_presets ship in the wheel.

## 3. Install into clean venv

```
$ python -m venv /tmp/scaffold-install-test
$ /tmp/scaffold-install-test/Scripts/python.exe -m pip install dist/scaffold_gui-2.12.0-py3-none-any.whl
Processing c:\claude\scaffold\dist\scaffold_gui-2.12.0-py3-none-any.whl
Collecting PySide6>=6.5 (from scaffold-gui==2.12.0)
  Using cached pyside6-6.11.0-cp310-abi3-win_amd64.whl.metadata (5.5 kB)
Collecting shiboken6==6.11.0 (from PySide6>=6.5->scaffold-gui==2.12.0)
Collecting PySide6_Essentials==6.11.0 (from PySide6>=6.5->scaffold-gui==2.12.0)
Collecting PySide6_Addons==6.11.0 (from PySide6>=6.5->scaffold-gui==2.12.0)
Installing collected packages: shiboken6, PySide6_Essentials, PySide6_Addons, PySide6, scaffold-gui
Successfully installed PySide6-6.11.0 PySide6_Addons-6.11.0 PySide6_Essentials-6.11.0 scaffold-gui-2.12.0 shiboken6-6.11.0
```

PySide6 6.11.0 was pulled in as the only transitive dependency.

## 4. Entry point

```
$ ls /tmp/scaffold-install-test/Scripts/scaffold*
/tmp/scaffold-install-test/Scripts/scaffold.exe
```

`scaffold.exe` lands on the venv's PATH (the Windows equivalent of
`scaffold` on Linux/macOS).

## 5. CLI smoke checks

### `scaffold --version`

```
$ /tmp/scaffold-install-test/Scripts/scaffold.exe --version
Scaffold 2.11.4
```

NOTE: Phase 5 leaves `__version__` at the previous release's value;
Phase 6 bumps it to `2.12.0`. The wheel filename and pip metadata
correctly carry `2.12.0` (from `pyproject.toml`); `scaffold --version`
reads the in-source `__version__` constant which Phase 6 will update.

### `scaffold --prompt` (reads bundled `SCHEMA_PROMPT.txt`)

```
$ /tmp/scaffold-install-test/Scripts/scaffold.exe --prompt | head -5
You are a CLI-to-JSON converter. Given a CLI tool's documentation, produce a single JSON object describing its interface.

Return ONLY raw JSON. No markdown fences, no explanation, no preamble, no trailing text. No comments in the JSON. No trailing commas. Use null for inapplicable fields — never empty string "", never omit a key.

=== TOP-LEVEL OBJECT ===
```

### `scaffold --preset-prompt` (reads bundled `PRESET_PROMPT.txt`)

```
$ /tmp/scaffold-install-test/Scripts/scaffold.exe --preset-prompt | head -5
You are a preset generator for Scaffold (https://github.com/Zencache/scaffold).

Scaffold turns CLI tools into GUI forms using JSON schemas. A PRESET is a saved
form configuration — a JSON file that maps argument flags to values, so a user
can load a complete setup with one click instead of filling in every field.
```

Both prompts resolve through `_bundled_root() / "<filename>"` and the
bundled-mode path resolution lands on the wheel's `scaffold_data/`
contents inside site-packages.

### `scaffold --help` (regression: portable mode mentioned)

```
$ /tmp/scaffold-install-test/Scripts/scaffold.exe --help
Scaffold 2.11.4 - CLI-to-GUI Translation Layer

Usage:
  python scaffold.py                        Launch the tool picker GUI
  python scaffold.py <tool.json>            Open a specific tool directly
  python scaffold.py --validate <tool.json> Validate a schema (no GUI)
  python scaffold.py --prompt               Print the LLM schema-generation prompt
  python scaffold.py --preset-prompt          Print the LLM preset-generation prompt
  python scaffold.py --version              Show version and exit
  python scaffold.py --help                 Show this help and exit

Portable mode:  Place portable.txt next to scaffold.py to store settings locally
```

## 6. Python introspection (critical sanity check)

Run from `/tmp` (so the source-tree `scaffold.py` doesn't shadow the
installed one):

```
$ cd /tmp && /tmp/scaffold-install-test/Scripts/python.exe -c \
    "from scaffold import _bundled_root, _user_data_root, _is_installed_mode; \
     print('installed_mode:', _is_installed_mode()); \
     print('bundled:', _bundled_root()); \
     print('user:', _user_data_root())"
installed_mode: True
bundled: C:\Users\kev\AppData\Local\Temp\scaffold-install-test\Lib\site-packages\scaffold_data
user: C:\Users\kev\AppData\Roaming\Scaffold
```

Matches the spec from Sessions 1-2:

| | Expected | Got |
|---|---|---|
| `installed_mode` | `True` | `True` |
| `bundled` | inside venv site-packages | `...\Lib\site-packages\scaffold_data` |
| `user` | `%APPDATA%\Scaffold` | `C:\Users\kev\AppData\Roaming\Scaffold` |

## 7. Surprise found and fixed during verification

The first verification run produced `user: C:\Users\kev\AppData\Roaming`
(missing the `\Scaffold` suffix). Root cause: `_user_data_root()` from
Sessions 1-2 used `QStandardPaths.AppDataLocation`, which only appends
`QCoreApplication.applicationName()` to the platform root if app name
has been set — and scaffold doesn't call `setApplicationName` at
startup. So both the introspection check (no QApplication at all) and
the actual GUI process (QApplication created with default name) would
end up writing presets/cascades into the bare `%APPDATA%` (Roaming)
directory rather than the documented `%APPDATA%\Scaffold\`.

Fixed in `scaffold.py:_user_data_root`: append `"Scaffold"` ourselves
when the resolved path doesn't already end in it. Idempotent — if a
future change ever does call `setApplicationName("Scaffold")`, the
suffix is detected and not duplicated.

The fix is small (3-line conditional), shipped in this Phase 5 commit
alongside `pyproject.toml`. Source-mode behavior is unchanged (the
`_is_installed_mode()` branch is the only one that needed a fix), so
existing §205 tests stay passing without modification.

## 8. Pip metadata

```
$ /tmp/scaffold-install-test/Scripts/python.exe -m pip show scaffold-gui
Name: scaffold-gui
Version: 2.12.0
Summary: Schema-driven GUI generator for any CLI tool
Home-page: https://github.com/Zencache/scaffold
Author: Kev
License: # PolyForm Noncommercial License 1.0.0
        ...
Location: C:\Users\kev\AppData\Local\Temp\scaffold-install-test\Lib\site-packages
Requires: PySide6
Required-by:
```

Wheel name, version, and `Requires: PySide6` all correct.

## 9. Cleanup

```
$ rm -rf /tmp/scaffold-install-test dist/ build/ *.egg-info scaffold_gui.egg-info
$ rm -rf /c/Users/kev/AppData/Roaming/Scaffold   # introspection artifact
```

---

## Verdict

`pip install dist/scaffold_gui-2.12.0-py3-none-any.whl` produces a
working `scaffold` command in a clean venv. Bundled data ships in the
wheel, the entry point is registered, the path-resolution layer
correctly distinguishes installed mode (site-packages bundled root +
platform AppData user root) from source mode, and `--prompt` /
`--preset-prompt` find their bundled files via the new resolution.

One latent bug from Sessions 1-2 (`_user_data_root` not appending
`Scaffold` to the platform root) was caught and fixed.
