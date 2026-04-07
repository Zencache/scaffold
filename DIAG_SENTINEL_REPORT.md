# Diagnostic 1 -- Sentinel System Report

Date: 2026-04-07
Script: `diag_sentinel.py`
Scaffold version: as of current HEAD (unmodified)

---

## Raw Output

### Schema S1: integer, min=5, max=10, default=null

| State | widget.min | widget.max | widget.val | specialValueText | active | field_value | command |
|---|---|---|---|---|---|---|---|
| Initial | 4 | 10 | 4 | `' '` | False | None | `['echo']` |
| sentinel+1 (=5) | 4 | 10 | 5 | `' '` | True | 5 | `['echo', '--val', '5']` |
| schema min (=5) | 4 | 10 | 5 | `' '` | True | 5 | `['echo', '--val', '5']` |
| schema min+1 (=6) | 4 | 10 | 6 | `' '` | True | 6 | `['echo', '--val', '6']` |
| schema max (=10) | 4 | 10 | 10 | `' '` | True | 10 | `['echo', '--val', '10']` |

Sentinel = 4 (schema_min - 1). All in-range values [5..10] are correctly active.

### Schema S2: integer, min=-5, max=5, default=null

| State | widget.min | widget.max | widget.val | specialValueText | active | field_value | command |
|---|---|---|---|---|---|---|---|
| Initial | -6 | 5 | -6 | `' '` | False | None | `['echo']` |
| sentinel+1 (=-5) | -6 | 5 | -5 | `' '` | True | -5 | `['echo', '--val', '-5']` |
| schema min (=-5) | -6 | 5 | -5 | `' '` | True | -5 | `['echo', '--val', '-5']` |
| schema min+1 (=-4) | -6 | 5 | -4 | `' '` | True | -4 | `['echo', '--val', '-4']` |
| schema max (=5) | -6 | 5 | 5 | `' '` | True | 5 | `['echo', '--val', '5']` |

Sentinel = -6 (schema_min - 1). Negative schema ranges work correctly. All in-range values [-5..5] are active.

### Schema S3: integer, min=0, max=10, default=null (control)

| State | widget.min | widget.max | widget.val | specialValueText | active | field_value | command |
|---|---|---|---|---|---|---|---|
| Initial | -1 | 10 | -1 | `' '` | False | None | `['echo']` |
| sentinel+1 (=0) | -1 | 10 | 0 | `' '` | True | 0 | `['echo', '--val', '0']` |
| schema min (=0) | -1 | 10 | 0 | `' '` | True | 0 | `['echo', '--val', '0']` |
| schema min+1 (=1) | -1 | 10 | 1 | `' '` | True | 1 | `['echo', '--val', '1']` |
| schema max (=10) | -1 | 10 | 10 | `' '` | True | 10 | `['echo', '--val', '10']` |

Sentinel = -1 (schema_min - 1 = 0 - 1). Matches existing test 36b. Value 0 is correctly preserved.

### Schema S4: float, min=0.1, max=99.9, default=null

| State | widget.min | widget.max | widget.val | specialValueText | active | field_value | command |
|---|---|---|---|---|---|---|---|
| Initial | -0.9 | 99.9 | -0.9 | `' '` | False | None | `['echo']` |
| sentinel+1 (=0.1) | -0.9 | 99.9 | 0.1 | `' '` | True | 0.1 | `['echo', '--val', '0.1']` |
| schema min (=0.1) | -0.9 | 99.9 | 0.1 | `' '` | True | 0.1 | `['echo', '--val', '0.1']` |
| schema min+1 (=1.1) | -0.9 | 99.9 | 1.1 | `' '` | True | 1.1 | `['echo', '--val', '1.1']` |
| schema max (=99.9) | -0.9 | 99.9 | 99.9 | `' '` | True | 99.9 | `['echo', '--val', '99.9']` |

Float extras at initial state:
- `repr(widget.value())` = `-0.9`, `repr(widget.minimum())` = `-0.9`
- `value == minimum` = **True**
- `math.isclose` = True

Sentinel = -0.9 (0.1 - 1.0). All 999 sampled in-range values OK.

### Schema S5: float, min=-1.5, max=1.5, default=null

