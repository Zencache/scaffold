"""
Diagnostic 4 — CascadeListDialog row/sort desync
Measures whether visual row indices match self._cascades indices after sorting.
Does NOT modify scaffold.py.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

import scaffold

# ---------------------------------------------------------------------------
# 1. Create 3 cascade files with names/steps/mtimes that sort differently
#
#    Name order (alpha asc): alpha < beta < gamma
#    Step counts:            alpha=1, beta=5, gamma=3
#    Mtimes:                 alpha=oldest, beta=middle, gamma=newest
#
#    After Name asc sort:    alpha(1), beta(5), gamma(3)
#      => _cascades = [alpha, beta, gamma]  (set during _populate)
#
#    After Steps desc sort:  beta(5), gamma(3), alpha(1)
#      => visual row 0 = Beta, but _cascades[0] = alpha  --> DESYNC
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="diag_cascade_")

cascades_info = [
    # alpha: 1 step — will sort to BOTTOM by steps desc
    ("alpha.cascade.json", {
        "_format": "scaffold_cascade", "name": "Alpha Cascade",
        "description": "First", "steps": [{"s": 0}],
    }),
    # beta: 5 steps — will sort to TOP by steps desc
    ("beta.cascade.json", {
        "_format": "scaffold_cascade", "name": "Beta Cascade",
        "description": "Second", "steps": [{"s": i} for i in range(5)],
    }),
    # gamma: 3 steps — will sort to MIDDLE by steps desc
    ("gamma.cascade.json", {
        "_format": "scaffold_cascade", "name": "Gamma Cascade",
        "description": "Third", "steps": [{"s": i} for i in range(3)],
    }),
]

for fname, data in cascades_info:
    p = Path(tmpdir) / fname
    p.write_text(json.dumps(data), encoding="utf-8")

# Set mtimes: alpha oldest, beta middle, gamma newest
time.sleep(0.05)
base_time = time.time()
os.utime(Path(tmpdir) / "alpha.cascade.json", (base_time - 200, base_time - 200))
os.utime(Path(tmpdir) / "beta.cascade.json",  (base_time - 100, base_time - 100))
os.utime(Path(tmpdir) / "gamma.cascade.json", (base_time,       base_time))

# ---------------------------------------------------------------------------
# 2. Patch _cascades_dir to point at our temp directory
# ---------------------------------------------------------------------------
original_cascades_dir = scaffold._cascades_dir

def patched_cascades_dir() -> Path:
    return Path(tmpdir)

scaffold._cascades_dir = patched_cascades_dir

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
passed = 0
failed = 0

def visual_order(table):
    """Return list of (row_idx, col0_name, col2_steps) for all visual rows."""
    rows = []
    for r in range(table.rowCount()):
        name_item = table.item(r, 0)
        steps_item = table.item(r, 2)
        name = name_item.text() if name_item else "?"
        steps = steps_item.data(Qt.ItemDataRole.DisplayRole) if steps_item else "?"
        rows.append((r, name, steps))
    return rows

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")
    if detail:
        print(f"         {detail}")

def name_from_path(p):
    """Extract cascade name prefix from a Path (e.g. 'alpha' from 'alpha.cascade.json')."""
    return p.stem.split(".")[0]

# ---------------------------------------------------------------------------
# 3. Construct dialog and inspect initial state
# ---------------------------------------------------------------------------
print("=" * 70)
print("DIAGNOSTIC 4: CascadeListDialog row/sort desync")
print("=" * 70)

dlg = scaffold.CascadeListDialog(mode="load")

# Stub accept() so double-click / action don't close the dialog
original_accept = dlg.accept
dlg.accept = lambda: None

print("\n--- Initial state (after _populate, sorted by Name asc) ---")
print("self._cascades backing list:")
for i, p in enumerate(dlg._cascades):
    print(f"  [{i}] {p.name}")

print("\nVisual table order (via table.item(row, col)):")
for row, name, steps in visual_order(dlg.table):
    print(f"  visual row {row}: name={name!r}, steps={steps}")

# Verify initial sync: after name-asc sort, visual and backing should agree
print("\nInitial sync check (Name asc — should all match):")
for i, p in enumerate(dlg._cascades):
    vis_name = dlg.table.item(i, 0).text()
    matches = name_from_path(p) in vis_name.lower()
    check(f"row {i} synced initially",
          matches,
          f"_cascades[{i}]={p.name}, visual={vis_name}")

# ---------------------------------------------------------------------------
# 4. Sort by Steps descending
#    Expected visual: Beta(5), Gamma(3), Alpha(1)
#    _cascades stays: [alpha, beta, gamma]
# ---------------------------------------------------------------------------
print("\n--- After sorting by Steps (col 2) DESCENDING ---")
dlg.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)

print("self._cascades backing list (UNCHANGED):")
for i, p in enumerate(dlg._cascades):
    print(f"  [{i}] {p.name}")

vis = visual_order(dlg.table)
print("\nVisual table order:")
for row, name, steps in vis:
    print(f"  visual row {row}: name={name!r}, steps={steps}")

# ---------------------------------------------------------------------------
# 5. Test _on_double_click on ALL visual rows
# ---------------------------------------------------------------------------
print("\n--- Simulate _on_double_click on each visual row ---")
for test_row in range(dlg.table.rowCount()):
    dlg.selected_path = None
    idx = dlg.table.model().index(test_row, 0)
    vis_name = dlg.table.item(test_row, 0).text()

    dlg._on_double_click(idx)

    if dlg.selected_path:
        sel_prefix = name_from_path(Path(dlg.selected_path))
    else:
        sel_prefix = "None"

    expected_prefix = vis_name.split()[0].lower()  # "Beta Cascade" -> "beta"
    match = sel_prefix == expected_prefix

    print(f"\n  Visual row {test_row}: displays {vis_name!r}")
    print(f"    index.row() = {idx.row()}")
    print(f"    _cascades[{idx.row()}] = {dlg._cascades[idx.row()].name}")
    print(f"    selected_path points to: {sel_prefix}")
    check(f"double-click row {test_row} selects displayed cascade",
          match,
          f"selected={sel_prefix}, expected={expected_prefix}")

# ---------------------------------------------------------------------------
# 6. Test _on_action (Open button) on each visual row
# ---------------------------------------------------------------------------
print("\n--- Simulate _on_action on each visual row ---")
for test_row in range(dlg.table.rowCount()):
    dlg.selected_path = None
    dlg.table.selectRow(test_row)
    sel_rows = dlg.table.selectionModel().selectedRows()
    row_idx = sel_rows[0].row()
    vis_name = dlg.table.item(test_row, 0).text()

    dlg._on_action()

    if dlg.selected_path:
        sel_prefix = name_from_path(Path(dlg.selected_path))
    else:
        sel_prefix = "None"

    expected_prefix = vis_name.split()[0].lower()
    match = sel_prefix == expected_prefix

    print(f"\n  Visual row {test_row}: displays {vis_name!r}")
    print(f"    selectionModel row = {row_idx}")
    print(f"    _cascades[{row_idx}] = {dlg._cascades[row_idx].name}")
    print(f"    selected_path points to: {sel_prefix}")
    check(f"_on_action row {test_row} selects displayed cascade",
          match,
          f"selected={sel_prefix}, expected={expected_prefix}")

# ---------------------------------------------------------------------------
# 7. Test _on_delete target resolution on each visual row
#    (don't actually delete — just inspect which path would be targeted)
# ---------------------------------------------------------------------------
print("\n--- Inspect _on_delete target for each visual row ---")
for test_row in range(dlg.table.rowCount()):
    dlg.table.selectRow(test_row)
    sel_rows = dlg.table.selectionModel().selectedRows()
    row_idx = sel_rows[0].row()
    vis_name = dlg.table.item(test_row, 0).text()
    target = dlg._cascades[row_idx] if 0 <= row_idx < len(dlg._cascades) else None

    if target:
        target_prefix = name_from_path(target)
    else:
        target_prefix = "None"

    expected_prefix = vis_name.split()[0].lower()
    match = target_prefix == expected_prefix

    print(f"\n  Visual row {test_row}: displays {vis_name!r}")
    print(f"    selectionModel row = {row_idx}")
    print(f"    _cascades[{row_idx}] = {target.name if target else None}")
    check(f"_on_delete row {test_row} targets displayed cascade",
          match,
          f"target={target_prefix}, expected={expected_prefix}")

# ---------------------------------------------------------------------------
# 8. Q3: Does table.item(row, col) reflect visual or logical order?
# ---------------------------------------------------------------------------
print("\n--- Q3: Does table.item(row, col) reflect visual or logical order? ---")
print("  Reading all rows via table.item(row, 0).text() after Steps desc sort:")
item_texts = []
for r in range(dlg.table.rowCount()):
    it = dlg.table.item(r, 0)
    item_texts.append(it.text() if it else "?")
    print(f"    row {r}: {it.text() if it else '?'}")

print(f"  Expected visual order (Steps desc): Beta(5), Gamma(3), Alpha(1)")
print(f"  Actual via item():  {', '.join(item_texts)}")
items_match_visual = (
    "Beta" in item_texts[0] and
    "Gamma" in item_texts[1] and
    "Alpha" in item_texts[2]
)
check("table.item() returns items in visual (sorted) order", items_match_visual)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 70)

if failed > 0:
    print("\nCONCLUSION: Row/sort desync CONFIRMED.")
    print("After re-sorting, _on_double_click / _on_action / _on_delete use")
    print("the visual row index to index into self._cascades, which retains")
    print("the original insertion order. This causes the wrong cascade to be")
    print("selected/opened/deleted when the table is sorted by any column")
    print("that changes the visual row order.")
else:
    print("\nCONCLUSION: No desync detected (QTableWidget may physically")
    print("rearrange items, keeping row indices in sync).")

# Cleanup
dlg.accept = original_accept
dlg.close()
scaffold._cascades_dir = original_cascades_dir

import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

sys.exit(0 if failed == 0 else 1)
