# Diagnostic 4 — CascadeListDialog Row/Sort Desync Report

**Date:** 2026-04-07
**File:** `scaffold.py` lines 3696–3873 (`CascadeListDialog`)
**Diagnostic script:** `diag_cascade_sort.py`
**Verdict:** BUG CONFIRMED — all three action methods are affected.

---

## Setup

Three cascade files created in a temp directory:

| File | Name | Steps | Mtime |
|------|------|-------|-------|
| alpha.cascade.json | Alpha Cascade | 1 | oldest |
| beta.cascade.json | Beta Cascade | 5 | middle |
| gamma.cascade.json | Gamma Cascade | 3 | newest |

These sort differently by name (alpha, beta, gamma), by steps descending (beta, gamma, alpha), and by date descending (gamma, beta, alpha).

---

## Initial State (Name Ascending — default)

**`self._cascades` backing list:**
```
[0] alpha.cascade.json
[1] beta.cascade.json
[2] gamma.cascade.json
```

**Visual table order (via `table.item(row, 0)`):**
```
row 0: Alpha Cascade  (1 step)
row 1: Beta Cascade   (5 steps)
row 2: Gamma Cascade  (3 steps)
```

All three rows are synced — visual row index matches `self._cascades` index. All checks PASS.

---

## After Sorting by Steps Descending

**`self._cascades` — UNCHANGED:**
```
[0] alpha.cascade.json
[1] beta.cascade.json
[2] gamma.cascade.json
```

**Visual table order — CHANGED:**
```
row 0: Beta Cascade   (5 steps)
row 1: Gamma Cascade  (3 steps)
row 2: Alpha Cascade  (1 step)
```

The visual order no longer matches the backing list order.

---

## Q1: `_on_double_click` — Does it open the visually displayed cascade?

**NO.** All three rows fail:

| Visual Row | Displays | `index.row()` | `_cascades[row]` | Selected | Correct? |
|------------|----------|---------------|-------------------|----------|----------|
| 0 | Beta Cascade | 0 | alpha.cascade.json | alpha | FAIL |
| 1 | Gamma Cascade | 1 | beta.cascade.json | beta | FAIL |
| 2 | Alpha Cascade | 2 | gamma.cascade.json | gamma | FAIL |

**Root cause:** `_on_double_click` (line 3817) uses `index.row()` directly as an index into `self._cascades`. After sorting, `QTableWidget` physically rearranges items (so `table.item(0,0)` returns the newly-sorted row 0), but `self._cascades` retains the original insertion order. The row index no longer maps to the same cascade.

---

## Q2: `_on_action` and `_on_delete` — Same bug?

**YES.** Both methods suffer the identical desync.

### `_on_action` (Open button, line 3824):

| Visual Row | Displays | `selectionModel` row | `_cascades[row]` | Selected | Correct? |
|------------|----------|----------------------|-------------------|----------|----------|
| 0 | Beta Cascade | 0 | alpha.cascade.json | alpha | FAIL |
| 1 | Gamma Cascade | 1 | beta.cascade.json | beta | FAIL |
| 2 | Alpha Cascade | 2 | gamma.cascade.json | gamma | FAIL |

### `_on_delete` (Delete button, line 3834):

| Visual Row | Displays | `selectionModel` row | Would delete | Correct? |
|------------|----------|----------------------|--------------|----------|
| 0 | Beta Cascade | 0 | alpha.cascade.json | FAIL |
| 1 | Gamma Cascade | 1 | beta.cascade.json | FAIL |
| 2 | Alpha Cascade | 2 | gamma.cascade.json | FAIL |

`_on_delete` is the most dangerous — it would silently delete the **wrong file** after the user confirms deletion of the cascade they see displayed.

---

## Q3: `table.item(row, col)` — Visual or Logical?

**Visual.** `QTableWidget.item(row, col)` returns items in the sorted (visual) order. After `sortByColumn(2, Descending)`:

```
table.item(0, 0).text() = "Beta Cascade"   (5 steps — correct top)
table.item(1, 0).text() = "Gamma Cascade"  (3 steps — correct middle)
table.item(2, 0).text() = "Alpha Cascade"  (1 step  — correct bottom)
```

This means `table.item()` and `selectionModel().selectedRows()` both return **visual** row indices, while `self._cascades` is indexed by **insertion** order. The fix would need to either:

1. Store the cascade path directly on each `QTableWidgetItem` (e.g., via `setData(Qt.UserRole, str(path))`) and retrieve it from the item rather than indexing into the list, or
2. Keep `self._cascades` in sync with the visual sort order (fragile), or
3. Disable user-initiated sorting (loses functionality).

Option 1 is the cleanest fix.

---

## Summary

| Check | Result |
|-------|--------|
| `_on_double_click` after sort | **FAIL** — opens wrong cascade |
| `_on_action` after sort | **FAIL** — opens wrong cascade |
| `_on_delete` after sort | **FAIL** — deletes wrong cascade |
| `table.item()` reflects visual order | PASS |
| Initial state (no re-sort) | PASS (3/3) |

**4 passed, 9 failed.** The desync affects every interaction method in `CascadeListDialog` once the user sorts by any column that changes the row order from the initial name-ascending default.
