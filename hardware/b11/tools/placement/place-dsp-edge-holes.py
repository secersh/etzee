#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Place rev1 castellated edge holes on the common B11 display PCB."""

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parents[1]
PLACEMENT_DIR = TOOLS_DIR / "placement"
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(PLACEMENT_DIR))

from config import ECAD_ROOT
from display_pinout import ALS_EDGE_CLUSTERS, ALS_EDGE_PINOUT, DSP_EDGE_CLUSTERS, DSP_EDGE_PINOUT

DSP_PCB = ECAD_ROOT / "common" / "ETZ-B11-DSP.kicad_pcb"

REF = "J1"
VALUE = "DSP_LED_CASTELLATIONS"
ALS_REF = "J_ALS1"
ALS_VALUE = "DSP_ALS_CASTELLATIONS"
PADS_PER_GROUP = 12
PAD_COUNT = len(DSP_EDGE_PINOUT)
ALS_PAD_COUNT = len(ALS_EDGE_PINOUT)
PAD_PITCH_MM = 1.27
GROUP_END_MARGIN_MM = 6.0
ALS_PAD_PITCH_MM = 1.27
PAD_SIZE_X_MM = 1.50
PAD_SIZE_Y_MM = 0.95
SLOT_DRILL_X_MM = 0.80
SLOT_DRILL_Y_MM = 0.45
SOLDER_MASK_MARGIN_MM = 0.0
BUS_LABEL_PREFIX = "DSP_BUS:"

PAD_NETS = DSP_EDGE_PINOUT


def _mm(value):
    import pcbnew

    return pcbnew.FromMM(value)


def _vec(x_mm, y_mm):
    import pcbnew

    return pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm))


def _remove_existing(board):
    import pcbnew

    removed = 0
    for fp in list(board.GetFootprints()):
        if fp.GetReference() in {REF, ALS_REF}:
            board.Remove(fp)
            removed += 1
    try:
        drawings = list(board.Drawings())
    except TypeError:
        drawings = []
    for drawing in drawings:
        if isinstance(drawing, pcbnew.PCB_TEXT) and drawing.GetText().startswith(BUS_LABEL_PREFIX):
            board.Remove(drawing)
            removed += 1
    return removed


def _edge_positions(board):
    import pcbnew

    bbox = board.GetBoardEdgesBoundingBox()
    left = pcbnew.ToMM(bbox.GetLeft())
    right = pcbnew.ToMM(bbox.GetRight())
    top = pcbnew.ToMM(bbox.GetTop())
    bottom = pcbnew.ToMM(bbox.GetBottom())

    group_span = PAD_PITCH_MM * (PADS_PER_GROUP - 1)
    top_start = top + GROUP_END_MARGIN_MM
    bottom_start = bottom - GROUP_END_MARGIN_MM - group_span
    if top_start + group_span >= bottom_start:
        raise RuntimeError("DSP board is too short for four separated 12-pad edge groups")

    groups = (
        (left, top_start, 11, 1),
        (left, bottom_start, PADS_PER_GROUP, 1),
        (right, bottom_start + PAD_PITCH_MM * (PADS_PER_GROUP - 1), PADS_PER_GROUP, -1),
        (right, top_start + PAD_PITCH_MM * 10, 11, -1),
    )
    for x, y_start, count, direction in groups:
        for index in range(count):
            yield x, y_start + direction * index * PAD_PITCH_MM


def _als_edge_positions(board):
    import pcbnew

    bbox = board.GetBoardEdgesBoundingBox()
    left = pcbnew.ToMM(bbox.GetLeft())
    right = pcbnew.ToMM(bbox.GetRight())
    top = pcbnew.ToMM(bbox.GetTop())

    total_span = ALS_PAD_PITCH_MM * (ALS_PAD_COUNT - 1)
    x_start = (left + right - total_span) / 2
    for index in range(ALS_PAD_COUNT):
        yield x_start + index * ALS_PAD_PITCH_MM, top


def _make_pad(fp, number, x, y):
    import pcbnew

    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(number))
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
    pad.SetProperty(pcbnew.PAD_PROP_CASTELLATED)
    pad.SetPosition(_vec(x, y))
    pad.SetSize(_vec(PAD_SIZE_X_MM, PAD_SIZE_Y_MM))
    pad.SetDrillSize(_vec(SLOT_DRILL_X_MM, SLOT_DRILL_Y_MM))
    pad.SetLocalSolderMaskMargin(_mm(SOLDER_MASK_MARGIN_MM))

    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    layers.AddLayer(pcbnew.F_Mask)
    layers.AddLayer(pcbnew.B_Mask)
    pad.SetLayerSet(layers)
    return pad


