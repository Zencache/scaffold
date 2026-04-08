# Cascade Panel — Layout Diagnostic Report

## Bug 1: Run/Stop/Clear buttons don't follow the cascade panel height

### Full Layout Hierarchy

```
CascadeSidebar (QDockWidget)
  └─ content (QWidget, setFixedWidth=220)
     └─ content_layout (QVBoxLayout, margins=6,6,6,6, spacing=4)
        ├─ item[0]: header_row (QHBoxLayout, stretch=0)
        │   ├─ header_label (QLabel, "Cascade", bold)
        │   └─ stretch
        ├─ item[1]: scroll_area (QScrollArea, stretch=1)           ← TAKES ALL REMAINING SPACE
        │   properties: widgetResizable=True, hScrollBar=AlwaysOff,
        │               frameShape=NoFrame, sizePolicy=(Expanding, Expanding)
        │   └─ scroll_widget (QWidget)
        │       └─ _slots_container (QVBoxLayout, margins=0, spacing=2)
        │           ├─ slot_widget[0] (QWidget)
        │           │   └─ slot_layout (QVBoxLayout)
        │           │       ├─ row1 (QHBoxLayout): num_label + main_btn + arrow_btn + remove_btn
        │           │       └─ delay_row (QHBoxLayout): stretch + delay_combo(fixedWidth=120) + stretch
        │           ├─ slot_widget[1] ...
        │           ├─ ... (up to CASCADE_MAX_SLOTS=20)
        │           ├─ add_step_btn (QPushButton, "+ Add Step")
        │           └─ stretch                                     ← PUSHES SLOTS TO TOP INSIDE SCROLL
        └─ item[2]: chain_bar (QHBoxLayout, stretch=0)             ← BUTTONS ARE OUTSIDE SCROLL AREA
            ├─ run_chain_btn (QPushButton, "Run")
            ├─ stop_chain_btn (QPushButton, "Stop")
            └─ clear_all_btn (QPushButton, "Clear")
```

### Key Findings

**The buttons ARE outside the scroll area** (line 3467: `content_layout.addLayout(chain_bar)`). They are the third item in `content_layout`, after the scroll area. The scroll area has `stretch=1` (line 3453: `content_layout.addWidget(scroll_area, 1)`) while the button bar has `stretch=0`. This means:

- **Buttons are pinned to the bottom of the content widget.** They do NOT scroll with the slots.
- **With many slots (tested with 17):** The scroll area scrolls internally (`scrollBar.maximum=758`), the buttons remain at the bottom at a fixed y-position. Buttons remain visible and accessible.
- **With few slots (2 default):** The scroll area expands to fill all available vertical space due to `stretch=1`. This creates **wasted empty space** inside the scroll viewport between the last slot/"+ Add Step" button and the bottom of the scroll area.

### Measured Metrics (2 slots, window 900x400)

| Metric | Value |
|--------|-------|
| Sidebar height | 346px |
| Content widget height | 322px |
| Scroll area height | 260px |
| Scroll area sizePolicy | (Expanding, Expanding) |
| Actual slot content height | ~118px |
| Wasted space inside scroll | ~142px |
| Button bar y-position | 290px |
| Button bar height | 26px |
| Buttons fully visible | Yes |

### Root Cause (line 3453)

```python
content_layout.addWidget(scroll_area, 1)  # stretch=1
```

The scroll area is given stretch factor 1 in the content_layout, so it **always expands to fill all vertical space** between the header row and the button bar. When few slots exist, this produces a large empty region inside the scroll viewport. The `addStretch()` inside `_slots_container` (line 3451) pushes slots to the top, making the gap appear at the bottom of the scroll area, directly above the button bar.

The buttons themselves are correctly positioned outside the scroll area and pinned to the bottom. They do not scroll away. The "wasted space" issue is cosmetic but real.

### Recommended Fix

Set a `maximumHeight` on the scroll area that tracks the actual content height (e.g., the scroll widget's `sizeHint().height()`), or replace the fixed `stretch=1` with a `QSizePolicy(Preferred, Preferred)` on the scroll area plus an `addStretch()` between the scroll area and the button bar in `content_layout`. This would let the scroll area shrink when content is short while still expanding when needed, with the stretch absorbing the remaining space between the scroll area and buttons.

---

## Bug 2: "Running..." text gets cut off on the left side of the Run button

### Layout Context

The three chain control buttons share the available width inside `chain_bar` (QHBoxLayout):

```
chain_bar (QHBoxLayout) — inside content (fixedWidth=220)
  ├─ run_chain_btn  — sizePolicy=(Minimum, Fixed), stretch=0, minimumWidth=0
  ├─ stop_chain_btn — sizePolicy=(Minimum, Fixed), stretch=0, minimumWidth=0
  └─ clear_all_btn  — sizePolicy=(Minimum, Fixed), stretch=0, minimumWidth=0
```

Available width = 220px (content fixedWidth) - 12px (content margins 6+6) = 208px.
Layout spacing default ~6px between items, so usable = 208 - 12 = ~196px / 3 buttons = ~65px each.

### Measured Metrics

| Metric | Value |
|--------|-------|
| Run button actual width | 67px |
| Run button minimumWidth | **0** (not set) |
| Run button sizeHint | 81x26 |
| Font advance for "Run" | 21px |
| Font advance for "Running..." | 54px |
| QPushButton padding (global QSS) | `4px 12px` = 24px horizontal |
| QPushButton border (global QSS) | 1px each side = 2px |
| **Width needed for "Running..."** | **54 + 24 + 2 = 80px** |
| **Width available** | **67px** |
| **Deficit** | **13px** |

### Root Cause (lines 3457, 3469, and 761-763)

Three factors combine:

1. **No `setMinimumWidth()` on `run_chain_btn`** (line 3457): The button has no minimum width to accommodate the longer "Running..." text. Compare to the main form's Run button (line 5005) which correctly does:
   ```python
   self.run_btn.setMinimumWidth(QFontMetrics(_run_font).horizontalAdvance("Stopping...") + 40)
   ```

2. **Fixed container width** (line 3469): `content.setFixedWidth(220)` constrains the total available space. With 3 buttons sharing ~196px of usable width, each gets ~65-67px.

3. **Global QPushButton padding** (lines 761-763): The theme stylesheet applies `padding: 4px 12px` to all QPushButtons, consuming 24px of each button's width for padding alone. This leaves only `67 - 24 - 2 = 41px` for text rendering, but "Running..." needs 54px.

The text is **centered** by default (no `text-align` override on these buttons, unlike the slot buttons which have `text-align: center` explicitly). Qt clips the text symmetrically when it overflows, causing the left side to be cut off.

No explicit `setStyleSheet`, `setFixedWidth`, or `setMinimumWidth` is called on any of the three chain control buttons.

### Recommended Fix

Add a `setMinimumWidth()` to `run_chain_btn` based on the font metrics of "Running..." (the longest text it displays), similar to how the main form's Run button handles it. This may require reducing the padding or using a compact layout for the three buttons — e.g., giving Run more stretch or using abbreviated text like "Run..." instead of "Running...".
