#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""
Route B11 display LED matrices on switch plate PCBs and the common DSP PCB.

Generated topology:
  F.Cu: LED_CS# rows on offset spines with short stubs to display LED pad 1
  F.Cu: short LED_SW# escapes from display LED pad 2 to off-pad vias
  vias: one off-pad LED_SW# via near each display LED pad 2
  B.Cu: LED_SW# columns through the off-pad vias

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
MICROVIA_DIAMETER_MM = 0.30
MICROVIA_DRILL_MM = 0.1016
SW_VIA_ESCAPE_MM = 0.72
SW_MICROVIA_ESCAPE_MM = 0.55
SW_SAME_NET_VIA_CLEARANCE_MM = 0.13
LED_PAD_AXIS_HALF_MM = 0.23
ROW_SPINE_Y_OFFSET_MM = -0.08
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


def _display_route_bounds(board, side, pcb_path):
    import pcbnew

    if pcb_path.stem == "ETZ-B11-DSP":
        _, bb_x, bb_y, bb_w, bb_h, _ = DISPLAY._display_context(board, pcb_path)
    else:
        outline = board.GetBoardEdgesBoundingBox()
        bb_x, bb_y = DISPLAY._display_top_left(outline, side)
        bb_w, bb_h = DISPLAY.BB_W, DISPLAY.BB_H
    margin = ROUTE_BOUNDS_MARGIN_MM
    left = bb_x - margin
    right = bb_x + bb_w + margin
    top = bb_y - margin
    bottom = bb_y + bb_h + margin
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


def _is_generated_led_route(item, bounds, clear_unnetted=False):
    import pcbnew

    net_name = _net_name(item)
    if clear_unnetted and not net_name:
        pass
    elif not LED_NET_RE.fullmatch(net_name):
        return False
    if isinstance(item, pcbnew.PCB_VIA):
        return _inside_bounds(item.GetPosition(), bounds)
    return _segment_touches_bounds(item, bounds)


def _remove_existing_routes(board, bounds, dry_run, clear_unnetted=False):
    routes = [
        item
        for item in list(board.GetTracks())
        if _is_generated_led_route(item, bounds, clear_unnetted=clear_unnetted)
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
    side, _, _, positions, _, _ = DISPLAY._display_positions(board, pcb_path)
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
        by_row.setdefault(row, []).append((pad1.GetPosition(), pad1.GetNet()))
        by_col.setdefault(col, []).append((pad2.GetPosition(), pad1.GetPosition(), pad2.GetNet()))
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


def _add_via(board, position, net, microvia=False):
    import pcbnew

    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    if microvia:
        via.SetViaType(pcbnew.VIATYPE_MICROVIA)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.In1_Cu)
        via.SetWidth(_mm(MICROVIA_DIAMETER_MM))
        via.SetDrill(_mm(MICROVIA_DRILL_MM))
    else:
        via.SetWidth(_mm(VIA_DIAMETER_MM))
        via.SetDrill(_mm(VIA_DRILL_MM))
    via.SetNet(net)
    board.Add(via)
    return via


def _route_row(board, entries, dry_run):
    import pcbnew

    entries = sorted(entries, key=lambda entry: (entry[0].x, entry[0].y))
    if len(entries) < 2:
        return 0
    if dry_run:
        return len(entries) + 1

    net = entries[0][1]
    spine_points = [
        _offset_point(position, 0, ROW_SPINE_Y_OFFSET_MM)
        for position, _ in entries
    ]
    for (position, _), spine_point in zip(entries, spine_points):
        _add_track(board, position, spine_point, pcbnew.F_Cu, net)
    _add_track(board, spine_points[0], spine_points[-1], pcbnew.F_Cu, net)
    return len(entries) + 1


def _offset_point(point, dx_mm, dy_mm):
    import pcbnew

    return pcbnew.VECTOR2I(point.x + pcbnew.FromMM(dx_mm), point.y + pcbnew.FromMM(dy_mm))


def _sw_via_position(pad2_position, pad1_position, escape_direction, via_diameter_mm, escape_mm):
    import math

    p1_x, p1_y = _point_mm(pad1_position)
    p2_x, p2_y = _point_mm(pad2_position)
    if math.hypot(p2_x - p1_x, p2_y - p1_y) == 0:
        raise RuntimeError("display LED pad positions overlap")
    via_position = _offset_point(
        pad2_position,
        escape_mm * escape_direction,
        0,
    )
    via_x, via_y = _point_mm(via_position)
    via_clearance = (
        math.hypot(via_x - p2_x, via_y - p2_y)
        - LED_PAD_AXIS_HALF_MM
        - via_diameter_mm / 2
    )
    if via_clearance < SW_SAME_NET_VIA_CLEARANCE_MM:
        raise RuntimeError(
            f"SW via is only {via_clearance:.3f} mm from LED pad copper; "
            f"need at least {SW_SAME_NET_VIA_CLEARANCE_MM:.3f} mm"
        )
    return via_position


