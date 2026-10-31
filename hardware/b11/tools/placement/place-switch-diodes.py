#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Place row-to-column matrix diodes on the B11 KS-33 test carrier."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT, LIB_ROOT

COMPONENTS_LIB = LIB_ROOT / "components.pretty"
FOOTPRINT_NAME = "1N4148WS"
TARGET = ECAD_ROOT / "KS-33" / "ETZ-B11-LSC-6-KS-33.kicad_pcb"

# Uniform upper-left placement relative to each KS-33 switch center. This keeps
# all SOD-323 courtyards outside the switch and case-contact keepouts, including
# the rounded board edge beside D1.
DIODE_OFFSET_X_MM = -7.7
DIODE_OFFSET_Y_MM = -6.9
DIODE_ROTATION_DEG = -90.0
PLACEMENT_GRID_MM = 0.25
ROUTING_LANE_ADJUST_Y_MM = -0.25

# D1 sits below SW1 pad 2, clear of the rounded board corner. It is rotated so
# its SW-side pad faces the switch and its column-side pad faces the escape via.
DIODE_ADJUSTMENTS_MM = {
    "D1": (-0.05, 8.40),
}
DIODE_ROTATIONS_DEG = {
    "D1": 90.0,
}


def _reference_number(reference):
    match = re.fullmatch(r"SW(\d+)", reference)
    return int(match.group(1)) if match else None


def _find_or_add_net(board, name):
    import pcbnew

    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _pad_by_number(footprint, number):
    return next((pad for pad in footprint.Pads() if pad.GetNumber() == number), None)


def _is_column_net(name):
    return name.lstrip("/").startswith("COL")


def _snap_coordinate(value, origin, step):
    delta = value - origin
    steps = (abs(delta) + step // 2) // step
    return origin + (steps * step if delta >= 0 else -steps * step)


def _sync_models(footprint, library_footprint):
    models = footprint.Models()
    models.clear()
    for model in library_footprint.Models():
        models.append(model)


def place(pcb_path, dry_run=False):
    import pcbnew
    from common import init_swig

    pcb_path = Path(pcb_path)
    plugin = init_swig()
    library_fp = plugin.FootprintLoad(str(COMPONENTS_LIB.resolve()), FOOTPRINT_NAME)
    if library_fp is None:
        raise RuntimeError(f"failed to load {FOOTPRINT_NAME}")

    board = pcbnew.LoadBoard(str(pcb_path))
    grid_origin = board.GetDesignSettings().GetGridOrigin()
    placement_grid = pcbnew.FromMM(PLACEMENT_GRID_MM)
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    switches = sorted(
        (fp for fp in board.GetFootprints() if _reference_number(fp.GetReference()) is not None),
        key=lambda fp: _reference_number(fp.GetReference()),
    )
    if not switches:
        raise RuntimeError(f"no switch footprints found in {pcb_path.name}")

    added = 0
    updated = 0

    for switch in switches:
        number = _reference_number(switch.GetReference())
        diode_ref = f"D{number}"
        switch_net_name = f"SW{number}"
        switch_pad_2 = _pad_by_number(switch, "2")
        if switch_pad_2 is None:
            raise RuntimeError(f"{switch.GetReference()} has no pad 2")

        diode = by_ref.get(diode_ref)
        if _is_column_net(switch_pad_2.GetNetname()):
            column_net_name = switch_pad_2.GetNetname()
        elif diode is not None:
            diode_pad_1 = _pad_by_number(diode, "1")
            column_net_name = diode_pad_1.GetNetname() if diode_pad_1 is not None else ""
        else:
            column_net_name = ""
        if not _is_column_net(column_net_name):
            raise RuntimeError(f"cannot determine column net for {switch.GetReference()}")

        column_net = _find_or_add_net(board, column_net_name)
        switch_net = _find_or_add_net(board, switch_net_name)
        switch_pad_2.SetNet(switch_net)

        if diode is None:
            diode = plugin.FootprintLoad(str(COMPONENTS_LIB.resolve()), FOOTPRINT_NAME)
            if diode is None:
                raise RuntimeError(f"failed to load {FOOTPRINT_NAME}")
            board.Add(diode)
            diode.SetReference(diode_ref)
            diode.SetValue(FOOTPRINT_NAME)
            by_ref[diode_ref] = diode
            added += 1
        else:
            updated += 1

        _sync_models(diode, library_fp)
        diode.Reference().SetVisible(False)

        switch_position = switch.GetPosition()
        diode.SetPosition(switch_position)
        if diode.GetLayer() != pcbnew.B_Cu:
            diode.Flip(diode.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        diode.SetOrientationDegrees(DIODE_ROTATIONS_DEG.get(diode_ref, DIODE_ROTATION_DEG))
        adjust_x, adjust_y = DIODE_ADJUSTMENTS_MM.get(diode_ref, (0.0, 0.0))
        if number != 1:
            adjust_y += ROUTING_LANE_ADJUST_Y_MM
        desired_x = switch_position.x + pcbnew.FromMM(DIODE_OFFSET_X_MM + adjust_x)
        desired_y = switch_position.y + pcbnew.FromMM(DIODE_OFFSET_Y_MM + adjust_y)
        diode.SetPosition(
            pcbnew.VECTOR2I(
                _snap_coordinate(desired_x, grid_origin.x, placement_grid),
                _snap_coordinate(desired_y, grid_origin.y, placement_grid),
            )
        )

        diode_pad_1 = _pad_by_number(diode, "1")
        diode_pad_2 = _pad_by_number(diode, "2")
        diode_pad_1.SetNet(column_net)
        diode_pad_2.SetNet(switch_net)

    if not dry_run:
        board.Save(str(pcb_path))

    action = "would update" if dry_run else "updated"
    print(
        f"  {pcb_path.name} ({action}: {added} added, {updated} existing, "
        f"{len(switches)} switch nets assigned)"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, default=TARGET, help="carrier PCB to update")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    place(args.single, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
