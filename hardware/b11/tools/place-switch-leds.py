#!/usr/bin/env python3
"""
Place per-key 6028 reverse-mount LED footprints on all B11 carrier PCBs.

Targets: hardware/b11/ecad/{MX,CHOC-V2,KS-33}/ETZ-B11-*SC-*.kicad_pcb
Each LED is placed LED_OFFSET_Y mm south of its corresponding switch center.

Non-destructive: refs already present on the board are skipped.
Each board is processed in a subprocess for a clean pcbnew SWIG context.

Run with KiCad's Python interpreter.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import SWITCH_FAMILIES, SWITCH_PITCH_MM, LIB_ROOT, ECAD_ROOT, FAMILY_PATTERN

LEDS_LIB     = LIB_ROOT / "leds.pretty"
FAMILY_RE    = re.compile(rf'ETZ-B11-[LR]SC-\d+-({FAMILY_PATTERN})')
LED_OFFSET_Y = 5.0   # mm south of switch center


def _place_single(pcb_path_str, dry_run=False):
    """Called in a fresh subprocess — pcbnew SWIG context is clean."""
    import pcbnew
    from placement import init_swig, board_meta, existing_refs, layout, grid_origin_mm

    pcb_path = Path(pcb_path_str)
    stem     = pcb_path.stem

    m = FAMILY_RE.search(stem)
    if not m:
        print(f"error: cannot parse family from {stem!r}", file=sys.stderr)
        sys.exit(1)
    family         = m.group(1)
    footprint_name = SWITCH_FAMILIES[family]["led"]
    lib_dir        = LEDS_LIB

    side, _, n_cols = board_meta(stem)
    positions       = layout(n_cols)

    plug       = init_swig()
    footprints = [plug.FootprintLoad(str(lib_dir.resolve()), footprint_name)
                  for _ in positions]

    board   = pcbnew.LoadBoard(str(pcb_path))
    present = existing_refs(board)
    go_x, go_y = grid_origin_mm(board)

    def mm(v):
        return pcbnew.FromMM(v)

    placed = 0

    for i, (row, col) in enumerate(positions):
        ref = f"LED{i + 1}"
        if ref in present:
            continue

        fp = footprints[i]
        x  = (go_x - col * SWITCH_PITCH_MM) if side == "R" else (go_x + col * SWITCH_PITCH_MM)
        y  = go_y + row * SWITCH_PITCH_MM + LED_OFFSET_Y

        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(0)
        fp.SetReference(ref)
        fp.SetValue(footprint_name)
        board.Add(fp)
        placed += 1

    if not dry_run:
        board.Save(str(pcb_path))
    skipped = len(positions) - placed
    status = "would place" if dry_run else "placed"
    print(f"  {pcb_path.name}  ({placed} {status}, {skipped} skipped, {side}-side, {n_cols}-col)")


def main(dry_run=False):
    targets = []
    for family in SWITCH_FAMILIES:
        targets.extend((ECAD_ROOT / family).glob("ETZ-B11-*SC-*.kicad_pcb"))
    targets = sorted(targets)

    if not targets:
        print("error: no carrier PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Placing LEDs on {len(targets)} carrier PCBs...\n")

    import subprocess
    for pcb_path in targets:
        print(f"  -> {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single", str(pcb_path.resolve())]
            + (["--dry-run"] if dry_run else []),
            capture_output=True, text=True
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)

    print("\nDone.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if "--single" in sys.argv:
        idx = sys.argv.index("--single")
        _place_single(sys.argv[idx + 1], dry_run=dry_run)
    else:
        main(dry_run=dry_run)