def _route_column(board, entries, dry_run, top_microvias_only=False, microvia_fanout=False, escape_direction=1):
    import pcbnew

    entries = sorted(entries, key=lambda entry: (entry[0].y, entry[0].x))
    use_microvias = top_microvias_only or microvia_fanout
    if dry_run:
        return len(entries), len(entries), 0 if top_microvias_only else max(0, len(entries) - 1)
    via_positions = []
    via_diameter = MICROVIA_DIAMETER_MM if use_microvias else VIA_DIAMETER_MM
    escape_mm = SW_MICROVIA_ESCAPE_MM if use_microvias else SW_VIA_ESCAPE_MM
    for pad2_position, pad1_position, net in entries:
        via_position = _sw_via_position(
            pad2_position,
            pad1_position,
            escape_direction,
            via_diameter,
            escape_mm,
        )
        _add_track(board, pad2_position, via_position, pcbnew.F_Cu, net)
        _add_via(board, via_position, net, microvia=use_microvias)
        via_positions.append((via_position, net))
    if top_microvias_only:
        return len(via_positions), len(via_positions), 0
    column_layer = pcbnew.In1_Cu if microvia_fanout else pcbnew.B_Cu
    for (start, net), (end, _) in zip(via_positions, via_positions[1:]):
        _add_track(board, start, end, column_layer, net)
    return len(via_positions), len(via_positions), len(via_positions) - 1


def _route_single(pcb_path_str, dry_run=False, top_microvias_only=False, microvia_fanout=False):
    import pcbnew
    from common import init_swig

    pcb_path = Path(pcb_path_str)
    init_swig()
    board = pcbnew.LoadBoard(str(pcb_path))

    side, by_row, by_col = _ordered_led_points(board, pcb_path)
    bounds = _display_route_bounds(board, side, pcb_path)
    removed = _remove_existing_routes(
        board,
        bounds,
        dry_run,
        clear_unnetted=top_microvias_only or microvia_fanout,
    )

    top_tracks = 0
    for row in sorted(by_row):
        top_tracks += _route_row(board, by_row[row], dry_run)

    sw_escapes = 0
    vias = 0
    bottom_tracks = 0
    max_col = max(by_col)
    for col in sorted(by_col):
        escape_direction = -1 if col == max_col else (1 if col % 2 == 0 else -1)
        col_escapes, col_vias, col_tracks = _route_column(
            board,
            by_col[col],
            dry_run,
            top_microvias_only=top_microvias_only,
            microvia_fanout=microvia_fanout,
            escape_direction=escape_direction,
        )
        sw_escapes += col_escapes
        vias += col_vias
        bottom_tracks += col_tracks

    if dry_run:
        status = "dry-run"
    else:
        board.Save(str(pcb_path))
        status = "saved"

    use_microvias = top_microvias_only or microvia_fanout
    via_label = "microvias" if use_microvias else "vias"
    column_layer = "In1.Cu" if microvia_fanout else "B.Cu"
    via_size = (
        f"{MICROVIA_DIAMETER_MM:.2f}/{MICROVIA_DRILL_MM:.4f} mm microvias"
        if use_microvias
        else f"{VIA_DIAMETER_MM:.2f}/{VIA_DRILL_MM:.2f} mm vias"
    )
    print(
        f"  {pcb_path.name}  ({status}, {removed} removed, {top_tracks} F.Cu row tracks, "
        f"{sw_escapes} F.Cu SW escapes, {vias} {via_label}, {bottom_tracks} B.Cu column tracks, "
        f"{column_layer if microvia_fanout else 'B.Cu'} column layer, {TRACK_WIDTH_MM:.3f} mm tracks, {via_size})"
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
    parser.add_argument(
        "--top-microvias-only",
        action="store_true",
        help="generate F.Cu rows/escapes and F.Cu-In1.Cu microvias, but no B.Cu column tracks",
    )
    parser.add_argument(
        "--microvia-fanout",
        action="store_true",
        help="generate F.Cu rows/escapes, F.Cu-In1.Cu microvias, and In1.Cu SW columns",
    )
    args = parser.parse_args()

    if args.single:
        _route_single(
            args.single,
            dry_run=args.dry_run,
            top_microvias_only=args.top_microvias_only,
            microvia_fanout=args.microvia_fanout,
        )
        return

    targets = sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*SP-*.kicad_pcb")
    )
    dsp_pcb = ECAD_ROOT / "common" / "ETZ-B11-DSP.kicad_pcb"
    if dsp_pcb.exists():
        targets.append(dsp_pcb)
    if not targets:
        print("error: no switch plate PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Routing display LEDs on {len(targets)} switch plates...\n")

    for pcb_path in targets:
        print(f"  -> {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single", str(pcb_path.resolve())]
            + (["--dry-run"] if args.dry_run else [])
            + (["--top-microvias-only"] if args.top_microvias_only else [])
            + (["--microvia-fanout"] if args.microvia_fanout else []),
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
