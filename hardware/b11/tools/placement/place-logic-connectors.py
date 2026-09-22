#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Place mirrored magnetic connector pairs on the B11 logic boards."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT, LIB_ROOT

COMPONENTS_LIB = LIB_ROOT / "components.pretty"
TOP_EDGE_Y_MM = 60.6
BOTTOM_EDGE_Y_MM = 149.4
PIN1_EDGE_INSET_MM = 16.437
PIN1_OFFSET_FROM_ORIGIN_MM = 3.0

TOP_ORIGIN_Y_MM = TOP_EDGE_Y_MM + PIN1_EDGE_INSET_MM - PIN1_OFFSET_FROM_ORIGIN_MM
BOTTOM_ORIGIN_Y_MM = BOTTOM_EDGE_Y_MM - PIN1_EDGE_INSET_MM + PIN1_OFFSET_FROM_ORIGIN_MM

BOARD_PLACEMENTS = (
    (
        ECAD_ROOT / "common" / "ETZ-B11-LLB.kicad_pcb",
        163.0,
        (
            ("J1", "CN-HY04C-01D-MALE", TOP_ORIGIN_Y_MM, 90.0),
            ("J2", "CN-HY04C-01D-FEMALE", BOTTOM_ORIGIN_Y_MM, 270.0),
        ),
    ),
    (
        ECAD_ROOT / "common" / "ETZ-B11-RLB.kicad_pcb",
        134.0,
        (
            ("J1", "CN-HY04C-01D-FEMALE", TOP_ORIGIN_Y_MM, 90.0),
            ("J2", "CN-HY04C-01D-MALE", BOTTOM_ORIGIN_Y_MM, 270.0),
        ),
    ),
)


def place(dry_run=False):
    import pcbnew
    from common import init_swig

    plugin = init_swig()
    for board_path, edge_x_mm, placements in BOARD_PLACEMENTS:
        footprints = [
            plugin.FootprintLoad(str(COMPONENTS_LIB.resolve()), footprint_name)
            for _, footprint_name, _, _ in placements
        ]
        if any(fp is None for fp in footprints):
            print("error: failed to load a CN-HY04C-01D footprint", file=sys.stderr)
            sys.exit(1)

        board = pcbnew.LoadBoard(str(board_path))
        existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
        placed = 0
        updated = 0

        for (ref, footprint_name, y_mm, rotation), library_fp in zip(placements, footprints):
            fp = existing.get(ref)
            if fp is None:
                fp = library_fp
                board.Add(fp)
                placed += 1
            else:
                pad_nets = {pad.GetNumber(): pad.GetNet() for pad in fp.Pads() if pad.GetNumber()}
                schematic_path = fp.GetPath()
                board.Remove(fp)
                fp = library_fp
                board.Add(fp)
                fp.SetPath(schematic_path)
                for pad in fp.Pads():
                    net = pad_nets.get(pad.GetNumber())
                    if net is not None:
                        pad.SetNet(net)
                updated += 1

            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(edge_x_mm), pcbnew.FromMM(y_mm)))
            fp.SetOrientationDegrees(rotation)
            fp.SetReference(ref)
            fp.SetValue(footprint_name)

        if not dry_run:
            board.Save(str(board_path))

        if dry_run:
            print(f"  {board_path.name}  ({placed} would place, {updated} would update)")
        else:
            print(f"  {board_path.name}  ({placed} placed, {updated} updated)")


if __name__ == "__main__":
    place(dry_run="--dry-run" in sys.argv)
