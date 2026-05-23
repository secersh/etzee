#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""
Place 0201 display LED matrix on all B11 switch plate PCBs.

Targets: hardware/b11/ecad/{MX,CHOC-V2,KS-33}/ETZ-B11-{L,R}SP-*.kicad_pcb

Matrix layout:
  39 rows (vertical,   mapped to IS31FL3741A CS lines as LED_CS# nets)
   9 columns (horizontal, mapped to IS31FL3741A SW lines as LED_SW# nets)
  339 LEDs after clipping a 39 × 9 grid to the rounded display area.

Bounding box: 14.5 mm wide × 73.8 mm tall, r=5.5 mm corners
  Top-right corner: 8.2 mm inward from PCB right edge, 8.2 mm below PCB top edge.

Idempotent: existing D refs are moved to the expected position and netted.
New footprints are loaded from the repo-local lib/leds.pretty library.

Usage:
  python3 place-display-leds.py
  python3 place-display-leds.py --single <board.kicad_pcb>
  python3 place-display-leds.py --dry-run

Run with KiCad's Python interpreter.
"""

import argparse
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import ECAD_ROOT, LIB_ROOT, SWITCH_FAMILIES

LEDS_LIB = LIB_ROOT / "leds.pretty"
FOOTPRINT = "0201_LED"
SWIG_WARNING_PREFIX = "swig/python detected a memory leak of type "

N_ROWS = 39
N_COLS = 9
BB_W   = 14.5   # mm
BB_H   = 73.8   # mm
BB_R   = 5.5    # mm corner radius

BB_TR_FROM_TOP   = 8.2   # mm from PCB top edge to BB top-right corner
BB_TR_FROM_RIGHT = 8.2   # mm from PCB right edge to BB top-right corner
BB_MARGIN        = 0.75  # mm inset from BB edge to first/last LED centre


def _in_rounded_rect(x, y):
    cx = BB_R if x < BB_R else (BB_W - BB_R if x > BB_W - BB_R else None)
    cy = BB_R if y < BB_R else (BB_H - BB_R if y > BB_H - BB_R else None)
    if cx is not None and cy is not None:
        return math.hypot(x - cx, y - cy) <= BB_R
    return True


def _compute_positions():
    pitch_x = (BB_W - 2 * BB_MARGIN) / (N_COLS - 1)
    pitch_y = (BB_H - 2 * BB_MARGIN) / (N_ROWS - 1)
    positions = [
        (row, col)
        for row in range(N_ROWS)
        for col in range(N_COLS)
        if _in_rounded_rect(BB_MARGIN + col * pitch_x, BB_MARGIN + row * pitch_y)
    ]
    return positions, pitch_x, pitch_y


def _ensure_net(board, net_name):
    import pcbnew
    net = board.FindNet(net_name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
    return net


def _set_led_nets(board, fp, row, col):
    nets = {
        "1": _ensure_net(board, f"LED_CS{row + 1}"),
        "2": _ensure_net(board, f"LED_SW{col + 1}"),
    }
    for pad in fp.Pads():
        net = nets.get(pad.GetNumber())
        if net is not None:
            pad.SetNet(net)


def _existing_by_ref(board):
    by_ref = {}
    duplicates = set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in by_ref:
            duplicates.add(ref)
        by_ref[ref] = fp
    return by_ref, duplicates


def _footprint_name(fp):
    fpid = fp.GetFPID()
    if hasattr(fpid, "GetLibItemName"):
        return str(fpid.GetLibItemName())
    return fp.GetValue()


def _has_body_outline(fp):
    return any(item.GetLayerName() == "F.Fab" for item in fp.GraphicalItems())


def _hide_led_fields(fp):
    import pcbnew

    keep = {"Reference", "Value"}
    for field in list(fp.GetFields()):
        if field.GetName() not in keep:
            fp.RemoveField(field)
            continue
        field.SetVisible(False)
        field.SetForceVisible(False)
        field.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.25), pcbnew.FromMM(0.25)))
        field.SetTextThickness(pcbnew.FromMM(0.04))


def _place_single(pcb_path_str, dry_run=False):
    """Called in a fresh subprocess so each pcbnew SWIG context is clean."""
    import pcbnew
    from placement import init_swig

    pcb_path = Path(pcb_path_str)
    plug = init_swig()

    positions, pitch_x, pitch_y = _compute_positions()
    board = pcbnew.LoadBoard(str(pcb_path))
    existing, duplicates = _existing_by_ref(board)

    outline = board.GetBoardEdgesBoundingBox()
    pcb_right = pcbnew.ToMM(outline.GetRight())
    pcb_top = pcbnew.ToMM(outline.GetTop())
    bb_tl_x = pcb_right - BB_TR_FROM_RIGHT - BB_W
    bb_tl_y = pcb_top + BB_TR_FROM_TOP

    added = 0
    replaced = 0
    updated = 0
    for i, (row, col) in enumerate(positions):
        ref = f"D{i + 1}"
        fp = existing.get(ref)
        replace = fp is not None and (_footprint_name(fp) != FOOTPRINT or not _has_body_outline(fp))
        if dry_run:
            if fp is None:
                added += 1
            elif replace:
                replaced += 1
            else:
                updated += 1
            continue

        if fp is None or replace:
            if fp is not None:
                board.Remove(fp)
                replaced += 1
            else:
                added += 1
            fp = plug.FootprintLoad(str(LEDS_LIB.resolve()), FOOTPRINT)
            if fp is None:
                raise RuntimeError(f"could not load footprint {FOOTPRINT}")
            fp.SetReference(ref)
            board.Add(fp)
        else:
            updated += 1

        x = bb_tl_x + BB_MARGIN + col * pitch_x
        y = bb_tl_y + BB_MARGIN + row * pitch_y
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(45)
        fp.SetValue(FOOTPRINT)
        _hide_led_fields(fp)
        _set_led_nets(board, fp, row, col)

    if dry_run:
        status = "dry-run"
    else:
        board.Save(str(pcb_path))
        status = "saved"

    duplicate_note = f", duplicate refs: {', '.join(sorted(duplicates))}" if duplicates else ""
    print(
        f"  {pcb_path.name}  ({status}, {added} added, {replaced} replaced, {updated} updated, "
        f"{len(positions)} expected, pitch {pitch_x:.3f}x{pitch_y:.3f} mm{duplicate_note})"
    )


def _write_child_output(output):
    skipped = 0
    for line in output.splitlines(keepends=True):
        if line.startswith(SWIG_WARNING_PREFIX):
            skipped += 1
            continue
        sys.stdout.write(line)
    return skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", metavar="PCB", help="process one .kicad_pcb file")
    parser.add_argument("--dry-run", action="store_true", help="report changes without saving")
    args = parser.parse_args()

    if args.single:
        _place_single(args.single, dry_run=args.dry_run)
        return

    targets = sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*SP-*.kicad_pcb")
    )
    if not targets:
        print("error: no switch plate PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Placing display LEDs on {len(targets)} switch plates...\n")

    for pcb_path in targets:
        print(f"  -> {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single", str(pcb_path.resolve())]
            + (["--dry-run"] if args.dry_run else []),
            capture_output=True,
            text=True,
        )
        skipped_warnings = _write_child_output(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)
        if skipped_warnings:
            print(f"    suppressed {skipped_warnings} KiCad SWIG cleanup warnings")

    print("\nDone.")


if __name__ == "__main__":
    main()
