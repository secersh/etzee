#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Place the switch-carrier backlight power stage and branch resistors."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))
from common import init_swig
from config import ECAD_ROOT, LIB_ROOT


BOARD_PATH = ECAD_ROOT / "KS-33" / "ETZ-B11-LSC-6-KS-33.kicad_pcb"
KICAD_FOOTPRINTS = Path(
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
)

# Current validated component positions on the left six-column carrier.
PLACEMENTS = (
    ("C1", "4.7uF 10V", KICAD_FOOTPRINTS / "Capacitor_SMD.pretty", "C_0603_1608Metric", 207.825, 120.55, 180.0),
    ("L1", "SWPA4018S100MT", KICAD_FOOTPRINTS / "Inductor_SMD.pretty", "L_Sunlord_SWPA4018S", 207.075, 117.05, 180.0),
    ("U1", "TPS61169", KICAD_FOOTPRINTS / "Package_TO_SOT_SMD.pretty", "SOT-353_SC-70-5", 207.075, 113.05, 0.0),
    ("R1", "3.74R 1%", LIB_ROOT / "components.pretty", "R_0402_1005Metric", 204.825, 112.55, -90.0),
    ("D23", "B5819W", KICAD_FOOTPRINTS / "Diode_SMD.pretty", "D_SOD-123", 203.575, 117.05, 90.0),
    ("C2", "1uF 50V", KICAD_FOOTPRINTS / "Capacitor_SMD.pretty", "C_0805_2012Metric", 204.325, 120.55, 0.0),
    ("J2", "BM03B-ACHSS-GAN-ETF", LIB_ROOT / "components.pretty", "BM03B-ACHSS-GAN-ETF", 207.35, 106.55, 90.0),
)

BALLAST_FOOTPRINT = "R_0402_1005Metric"
BALLAST_VALUE = "220R 1%"
BALLAST_OFFSET_X_MM = 4.3
BALLAST_OFFSET_Y_MM = 1.8
BALLAST_ROTATION_DEG = -90.0


def _ballast_placements(board):
    """Place each resistor beside the even LED that ends its series branch."""
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    placements = []
    for branch in range(1, 12):
        resistor_ref = f"R{branch + 1}"
        led_ref = f"LED{branch * 2}"
        led = by_ref.get(led_ref)
        if led is None:
            raise RuntimeError(f"cannot place R{branch + 1}: {led_ref} is missing")
        position = led.GetPosition()
        placements.append(
            (
                resistor_ref,
                BALLAST_VALUE,
                LIB_ROOT / "components.pretty",
                BALLAST_FOOTPRINT,
                position.x / 1_000_000 + BALLAST_OFFSET_X_MM,
                position.y / 1_000_000 + BALLAST_OFFSET_Y_MM,
                BALLAST_ROTATION_DEG,
            )
        )
    return placements


def place(board_path=BOARD_PATH, dry_run=False, ballast_only=False):
    import pcbnew

    plugin = init_swig()
    board_path = Path(board_path)
    board = pcbnew.LoadBoard(str(board_path))
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}

    fixed_placements = () if ballast_only else PLACEMENTS
    placements = (*fixed_placements, *_ballast_placements(board))
    for ref, value, library, footprint_name, x_mm, y_mm, rotation in placements:
        previous = existing.get(ref)
        pad_nets = {}
        schematic_path = None
        if previous is not None:
            pad_nets = {
                pad.GetNumber(): pad.GetNet()
                for pad in previous.Pads()
                if pad.GetNumber()
            }
            schematic_path = previous.GetPath()
            board.Remove(previous)

        footprint = plugin.FootprintLoad(str(library.resolve()), footprint_name)
        if footprint is None:
            print(f"error: failed to load {library.name}:{footprint_name}", file=sys.stderr)
            sys.exit(1)

        board.Add(footprint)
        position = pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))
        footprint.SetPosition(position)
        footprint.Flip(position, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        footprint.SetOrientationDegrees(rotation)
        footprint.SetReference(ref)
        footprint.SetValue(value)
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        if schematic_path is not None:
            footprint.SetPath(schematic_path)

        for pad in footprint.Pads():
            net = pad_nets.get(pad.GetNumber())
            if net is not None:
                pad.SetNet(net)

        action = "would update" if dry_run and previous else "would place" if dry_run else "updated" if previous else "placed"
        print(
            f"  {ref} {action} on B.Cu at "
            f"{x_mm:.1f}, {y_mm:.1f} mm ({footprint_name})"
        )

    if not dry_run:
        board.Save(str(board_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, default=BOARD_PATH, help="carrier PCB to update")
    parser.add_argument("--ballast-only", action="store_true", help="update only R2-R12")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    place(args.single, dry_run=args.dry_run, ballast_only=args.ballast_only)