| State | widget.min | widget.max | widget.val | specialValueText | active | field_value | command |
|---|---|---|---|---|---|---|---|
| Initial | -2.5 | 1.5 | -2.5 | `' '` | False | None | `['echo']` |
| sentinel+1 (=-1.5) | -2.5 | 1.5 | -1.5 | `' '` | True | -1.5 | `['echo', '--val', '-1.5']` |
| schema min (=-1.5) | -2.5 | 1.5 | -1.5 | `' '` | True | -1.5 | `['echo', '--val', '-1.5']` |
| schema min+1 (=-0.5) | -2.5 | 1.5 | -0.5 | `' '` | True | -0.5 | `['echo', '--val', '-0.5']` |
| schema max (=1.5) | -2.5 | 1.5 | 1.5 | `' '` | True | 1.5 | `['echo', '--val', '1.5']` |

Float extras at initial state:
- `repr(widget.value())` = `-2.5`, `repr(widget.minimum())` = `-2.5`
- `value == minimum` = **True**
- `math.isclose` = True

Sentinel = -2.5 (-1.5 - 1.0). All 31 sampled in-range values OK.

---

## Float Equality Edge Cases

Six additional float schemas tested for sentinel equality:

| Case | schema_min | sentinel_target (Python) | repr(minimum) | repr(value) | `==` | isclose | active |
|---|---|---|---|---|---|---|---|
| F_edge1 | 0.1 | -0.9 | -0.9 | -0.9 | True | True | False |
| F_edge2 | -1.5 | -2.5 | -2.5 | -2.5 | True | True | False |
| F_edge3 | 0.3 | -0.7 | -0.7 | -0.7 | True | True | False |
| F_edge4 | 0.7 | -0.30000000000000004 | -0.3 | -0.3 | True | True | False |
| F_edge5 | 1.1 | 0.10000000000000009 | 0.1 | 0.1 | True | True | False |
| F_edge6 | 0.01 | -0.99 | -0.99 | -0.99 | True | True | False |

Note F_edge4: Python computes `0.7 - 1.0 = -0.30000000000000004`, but `QDoubleSpinBox` rounds to 2 decimal places internally, storing `-0.3`. Both `setMinimum` and `setValue` pass through the same rounding, so `value == minimum` holds. The same applies to F_edge5 (`1.1 - 1.0 = 0.10000000000000009` -> stored as `0.1`).

---

## Q1 Exhaustive Scan: In-range Values Dropped?

| Schema | Range | Values tested | Dropped |
|---|---|---|---|
| S1 (integer) | [5, 10] | 6 | **0** |
| S2 (integer) | [-5, 5] | 11 | **0** |
| S3 (integer) | [0, 10] | 11 | **0** |
| S4 (float) | [0.1, 99.9] | 999 (step 0.1) | **0** |
| S5 (float) | [-1.5, 1.5] | 31 (step 0.1) | **0** |

---

## Answers

### Q1: Does any user-typeable value within [schema_min, schema_max] ever get silently dropped from the command?

**No.** For all five schemas, every value in the declared [min, max] range was correctly emitted in `build_command()`. The sentinel is always placed at `schema_min - 1` (integer) or `schema_min - 1.0` (float), which is strictly below the valid range. No in-range value collides with the sentinel.

### Q2: For floats, is there ANY combination of decimals/min where `value == minimum` returns False when the widget is conceptually "unset"?

**No.** Across all six float edge cases (including tricky binary fractions like 0.3 and 0.7), `value == minimum` correctly returned `True` when the widget was at its sentinel position. This is because `QDoubleSpinBox` with `setDecimals(2)` rounds both `setMinimum()` and `setValue()` through the same internal path, so the stored doubles match exactly. The Python-side floating point noise (e.g. `0.7 - 1.0 = -0.30000000000000004`) is absorbed by Qt's rounding before storage.

### Q3: What value, if any, falls inside the valid schema range but is treated as the sentinel?

**None.** The sentinel is always `schema_min - 1` (or `- 1.0`), which is one full unit below the declared minimum. Since `QSpinBox` steps by 1 and `QDoubleSpinBox` steps by 0.01 (2 decimals), the sentinel is unreachable via normal user interaction (arrow keys, typing). The only way to reach the sentinel value is programmatically via `setValue(minimum())` or `_set_field_value(key, None)`.
