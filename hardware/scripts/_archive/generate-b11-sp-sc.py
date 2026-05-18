#!/usr/bin/env python3
"""
Generate KiCad PCB files for all B11 switch plate and carrier variants.

Reads DXF board outlines from hardware/b11/mcad/pcb-outlines/ and creates
a .kicad_pcb for each variant with:
  - DXF geometry imported on Edge.Cuts
  - Board centered on A4 page
  - Board thickness: 1.6 mm for -N variants, 1.2 mm for -L variants
  - Aux-axis origin (drill/place file origin) placed at the top-left switch center
  - 19.2 mm grid injected into KiCad's user preferences (pcbnew.json)

Switch-to-board-edge offsets are read from hardware/b11/mcad/switch-origins.yaml.

Usage:
  python3 generate-b11-sp-sc.py
Requires KiCad's bundled Python (pcbnew) and ezdxf + pyyaml.
Close KiCad before running so the grid change is not overwritten.

Run with KiCad's Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9
"""

import glob
import json
import math
import sys
from pathlib import Path

try:
    import pcbnew
except ImportError:
    print("error: pcbnew not found — run with KiCad's bundled Python", file=sys.stderr)
    sys.exit(1)

try:
    import ezdxf
except ImportError:
    print("error: ezdxf not found — pip install ezdxf", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("error: pyyaml not found — pip install pyyaml", file=sys.stderr)
    sys.exit(1)

OUTLINES_DIR  = Path(__file__).parent.parent / "b11/mcad/pcb-outlines"
ECAD_DIR      = Path(__file__).parent.parent / "b11/ecad"
ORIGINS_FILE  = Path(__file__).parent.parent / "b11/mcad/switch-origins.yaml"

EDGE_WIDTH_MM = 0.05
USER_GRID_MM  = 19.2

# KiCad A4 landscape: 297 × 210 mm
A4_W_MM = 297.0
A4_H_MM = 210.0


def mm(v):
    return pcbnew.FromMM(v)


def variant_thickness(stem):
    """1.6 mm for -N (normal), 1.2 mm for -L (low-profile)."""
    return 1.2 if stem.endswith("-L") else 1.6


def compute_bbox(msp):
    """Return (min_x, min_y, max_x, max_y) in DXF coords (Y-up)."""
    xs, ys = [], []
    for e in msp:
        if e.dxftype() == "LINE":
            xs += [e.dxf.start.x, e.dxf.end.x]
            ys += [e.dxf.start.y, e.dxf.end.y]
        elif e.dxftype() in ("ARC", "CIRCLE"):
            cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
    return min(xs), min(ys), max(xs), max(ys)


def dxf_to_pcb(dxf_path, pcb_path, origin_x, origin_y):
    """
    origin_x, origin_y: distance from board top-left corner to top-left switch center (mm).
    Board is centered on A4 (297 × 210 mm landscape).
    Aux axis origin is placed at the top-left switch center.
    """
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    min_x, min_y, max_x, max_y = compute_bbox(msp)

    board_w = max_x - min_x
    board_h = max_y - min_y

    # Offset so board is centered on A4
    off_x = (A4_W_MM - board_w) / 2
    off_y = (A4_H_MM - board_h) / 2

    # DXF (Y-up) → KiCad (Y-down), board top-left at (off_x, off_y)
    def kx(x):
        return (x - min_x) + off_x

    def ky(y):
        return (max_y - y) + off_y

    def pt(x, y):
        return pcbnew.VECTOR2I(mm(kx(x)), mm(ky(y)))

    thickness = variant_thickness(pcb_path.stem)
    board = pcbnew.NewBoard(str(pcb_path))
    board.GetDesignSettings().SetBoardThickness(mm(thickness))
    board.SetTitleBlock(pcbnew.TITLE_BLOCK())

    # Grid origin = top-left switch (L boards) or top-right switch (R boards)
    is_right = "-RS" in pcb_path.stem
    switch_kx = (off_x + board_w - origin_x) if is_right else (off_x + origin_x)
    switch_ky = off_y + origin_y
    board.GetDesignSettings().SetGridOrigin(pcbnew.VECTOR2I(mm(switch_kx), mm(switch_ky)))

    for entity in msp:
        t = entity.dxftype()

        if t == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            seg.SetLayer(pcbnew.Edge_Cuts)
            seg.SetWidth(mm(EDGE_WIDTH_MM))
            seg.SetStart(pt(s.x, s.y))
            seg.SetEnd(pt(e.x, e.y))
            board.Add(seg)

        elif t == "ARC":
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r, sa, ea = entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle
            sx = cx + r * math.cos(math.radians(sa))
            sy = cy + r * math.sin(math.radians(sa))
            ex = cx + r * math.cos(math.radians(ea))
            ey = cy + r * math.sin(math.radians(ea))
            arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
            arc.SetLayer(pcbnew.Edge_Cuts)
            arc.SetWidth(mm(EDGE_WIDTH_MM))
            arc.SetCenter(pt(cx, cy))
            arc.SetStart(pt(ex, ey))   # swapped to correct winding after Y-flip
            arc.SetEnd(pt(sx, sy))
            board.Add(arc)

        elif t == "CIRCLE":
            cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
            circle = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
            circle.SetLayer(pcbnew.Edge_Cuts)
            circle.SetWidth(mm(EDGE_WIDTH_MM))
            circle.SetCenter(pt(cx, cy))
            circle.SetEnd(pcbnew.VECTOR2I(mm(kx(cx + r)), mm(ky(cy))))
            board.Add(circle)

    board.Save(str(pcb_path))


def set_kicad_user_grid(grid_mm):
    """
    Inject grid_mm into KiCad's pcbnew.json window.grid.sizes and select it.
    Modifies the global KiCad user prefs — close KiCad before running.
    """
    pref_files = sorted(glob.glob(
        str(Path.home() / "Library/Preferences/kicad/*/pcbnew.json")
    ))
    if not pref_files:
        print("  ⚠️  pcbnew.json not found — set grid to 19.2 mm manually in KiCad")
        return

    pcbnew_json = Path(pref_files[-1])
    data = json.loads(pcbnew_json.read_text())

    grid = data.setdefault("window", {}).setdefault("grid", {})
    sizes = grid.setdefault("sizes", [])

    grid_str = str(grid_mm)

    # Remove any stale entries with unit suffix from previous script runs
    stale = f"{grid_mm} mm"
    sizes[:] = [s for s in sizes if not (s.get("x") == stale and s.get("y") == stale)]

    idx = next(
        (i for i, s in enumerate(sizes)
         if s.get("x") == grid_str and s.get("y") == grid_str),
        None
    )
    if idx is None:
        sizes.append({"name": "", "x": grid_str, "y": grid_str})
        idx = len(sizes) - 1

    grid["last_size"] = idx
    pcbnew_json.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  ✅  {grid_mm} mm grid set in {pcbnew_json} (index {idx})")


def main():
    with open(ORIGINS_FILE) as f:
        origins = yaml.safe_load(f)["origins"]

    dxf_files = sorted(OUTLINES_DIR.glob("*.dxf"))

    if not dxf_files:
        print(f"error: no DXF files found in {OUTLINES_DIR}", file=sys.stderr)
        print("  run fetch-pcb-outlines.py first", file=sys.stderr)
        sys.exit(1)

    missing = [f.stem for f in dxf_files if f.stem not in origins]
    if missing:
        print(f"error: no origin defined for: {', '.join(missing)}", file=sys.stderr)
        print(f"  add entries to {ORIGINS_FILE}", file=sys.stderr)
        sys.exit(1)

    print(f"Generating {len(dxf_files)} PCB files...\n")

    for dxf in dxf_files:
        pcb_path = ECAD_DIR / (dxf.stem + ".kicad_pcb")
        origin = origins[dxf.stem]
        thickness = variant_thickness(dxf.stem)
        print(f"  🔄  {dxf.name} → {pcb_path.name}  "
              f"(origin {origin['x']}, {origin['y']} mm  |  {thickness} mm)")
        dxf_to_pcb(dxf, pcb_path, origin["x"], origin["y"])
        print(f"  ✅  {pcb_path.name}")

    print(f"\n✅  Done — {len(dxf_files)} PCBs written to {ECAD_DIR}\n")

    print("Setting KiCad user grid...")
    set_kicad_user_grid(USER_GRID_MM)
    print("  ⚠️  Reopen KiCad to pick up the grid change.")


if __name__ == "__main__":
    main()
