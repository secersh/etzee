#!/usr/bin/env python3
"""
Place 0201 LED matrix (39 rows × 9 cols) on all B11 left switch plate PCBs.

Targets:  ETZ-B11-LSP-{5,6}-{N,L}.kicad_pcb
Footprint: LED_0201 from lib/leds.pretty/

Matrix layout:
  39 rows (vertical, mapped to IS31FL3741A CS lines)
   9 cols (horizontal, mapped to IS31FL3741A SW lines)
  351 LEDs total, all at 45° Z rotation

Bounding box: 14.5 mm wide × 73.8 mm tall
  Top-right corner: 8.2 mm inward from PCB right edge, 7.2 mm below PCB top edge
  Grid fills edge-to-edge: outermost LED centres sit on the bounding box boundary.

Run with KiCad's Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9
"""

import math
import subprocess
import sys
from pathlib import Path

ECAD_DIR  = Path(__file__).parent.parent / "b11/ecad"
LIB_DIR   = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/LED_SMD.pretty")
FOOTPRINT = "LED_0201_0603Metric"

N_ROWS = 39
N_COLS = 9
BB_W   = 14.5   # bounding box width  mm (horizontal)
BB_H   = 73.8   # bounding box height mm (vertical)
BB_R   = 5.5    # corner radius mm

BB_TR_FROM_TOP   = 8.2   # top-right corner: mm below PCB top edge
BB_TR_FROM_RIGHT = 8.2   # top-right corner: mm inward from PCB right edge
BB_MARGIN        = 0.75  # inset LED centres from bounding box edges (courtyard at 45° = 0.74mm)


def in_rounded_rect(x, y):
    """Return True if (x, y) is inside the rounded-rect bounding box (origin at top-left)."""
    cx = BB_R if x < BB_R else (BB_W - BB_R if x > BB_W - BB_R else None)
    cy = BB_R if y < BB_R else (BB_H - BB_R if y > BB_H - BB_R else None)
    if cx is not None and cy is not None:
        return math.hypot(x - cx, y - cy) <= BB_R
    return True


def _place_single(pcb_path_str):
    import pcbnew

    pcb_path = Path(pcb_path_str)
    lib_dir  = LIB_DIR

    plug = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)

    pitch_x = (BB_W - 2 * BB_MARGIN) / (N_COLS - 1)
    pitch_y = (BB_H - 2 * BB_MARGIN) / (N_ROWS - 1)

    positions = [
        (row, col)
        for row in range(N_ROWS)
        for col in range(N_COLS)
        if in_rounded_rect(BB_MARGIN + col * pitch_x, BB_MARGIN + row * pitch_y)
    ]

    footprints = [plug.FootprintLoad(str(lib_dir), FOOTPRINT)
                  for _ in positions]

    board = pcbnew.LoadBoard(str(pcb_path))

    outline   = board.GetBoardEdgesBoundingBox()
    pcb_right = pcbnew.ToMM(outline.GetRight())
    pcb_top   = pcbnew.ToMM(outline.GetTop())

    bb_tr_x = pcb_right - BB_TR_FROM_RIGHT
    bb_tr_y = pcb_top   + BB_TR_FROM_TOP
    bb_tl_x = bb_tr_x - BB_W
    bb_tl_y = bb_tr_y

    for fp in list(board.GetFootprints()):
        if FOOTPRINT in fp.GetValue():
            board.Remove(fp)

    for i, (row, col) in enumerate(positions):
        fp = footprints[i]
        x  = bb_tl_x + BB_MARGIN + col * pitch_x
        y  = bb_tl_y + BB_MARGIN + row * pitch_y

        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(45)
        fp.SetReference(f"D{i + 1}")
        fp.SetValue(FOOTPRINT)
        board.Add(fp)

    board.Save(str(pcb_path))
    print(f"  ✅  {pcb_path.name}  ({len(positions)} LEDs placed, {N_ROWS - N_COLS} skipped in corners, pitch {pitch_x:.3f}×{pitch_y:.3f} mm)")


def main():
    targets = sorted(ECAD_DIR.glob("ETZ-B11-LSP-*.kicad_pcb"))
    if not targets:
        print("error: no left switch plate PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Placing display LEDs on {len(targets)} switch plate PCBs...\n")

    for pcb_path in targets:
        print(f"  🔄  {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single",
             str(pcb_path.resolve())],
            capture_output=True, text=True
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)

    print(f"\n✅  Done.")


if __name__ == "__main__":
    if "--single" in sys.argv:
        idx = sys.argv.index("--single")
        _place_single(sys.argv[idx + 1])
    else:
        main()
