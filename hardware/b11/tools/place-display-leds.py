#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""
Place 0201 display LED matrix on all B11 switch plate PCBs.

Targets: hardware/b11/ecad/{MX,CHOC-V2,KS-33}/ETZ-B11-{L,R}SP-*.kicad_pcb

Matrix layout:
  39 rows (vertical,   mapped to IS31FL3741A CS lines as LED_CS# nets)
   9 columns (horizontal, mapped to IS31FL3741A SW lines as LED_SW# nets)
  LEDs are placed around the display bounding-box center and clipped to the rounded display area.

Bounding box: 14.5 mm wide × 73.8 mm tall, r=5.5 mm corners
  Left switch plates:  top-right corner is 8.2 mm inward from PCB right edge, 8.2 mm below PCB top edge.
  Right switch plates: top-left corner is 8.2 mm inward from PCB left edge,  8.2 mm below PCB top edge.

The ALS position is reserved by omitting display LEDs from the top display corner:
  left switch plates reserve top-right, right switch plates reserve top-left.

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
import re
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

BB_FROM_TOP  = 8.2   # mm from PCB top edge to display bounding-box top edge
BB_FROM_SIDE = 8.2   # mm from PCB side edge to display bounding-box side edge
BB_MARGIN    = 1.0   # mm inset from BB edge to first/last LED centre

ALS_RESERVED_W = 5.0  # mm, LED-free region from the side of the display bounding box
ALS_RESERVED_H = 5.0  # mm, LED-free region from the top of the display bounding box

LEFT_CASE_CLEARANCE_OMIT = {
    0: {0, 4},
    1: {0, 5},
    2: {5},
    37: {0, 8},
    38: {0, 6},
}


def _in_rounded_rect(x, y):
    cx = BB_R if x < BB_R else (BB_W - BB_R if x > BB_W - BB_R else None)
    cy = BB_R if y < BB_R else (BB_H - BB_R if y > BB_H - BB_R else None)
    if cx is not None and cy is not None:
        return math.hypot(x - cx, y - cy) <= BB_R
    return True


def _is_reserved_for_als(x, y, side):
    if y > ALS_RESERVED_H:
        return False
    if side == "left":
        return BB_W - x <= ALS_RESERVED_W
    return x <= ALS_RESERVED_W


def _base_positions(side):
    pitch_x = (BB_W - 2 * BB_MARGIN) / (N_COLS - 1)
    pitch_y = (BB_H - 2 * BB_MARGIN) / (N_ROWS - 1)
    center_row = N_ROWS // 2
    center_col = N_COLS // 2
    positions = []
    for row in range(N_ROWS):
        for col in range(N_COLS):
            x = BB_W / 2 + (col - center_col) * pitch_x
            y = BB_H / 2 + (row - center_row) * pitch_y
            if (
                _in_rounded_rect(x, y)
                and not _is_reserved_for_als(x, y, side)
            ):
                positions.append((row, col, x, y))
    return positions, pitch_x, pitch_y


def _case_omitted_cols(side):
    left_positions, _, _ = _base_positions("left")
    left_cols_by_row = {}
    for row, col, _, _ in left_positions:
        left_cols_by_row.setdefault(row, []).append(col)

    omitted = {}
    for row, indexes in LEFT_CASE_CLEARANCE_OMIT.items():
        cols = left_cols_by_row.get(row, [])
        omitted_cols = {
            cols[index]
            for index in indexes
            if index < len(cols)
        }
        if side == "right":
            omitted_cols = {N_COLS - 1 - col for col in omitted_cols}
        omitted[row] = omitted_cols
    return omitted


def _compute_positions(side):
    positions, pitch_x, pitch_y = _base_positions(side)
    omitted = _case_omitted_cols(side)
    positions = [
        position
        for position in positions
        if position[1] not in omitted.get(position[0], set())
    ]
    return positions, pitch_x, pitch_y


def _board_side(pcb_path):
    board_code = pcb_path.name.split("-")[2]
    if board_code.startswith("L"):
        return "left"
    if board_code.startswith("R"):
        return "right"
    raise ValueError(f"could not infer board side from {pcb_path.name}")


def _display_top_left(outline, side):
    import pcbnew

    pcb_left = pcbnew.ToMM(outline.GetLeft())
    pcb_right = pcbnew.ToMM(outline.GetRight())
    pcb_top = pcbnew.ToMM(outline.GetTop())
    if side == "left":
        x = pcb_right - BB_FROM_SIDE - BB_W
    else:
        x = pcb_left + BB_FROM_SIDE
    return x, pcb_top + BB_FROM_TOP


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


def _is_display_led_ref(ref):
    return re.fullmatch(r"D[1-9][0-9]*", ref) is not None


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

    side = _board_side(pcb_path)
    positions, pitch_x, pitch_y = _compute_positions(side)
    board = pcbnew.LoadBoard(str(pcb_path))
    existing, duplicates = _existing_by_ref(board)

    outline = board.GetBoardEdgesBoundingBox()
    bb_tl_x, bb_tl_y = _display_top_left(outline, side)

    added = 0
    replaced = 0
    updated = 0
    removed = 0
    desired_refs = {f"D{i + 1}" for i in range(len(positions))}
    for i, (row, col, local_x, local_y) in enumerate(positions):
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

        x = bb_tl_x + local_x
        y = bb_tl_y + local_y
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(225)
        fp.SetValue(FOOTPRINT)
        _hide_led_fields(fp)
        _set_led_nets(board, fp, row, col)

    stale_refs = [
        (ref, fp)
        for ref, fp in existing.items()
        if ref not in desired_refs and _is_display_led_ref(ref) and _footprint_name(fp) == FOOTPRINT
    ]
    if dry_run:
        removed = len(stale_refs)
    else:
        for _, fp in stale_refs:
            board.Remove(fp)
            removed += 1

    if dry_run:
        status = "dry-run"
    else:
        board.Save(str(pcb_path))
        status = "saved"

    duplicate_note = f", duplicate refs: {', '.join(sorted(duplicates))}" if duplicates else ""
    print(
        f"  {pcb_path.name}  ({status}, {added} added, {replaced} replaced, {updated} updated, {removed} removed, "
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
