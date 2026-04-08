#!/usr/bin/env python3
"""Cascade Panel Visual Diagnostic — measurement-only, changes nothing."""

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QScrollArea, QPushButton, QLabel
from PySide6.QtGui import QPalette, QFontMetrics
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

import scaffold
from pathlib import Path

# Locate a tool + preset for slot assignment
tools_dir = Path(__file__).parent / "tools"
tests_dir = Path(__file__).parent / "tests"
tool_path = None
preset_path = None
for f in sorted(tools_dir.glob("*.json")) if tools_dir.exists() else []:
    tool_path = str(f)
    break
if tool_path is None:
    for f in sorted(tests_dir.glob("test_minimal.json")):
        tool_path = str(f)
        break
# Find a preset
presets_dir = Path(__file__).parent / "presets"
if presets_dir.exists():
    for sub in sorted(presets_dir.iterdir()):
        if sub.is_dir():
            for p in sorted(sub.glob("*.json")):
                preset_path = str(p)
                break
        if preset_path:
            break

print(f"Using tool_path: {tool_path}")
print(f"Using preset_path: {preset_path}")


def collect_measurements(mode_label):
    """Collect and print all measurements for the current theme mode."""
    print(f"\n{'=' * 70}")
    print(f"=== {mode_label} ===")
    print(f"{'=' * 70}")

    win = scaffold.MainWindow()
    win.show()
    dock = win.cascade_dock
    dock.show()
    app.processEvents()

    # Assign tool+preset to slot 0
    dock._slots[0]["tool_path"] = tool_path
    dock._slots[0]["preset_path"] = preset_path
    dock._refresh_button_labels()
    app.processEvents()

    info = dock._slot_widgets[0]
    content = dock.widget()
    content_layout = content.layout()

    # --- Section A: Slot Row Button Geometry ---
    print(f"\n--- Section A: Slot Row Button Geometry (slot 0, {mode_label}) ---")
    widgets_map = {
        "num_label": info["num_label"],
        "main_btn": info["main_btn"],
        "arrow_btn": info["arrow_btn"],
        "remove_btn": info["remove_btn"],
    }
    for name, w in widgets_map.items():
        text = w.text() if hasattr(w, "text") else "N/A"
        font = w.font()
        sh = w.sizeHint()
        fixed_w = w.minimumWidth() == w.maximumWidth()
        fixed_h = w.minimumHeight() == w.maximumHeight()
        cm = w.contentsMargins()
        print(f"Widget: {name}")
        print(f"  text: {text!r}")
        print(f"  font family: {font.family()}")
        print(f"  font pixel size: {font.pixelSize()}")
        print(f"  font point size: {font.pointSize()}")
        print(f"  sizeHint: {sh.width()} x {sh.height()}")
        print(f"  fixedWidth set: {fixed_w}")
        print(f"  fixedWidth value: {w.minimumWidth() if fixed_w else 'N/A'}")
        print(f"  fixedHeight set: {fixed_h}")
        print(f"  actual size: {w.size().width()} x {w.size().height()}")
        print(f"  styleSheet: '{w.styleSheet()}'")
        print(f"  contentsMargins: {cm.left()},{cm.top()},{cm.right()},{cm.bottom()}")

    # --- Section B: Row Layout Budget ---
    print(f"\n--- Section B: Row Layout Budget ({mode_label}) ---")
    cl_margins = content_layout.contentsMargins()
    print(f"content fixedWidth: {content.width()}")
    print(f"content_layout margins L+R: {cl_margins.left() + cl_margins.right()}")

    # Find row1 layout from the slot widget
    slot_widget = info["widget"]
    slot_layout = slot_widget.layout()
    row1 = slot_layout.itemAt(0).layout()
    print(f"row1 spacing: {row1.spacing()}")

    nw = info["num_label"].size().width()
    mw = info["main_btn"].size().width()
    aw = info["arrow_btn"].size().width()
    rw = info["remove_btn"].size().width()
    n_items = 4
    total = nw + mw + aw + rw + row1.spacing() * (n_items - 1)
    available = content.width() - cl_margins.left() - cl_margins.right()
    print(f"num_label width: {nw}")
    print(f"main_btn width: {mw}")
    print(f"arrow_btn width: {aw}")
    print(f"remove_btn width: {rw}")
    print(f"total consumed: {total}")
    print(f"available: {available}")
    print(f"overflow: {total - available}")

    # --- Section C: Button Text Rendering ---
    print(f"\n--- Section C: Button Text Rendering ({mode_label}) ---")
    for name in ("arrow_btn", "remove_btn"):
        w = widgets_map[name]
        char = w.text()
        fm = w.fontMetrics()
        text_w = fm.horizontalAdvance(char)
        # Estimate inner width: widget width - contentsMargins L+R - some padding
        cm = w.contentsMargins()
        # QPushButton padding from QSS is 4px 12px in dark, platform default in light
        inner_w = w.size().width() - cm.left() - cm.right()
        in_font = fm.inFontUcs4(ord(char))
        print(f"Widget: {name}")
        print(f"  text: '{char}' (U+{ord(char):04X})")
        print(f"  font: {w.font().family()} {w.font().pointSize()}pt")
        print(f"  text width via fontMetrics: {text_w}")
        print(f"  button inner width (width - contentsMargins): {inner_w}")
        print(f"  fits: {text_w <= inner_w}")
        print(f"  inFontUcs4: {in_font}")

    # --- Section D: Dark Mode QSS Impact ---
    print(f"\n--- Section D: Dark Mode QSS Impact on Cascade Buttons ({mode_label}) ---")
    qss = app.styleSheet()
    if qss:
        # Extract QPushButton rules
        import re
        blocks = re.findall(r'(QPushButton[^{]*\{[^}]*\})', qss)
        if blocks:
            print("Dark QSS rules affecting QPushButton:")
            for b in blocks:
                print(f"  {b.strip()}")
        else:
            print("No QPushButton rules found in app stylesheet")

        # Check for specific properties
        for prop in ("min-height", "padding", "border", "font-size", "margin"):
            found = [b for b in blocks if prop in b]
            if found:
                print(f"  QPushButton sets '{prop}': YES")
            else:
                print(f"  QPushButton sets '{prop}': no")

        # Check QDockWidget rules
        dock_blocks = re.findall(r'(QDockWidget[^{]*\{[^}]*\})', qss)
        if dock_blocks:
            print("QDockWidget rules in QSS:")
            for b in dock_blocks:
                print(f"  {b.strip()}")
        else:
            print("No QDockWidget rules in app stylesheet")
    else:
        print("No app stylesheet set (light mode)")

    # --- Section E: Chain Bar Button Layout ---
    print(f"\n--- Section E: Chain Bar Button Layout ({mode_label}) ---")
    chain_btns = {
        "loop_btn": dock.loop_btn,
        "run_chain_btn": dock.run_chain_btn,
        "stop_chain_btn": dock.stop_chain_btn,
        "clear_all_btn": dock.clear_all_btn,
    }
    total_sh_w = 0
    for name, w in chain_btns.items():
        sh = w.sizeHint()
        msh = w.minimumSizeHint()
        sp = w.sizePolicy()
        fixed_w = w.minimumWidth() == w.maximumWidth()
        print(f"Widget: {name}")
        print(f"  text: '{w.text()}'")
        print(f"  sizeHint: {sh.width()} x {sh.height()}")
        print(f"  minimumSizeHint: {msh.width()} x {msh.height()}")
        print(f"  minimumWidth: {w.minimumWidth()}")
        print(f"  fixedWidth: {fixed_w}")
        print(f"  actual size: {w.size().width()} x {w.size().height()}")
        print(f"  sizePolicy H: {sp.horizontalPolicy()}")
        print(f"  sizePolicy V: {sp.verticalPolicy()}")
        total_sh_w += sh.width()

    # Find chain_bar layout
    chain_bar_layout = None
    for i in range(content_layout.count()):
        item = content_layout.itemAt(i)
        if item.layout() and item.layout() is not content_layout.itemAt(0).layout():
            # Check if this layout contains the run_chain_btn
            for j in range(item.layout().count()):
                sub = item.layout().itemAt(j)
                if sub.widget() is dock.run_chain_btn:
                    chain_bar_layout = item.layout()
                    break
            if chain_bar_layout:
                break

    if chain_bar_layout:
        cb_m = chain_bar_layout.contentsMargins()
        n_buttons = len(chain_btns)
        spacing = chain_bar_layout.spacing()
        total_consumed = total_sh_w + spacing * (n_buttons - 1)
        avail = content.width() - cl_margins.left() - cl_margins.right()
        # Check for trailing stretch
        has_trailing_stretch = False
        widget_count = 0
        for i in range(chain_bar_layout.count()):
            ci = chain_bar_layout.itemAt(i)
            if ci.widget():
                widget_count += 1
            elif ci.spacerItem():
                has_trailing_stretch = True
        print(f"chain_bar spacing: {spacing}")
        print(f"chain_bar contentsMargins: {cb_m.left()},{cb_m.top()},{cb_m.right()},{cb_m.bottom()}")
        print(f"total button sizeHint width: {total_sh_w}")
        print(f"total consumed (buttons + spacing): {total_consumed}")
        print(f"available width: {avail}")
        print(f"overflow: {total_consumed - avail}")
        print(f"has trailing stretch: {has_trailing_stretch}")
        print(f"chain_bar item count: {chain_bar_layout.count()} (widgets: {widget_count})")

    # --- Section G: Slot Widget Visibility in Dark Mode ---
    print(f"\n--- Section G: Slot Widget Visibility ({mode_label}) ---")
    for name in ("arrow_btn", "remove_btn"):
        w = widgets_map[name]
        pal = w.palette()
        fg = pal.color(QPalette.ColorRole.ButtonText).name()
        bg = pal.color(QPalette.ColorRole.Button).name()
        print(f"{name} visible: {w.isVisible()}")
        print(f"{name} enabled: {w.isEnabled()}")
        print(f"{name} text: '{w.text()}'")
        print(f"{name} foreground color (palette): {fg}")
        print(f"{name} background color (palette): {bg}")
        print(f"{name} styleSheet: '{w.styleSheet()}'")

    # Collect data for comparison table
    data = {}
    for name in ("arrow_btn", "remove_btn", "main_btn"):
        w = widgets_map[name]
        data[name] = (w.size().width(), w.size().height())
    for name, w in chain_btns.items():
        data[name] = (w.size().width(), w.size().height())
    data["slot_widget[0]"] = (info["widget"].size().width(), info["widget"].size().height())
    data["content widget"] = (content.size().width(), content.size().height())

    win.close()
    win.deleteLater()
    app.processEvents()

    return data


# --- Run in LIGHT mode ---
scaffold.apply_theme(False)
app.processEvents()
light_data = collect_measurements("LIGHT MODE")

# --- Run in DARK mode ---
scaffold.apply_theme(True)
app.processEvents()
dark_data = collect_measurements("DARK MODE")

# --- Section F: Light vs Dark Size Comparison ---
print(f"\n{'=' * 70}")
print("--- Section F: Light vs Dark Size Comparison ---")
print(f"{'=' * 70}")
print(f"  {'Widget':<20} {'Light WxH':<14} {'Dark WxH':<14} {'Delta'}")
print(f"  {'-'*20} {'-'*14} {'-'*14} {'-'*20}")
all_keys = list(light_data.keys())
for key in all_keys:
    lw, lh = light_data.get(key, (0, 0))
    dw, dh = dark_data.get(key, (0, 0))
    delta_w = dw - lw
    delta_h = dh - lh
    delta_str = f"w:{delta_w:+d} h:{delta_h:+d}" if (delta_w or delta_h) else "same"
    print(f"  {key:<20} {lw}x{lh:<11} {dw}x{dh:<11} {delta_str}")

print("\nDiagnostic complete.")
