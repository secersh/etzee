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
from display_pinout import DSP_EDGE_PINOUT

DSP_PCB = ECAD_ROOT / "common" / "ETZ-B11-DSP.kicad_pcb"

REF = "J1"
VALUE = "DSP_CASTELLATED_EDGE"
PADS_PER_GROUP = 12
GROUPS = 4
PAD_COUNT = PADS_PER_GROUP * GROUPS
PAD_PITCH_MM = 1.27
GROUP_END_MARGIN_MM = 6.0
PAD_SIZE_X_MM = 1.50
PAD_SIZE_Y_MM = 0.95
SLOT_DRILL_X_MM = 0.80
SLOT_DRILL_Y_MM = 0.45
SOLDER_MASK_MARGIN_MM = 0.0

PAD_NETS = DSP_EDGE_PINOUT


def _mm(value):
    import pcbnew

    return pcbnew.FromMM(value)


def _vec(x_mm, y_mm):
    import pcbnew

    return pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm))


def _remove_existing(board):
    removed = 0
    for fp in list(board.GetFootprints()):
        if fp.GetReference() == REF:
            board.Remove(fp)
            removed += 1
    return removed


def _edge_groups(board):
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
        ("left-top", left, top_start),
        ("left-bottom", left, bottom_start),
        ("right-top", right, top_start),
        ("right-bottom", right, bottom_start),
    )
    for _, x, y_start in groups:
        for index in range(PADS_PER_GROUP):
            yield x, y_start + index * PAD_PITCH_MM


def _make_pad(fp, number, x, y):
    import pcbnew

    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(number))
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
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


def _ensure_net(board, net_name):
    import pcbnew

    net = board.FindNet(net_name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
    return net


def _place_single(pcb_path, dry_run=False):
    import pcbnew
    from common import init_swig

    plugin = init_swig()
    board = pcbnew.LoadBoard(str(pcb_path))
    positions = list(_edge_groups(board))

    existing = sum(1 for fp in board.GetFootprints() if fp.GetReference() == REF)
    if dry_run:
        print(f"  {pcb_path.name}  (dry-run, {existing} existing {REF} footprints, {PAD_COUNT} pads expected)")
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

    board.Save(str(pcb_path))
    print(f"  {pcb_path.name}  (saved, removed {removed}, placed {PAD_COUNT} castellated pads)")
    return plugin


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
