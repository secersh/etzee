#!/usr/bin/env python3
"""
Place 0201 LED matrix (39 rows × 9 cols) on all B11 left switch plate PCBs.

Targets: hardware/b11/ecad/{MX,CHOC-V2,KS-33}/ETZ-B11-{L,R}SP-*.kicad_pcb
Footprint: LED_0201_0603Metric from the KiCad system LED_SMD library.

Matrix layout:
  39 rows (vertical,   mapped to IS31FL3741A CS lines)
   9 cols (horizontal, mapped to IS31FL3741A SW lines)
  351 LEDs total, all at 45° rotation, clipped to a rounded-rect bounding box.

Bounding box: 14.5 mm wide × 73.8 mm tall, r=5.5 mm corners
  Top-right corner: 8.2 mm inward from PCB right edge, 8.2 mm below PCB top edge.

Non-destructive: refs already present on the board are skipped.
Each board is processed in a subprocess for a clean pcbnew SWIG context.

Run with KiCad's Python interpreter.
"""

import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import ECAD_ROOT, SWITCH_FAMILIES

FOOTPRINT = "LED_0201_0603Metric"

N_ROWS = 39
N_COLS = 9
BB_W   = 14.5
BB_H   = 73.8
BB_R   = 5.5

BB_TR_FROM_TOP   = 8.2
BB_TR_FROM_RIGHT = 8.2
BB_MARGIN        = 0.75


def _find_led_lib():
    """Locate the KiCad system LED_SMD footprint library."""
    import pcbnew
    # pcbnew lives deep inside the KiCad bundle; SharedSupport is under Contents/
    contents = Path(pcbnew.__file__)
    for parent in contents.parents:
        candidate = parent / "SharedSupport/footprints/LED_SMD.pretty"
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "KiCad system LED_SMD.pretty not found. "
        "Make sure KiCad is installed and you are running its Python interpreter."
    )


def _in_rounded_rect(x, y):
    cx = BB_R if x < BB_R else (BB_W - BB_R if x > BB_W - BB_R else None)
    cy = BB_R if y < BB_R else (BB_H - BB_R if y > BB_H - BB_R else None)
    if cx is not None and cy is not None:
        return math.hypot(x - cx, y - cy) <= BB_R
    return True


def _place_single(pcb_path_str):
    """Called in a fresh subprocess — pcbnew SWIG context is clean."""
    import pcbnew
    from placement import init_swig, existing_refs

    pcb_path = Path(pcb_path_str)
    lib_dir  = _find_led_lib()

    plug      = init_swig()
    pitch_x   = (BB_W - 2 * BB_MARGIN) / (N_COLS - 1)
    pitch_y   = (BB_H - 2 * BB_MARGIN) / (N_ROWS - 1)
    positions = [
        (row, col)
        for row in range(N_ROWS)
        for col in range(N_COLS)
        if _in_rounded_rect(BB_MARGIN + col * pitch_x, BB_MARGIN + row * pitch_y)
    ]

    footprints = [plug.FootprintLoad(str(lib_dir), FOOTPRINT) for _ in positions]

    board   = pcbnew.LoadBoard(str(pcb_path))
    present = existing_refs(board)

    outline   = board.GetBoardEdgesBoundingBox()
    pcb_right = pcbnew.ToMM(outline.GetRight())
    pcb_top   = pcbnew.ToMM(outline.GetTop())
    bb_tl_x   = pcb_right - BB_TR_FROM_RIGHT - BB_W
    bb_tl_y   = pcb_top   + BB_TR_FROM_TOP

    placed = 0
    for i, (row, col) in enumerate(positions):
        ref = f"D{i + 1}"
        if ref in present:
            continue

        fp = footprints[i]
        x  = bb_tl_x + BB_MARGIN + col * pitch_x
        y  = bb_tl_y + BB_MARGIN + row * pitch_y

        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(45)
        fp.SetReference(ref)
        fp.SetValue(FOOTPRINT)
        board.Add(fp)
        placed += 1

    board.Save(str(pcb_path))
    skipped = len(positions) - placed
    print(f"  {pcb_path.name}  ({placed} placed, {skipped} skipped, pitch {pitch_x:.3f}×{pitch_y:.3f} mm)")


def main():
    targets = []
    for family in SWITCH_FAMILIES:
        targets.extend((ECAD_ROOT / family).glob("ETZ-B11-*SP-*.kicad_pcb"))
    targets = sorted(targets)

    if not targets:
        print("error: no switch plate PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Placing display LEDs on {len(targets)} switch plates...\n")

    for pcb_path in targets:
        print(f"  -> {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single", str(pcb_path.resolve())],
            capture_output=True, text=True
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)

    print("\nDone.")


if __name__ == "__main__":
    if "--single" in sys.argv:
        idx = sys.argv.index("--single")
        _place_single(sys.argv[idx + 1])
    else:
        main()