def _make_top_edge_pad(fp, number, x, y):
    import pcbnew

    pad = _make_pad(fp, number, x, y)
    pad.SetSize(_vec(PAD_SIZE_Y_MM, PAD_SIZE_X_MM))
    pad.SetDrillSize(_vec(SLOT_DRILL_Y_MM, SLOT_DRILL_X_MM))
    return pad


def _ensure_net(board, net_name):
    import pcbnew

    net = board.FindNet(net_name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
    return net


def _add_bus_label(board, text, x, y, angle_degrees=0):
    import pcbnew

    label = pcbnew.PCB_TEXT(board)
    label.SetText(f"{BUS_LABEL_PREFIX} {text}")
    label.SetLayer(pcbnew.Cmts_User)
    label.SetPosition(_vec(x, y))
    label.SetTextAngleDegrees(angle_degrees)
    label.SetTextSize(_vec(1.0, 1.0))
    label.SetTextThickness(_mm(0.12))
    label.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    label.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(label)


def _add_edge_bus_labels(board, positions, als_positions):
    left = min(x for x, _ in positions)
    right = max(x for x, _ in positions)
    top = min(y for _, y in als_positions)

    for cluster in DSP_EDGE_CLUSTERS:
        points = [positions[pad - 1] for pad in cluster["pads"]]
        avg_x = sum(x for x, _ in points) / len(points)
        avg_y = sum(y for _, y in points) / len(points)
        if avg_x < (left + right) / 2:
            _add_bus_label(board, cluster["label"], left - 2.4, avg_y, 90)
        else:
            _add_bus_label(board, cluster["label"], right + 2.4, avg_y, 90)

    for cluster in ALS_EDGE_CLUSTERS:
        points = [als_positions[pad - 1] for pad in cluster["pads"]]
        avg_x = sum(x for x, _ in points) / len(points)
        _add_bus_label(board, cluster["label"], avg_x, top - 2.2, 0)


def _place_single(pcb_path, dry_run=False):
    import pcbnew

    board = pcbnew.LoadBoard(str(pcb_path))
    positions = list(_edge_positions(board))
    als_positions = list(_als_edge_positions(board))

    existing = sum(1 for fp in board.GetFootprints() if fp.GetReference() == REF)
    if dry_run:
        print(
            f"  {pcb_path.name}  (dry-run, {existing} existing {REF} footprints, "
            f"{PAD_COUNT} LED pads and {ALS_PAD_COUNT} ALS pads expected)"
        )
        return

    removed = _remove_existing(board)

    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(REF)
    fp.SetValue(VALUE)
    fp.SetPosition(_vec(0, 0))
    board.Add(fp)

    for number, (x, y) in enumerate(positions, start=1):
        pad = _make_pad(fp, number, x, y)
        net_name = PAD_NETS[number]
        if net_name != "NC":
            pad.SetNet(_ensure_net(board, net_name))
        fp.Add(pad)

    als_fp = pcbnew.FOOTPRINT(board)
    als_fp.SetReference(ALS_REF)
    als_fp.SetValue(ALS_VALUE)
    als_fp.SetPosition(_vec(0, 0))
    board.Add(als_fp)

    for number, (x, y) in enumerate(als_positions, start=1):
        pad = _make_top_edge_pad(als_fp, number, x, y)
        pad.SetNet(_ensure_net(board, ALS_EDGE_PINOUT[number]))
        als_fp.Add(pad)

    _add_edge_bus_labels(board, positions, als_positions)

    board.Save(str(pcb_path))
    print(
        f"  {pcb_path.name}  (saved, removed {removed}, placed {PAD_COUNT} LED pads "
        f"and {ALS_PAD_COUNT} ALS pads)"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", metavar="PCB", default=str(DSP_PCB), help="DSP .kicad_pcb file")
    parser.add_argument("--dry-run", action="store_true", help="report changes without saving")
    args = parser.parse_args()

    pcb_path = Path(args.single)
    if not pcb_path.exists():
        print(f"error: missing PCB file: {pcb_path}", file=sys.stderr)
        sys.exit(1)

    _place_single(pcb_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
