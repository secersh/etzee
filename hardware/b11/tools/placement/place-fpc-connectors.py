#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Place the left B11 carrier-to-logic-board FPC connector pair."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT, LIB_ROOT

COMPONENTS_LIB = LIB_ROOT / "components.pretty"
FOOTPRINT_NAME = "503480-2000"

# The two PCBs overlap in the assembly. Keep the connectors on a common X axis
# near their lower edges while the final cable path is being established.
PLACEMENTS = (
    (ECAD_ROOT / "KS-33" / "ETZ-B11-LSC-6-KS-33.kicad_pcb", "J1", 151.5, 143.8, 0.0, True),
    (ECAD_ROOT / "common" / "ETZ-B11-LGB-L.kicad_pcb", "J3", 151.5, 148.2, 0.0, False),
)


def _place_single(index, dry_run=False):
    import pcbnew
    from common import init_swig

    board_path, ref, x_mm, y_mm, rotation, on_back = PLACEMENTS[index]
    plugin = init_swig()
    library_fp = plugin.FootprintLoad(str(COMPONENTS_LIB.resolve()), FOOTPRINT_NAME)
    if library_fp is None:
        print(f"error: failed to load {FOOTPRINT_NAME}", file=sys.stderr)
        sys.exit(1)

    board = pcbnew.LoadBoard(str(board_path))
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    previous = existing.get(ref)
    pad_nets = {}
    schematic_path = None

    if previous is not None:
        pad_nets = {pad.GetNumber(): pad.GetNet() for pad in previous.Pads() if pad.GetNumber()}
        schematic_path = previous.GetPath()
        board.Remove(previous)

    board.Add(library_fp)
    library_fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    library_fp.SetOrientationDegrees(rotation)
    if on_back:
        library_fp.Flip(library_fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    library_fp.SetReference(ref)
    library_fp.SetValue(FOOTPRINT_NAME)
    if schematic_path is not None:
        library_fp.SetPath(schematic_path)

    for pad in library_fp.Pads():
        net = pad_nets.get(pad.GetNumber())
        if net is not None:
            pad.SetNet(net)

    if not dry_run:
        board.Save(str(board_path))

    if dry_run:
        action = "would update" if previous is not None else "would place"
    else:
        action = "updated" if previous is not None else "placed"
    side = "B.Cu" if on_back else "F.Cu"
    print(f"  {board_path.name}  ({ref} {action} on {side} at {x_mm:.1f}, {y_mm:.1f} mm)")


def place(dry_run=False):
    import subprocess

    for index in range(len(PLACEMENTS)):
        result = subprocess.run(
            [sys.executable, __file__, "--single", str(index)]
            + (["--dry-run"] if dry_run else []),
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if "--single" in sys.argv:
        _place_single(int(sys.argv[sys.argv.index("--single") + 1]), dry_run=dry_run)
    else:
        place(dry_run=dry_run)
