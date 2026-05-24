#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""
Route B11 display LED matrices on switch plate PCBs.

Generated topology:
  F.Cu: LED_SW# columns on offset spines with short stubs to display LED pad 2
  F.Cu: short LED_CS# escapes from display LED pad 1 to off-pad vias
  vias: one off-pad LED_CS# via near each display LED pad 1
  B.Cu: LED_CS# rows through the off-pad vias

The script is idempotent for its generated area. It removes existing LED_CS#/LED_SW#
tracks and vias inside the display routing bounds, then recreates them from the
current display LED footprint pad positions.

Run with KiCad's Python interpreter.
"""

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parents[1]
PLACEMENT_DIR = TOOLS_DIR / "placement"

sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(PLACEMENT_DIR))

from config import ECAD_ROOT, SWITCH_FAMILIES

SWIG_WARNING_PREFIX = "swig/python detected a memory leak of type "

TRACK_WIDTH_MM = 0.127
VIA_DIAMETER_MM = 0.60
VIA_DRILL_MM = 0.30
CS_VIA_ESCAPE_MM = 0.72
CS_SAME_NET_VIA_CLEARANCE_MM = 0.13
LED_PAD_AXIS_HALF_MM = 0.23
COLUMN_SPINE_X_OFFSET_MM = -0.08
ROUTE_BOUNDS_MARGIN_MM = 2.0

DISPLAY_LED_RE = re.compile(r"D([1-9][0-9]*)$")
LED_NET_RE = re.compile(r"LED_(CS|SW)[1-9][0-9]*$")


def _load_display_placement_module():
    path = PLACEMENT_DIR / "place-display-leds.py"
    spec = importlib.util.spec_from_file_location("place_display_leds", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISPLAY = _load_display_placement_module()


def _mm(value):
    import pcbnew

    return pcbnew.FromMM(value)


def _point_mm(point):
    import pcbnew

    return pcbnew.ToMM(point.x), pcbnew.ToMM(point.y)


def _display_route_bounds(board, side):
    import pcbnew

    outline = board.GetBoardEdgesBoundingBox()
    bb_x, bb_y = DISPLAY._display_top_left(outline, side)
    margin = ROUTE_BOUNDS_MARGIN_MM
    left = bb_x - margin
    right = bb_x + DISPLAY.BB_W + margin
    top = bb_y - margin
    bottom = bb_y + DISPLAY.BB_H + margin
    return (
        pcbnew.FromMM(left),
        pcbnew.FromMM(top),
        pcbnew.FromMM(right),
        pcbnew.FromMM(bottom),
    )


def _inside_bounds(point, bounds):
    left, top, right, bottom = bounds
    return left <= point.x <= right and top <= point.y <= bottom


def _segment_touches_bounds(track, bounds):
    return _inside_bounds(track.GetStart(), bounds) or _inside_bounds(track.GetEnd(), bounds)


def _net_name(item):
    net = item.GetNet()
    return net.GetNetname() if net is not None else ""


def _is_generated_led_route(item, bounds):
    import pcbnew

    if not LED_NET_RE.fullmatch(_net_name(item)):
        return False
    if isinstance(item, pcbnew.PCB_VIA):
        return _inside_bounds(item.GetPosition(), bounds)
    return _segment_touches_bounds(item, bounds)


def _remove_existing_routes(board, bounds, dry_run):
    routes = [
        item
        for item in list(board.GetTracks())
        if _is_generated_led_route(item, bounds)
    ]
    if not dry_run:
        for item in routes:
            board.Remove(item)
    return len(routes)


def _display_leds_by_ref(board):
    leds = {}
    for fp in board.GetFootprints():
        match = DISPLAY_LED_RE.fullmatch(fp.GetReference())
        if match and DISPLAY._footprint_name(fp) == DISPLAY.FOOTPRINT:
            leds[int(match.group(1))] = fp
    return leds


def _pad(fp, number):
    pad = fp.FindPadByNumber(number)
    if pad is None:
        raise RuntimeError(f"{fp.GetReference()} has no pad {number}")
    return pad


def _ordered_led_points(board, pcb_path):
    side = DISPLAY._board_side(pcb_path)
    positions, _, _ = DISPLAY._compute_positions(side)
    footprints = _display_leds_by_ref(board)
    expected = len(positions)
    if len(footprints) != expected:
        raise RuntimeError(
            f"{pcb_path.name}: expected {expected} display LEDs, found {len(footprints)}; "
            "run placement first"
        )

    by_row = {}
    by_col = {}
    for i, (row, col, _, _) in enumerate(positions, start=1):
        fp = footprints.get(i)
        if fp is None:
            raise RuntimeError(f"{pcb_path.name}: missing display LED D{i}; run placement first")
        pad1 = _pad(fp, "1")
        pad2 = _pad(fp, "2")
        by_row.setdefault(row, []).append((pad1.GetPosition(), pad2.GetPosition(), pad1.GetNet()))
        by_col.setdefault(col, []).append((pad2.GetPosition(), pad2.GetNet()))
    return side, by_row, by_col


def _add_track(board, start, end, layer, net):
    import pcbnew

    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    track.SetLayer(layer)
    track.SetWidth(_mm(TRACK_WIDTH_MM))
    track.SetNet(net)
    board.Add(track)
    return track


def _add_via(board, position, net):
    import pcbnew

    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    via.SetWidth(_mm(VIA_DIAMETER_MM))
    via.SetDrill(_mm(VIA_DRILL_MM))
    via.SetNet(net)
    board.Add(via)
    return via


def _route_column(board, entries, dry_run):
    import pcbnew

    entries = sorted(entries, key=lambda entry: (entry[0].y, entry[0].x))
    if len(entries) < 2:
        return 0
    if dry_run:
        return len(entries) + 1

    net = entries[0][1]
    spine_points = [
        _offset_point(position, COLUMN_SPINE_X_OFFSET_MM, 0)
        for position, _ in entries
    ]
    for (position, _), spine_point in zip(entries, spine_points):
        _add_track(board, position, spine_point, pcbnew.F_Cu, net)
    _add_track(board, spine_points[0], spine_points[-1], pcbnew.F_Cu, net)
    return len(entries) + 1


def _offset_point(point, dx_mm, dy_mm):
    import pcbnew

    return pcbnew.VECTOR2I(point.x + pcbnew.FromMM(dx_mm), point.y + pcbnew.FromMM(dy_mm))


def _cs_via_position(pad1_position, pad2_position):
    import math

    p1_x, p1_y = _point_mm(pad1_position)
    p2_x, p2_y = _point_mm(pad2_position)
    dx = p1_x - p2_x
    dy = p1_y - p2_y
    length = math.hypot(dx, dy)
    if length == 0:
        raise RuntimeError("display LED pad positions overlap")
    via_position = _offset_point(
        pad1_position,
        CS_VIA_ESCAPE_MM * dx / length,
        CS_VIA_ESCAPE_MM * dy / length,
    )
    via_x, via_y = _point_mm(via_position)
    via_clearance = (
        math.hypot(via_x - p1_x, via_y - p1_y)
        - LED_PAD_AXIS_HALF_MM
        - VIA_DIAMETER_MM / 2
    )
    if via_clearance < CS_SAME_NET_VIA_CLEARANCE_MM:
        raise RuntimeError(
            f"CS via is only {via_clearance:.3f} mm from LED pad copper; "
            f"need at least {CS_SAME_NET_VIA_CLEARANCE_MM:.3f} mm"
        )
    return via_position


def _route_row(board, entries, dry_run):
    import pcbnew

    entries = sorted(entries, key=lambda entry: (entry[0].x, entry[0].y))
    if dry_run:
        return len(entries), len(entries), max(0, len(entries) - 1)
    via_positions = []
    for pad1_position, pad2_position, net in entries:
        via_position = _cs_via_position(pad1_position, pad2_position)
        _add_track(board, pad1_position, via_position, pcbnew.F_Cu, net)
        _add_via(board, via_position, net)
        via_positions.append((via_position, net))
    for (start, net), (end, _) in zip(via_positions, via_positions[1:]):
        _add_track(board, start, end, pcbnew.B_Cu, net)
    return len(via_positions), len(via_positions), len(via_positions) - 1


def _route_single(pcb_path_str, dry_run=False):
    import pcbnew
    from common import init_swig

    pcb_path = Path(pcb_path_str)
    init_swig()
    board = pcbnew.LoadBoard(str(pcb_path))

    side, by_row, by_col = _ordered_led_points(board, pcb_path)
    bounds = _display_route_bounds(board, side)
    removed = _remove_existing_routes(board, bounds, dry_run)

    top_tracks = 0
    for col in sorted(by_col):
        top_tracks += _route_column(board, by_col[col], dry_run)

    cs_escapes = 0
    vias = 0
    bottom_tracks = 0
    for row in sorted(by_row):
        row_escapes, row_vias, row_tracks = _route_row(board, by_row[row], dry_run)
        cs_escapes += row_escapes
        vias += row_vias
        bottom_tracks += row_tracks

    if dry_run:
        status = "dry-run"
    else:
        board.Save(str(pcb_path))
        status = "saved"

    print(
        f"  {pcb_path.name}  ({status}, {removed} removed, {top_tracks} F.Cu column tracks, "
        f"{cs_escapes} F.Cu CS escapes, {vias} vias, {bottom_tracks} B.Cu row tracks, "
        f"{TRACK_WIDTH_MM:.3f} mm tracks, {VIA_DIAMETER_MM:.2f}/{VIA_DRILL_MM:.2f} mm vias)"
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
        _route_single(args.single, dry_run=args.dry_run)
        return

    targets = sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*SP-*.kicad_pcb")
    )
    if not targets:
        print("error: no switch plate PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Routing display LEDs on {len(targets)} switch plates...\n")

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
