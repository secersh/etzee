#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Generate B11 KiCad PCB files from local DXF outlines."""

import argparse
import math
import sys
from pathlib import Path

try:
    import pcbnew
except ImportError:
    print("error: pcbnew not found; run with KiCad's Python interpreter", file=sys.stderr)
    sys.exit(1)

try:
    import ezdxf
except ImportError:
    print("error: ezdxf not found; install hardware/b11/tools/requirements.txt", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT, GRID_ORIGINS, MCAD_ROOT, PCB_STACKUP, SWITCH_FAMILIES

EDGE_WIDTH_MM = 0.05
A4_W_MM = 297.0
A4_H_MM = 210.0

def mm(value):
    return pcbnew.FromMM(value)


def compute_bbox(modelspace):
    xs = []
    ys = []
    for entity in modelspace:
        entity_type = entity.dxftype()
        if entity_type == "LINE":
            xs.extend([entity.dxf.start.x, entity.dxf.end.x])
            ys.extend([entity.dxf.start.y, entity.dxf.end.y])
        elif entity_type in ("ARC", "CIRCLE"):
            cx = entity.dxf.center.x
            cy = entity.dxf.center.y
            radius = entity.dxf.radius
            xs.extend([cx - radius, cx + radius])
            ys.extend([cy - radius, cy + radius])

    if not xs or not ys:
        raise ValueError("DXF has no supported outline entities")

    return min(xs), min(ys), max(xs), max(ys)


def add_edge_cuts(board, modelspace, min_x, min_y, max_x, max_y, off_x, off_y):
    def kx(x):
        return (x - min_x) + off_x

    def ky(y):
        return (max_y - y) + off_y

    def pt(x, y):
        return pcbnew.VECTOR2I(mm(kx(x)), mm(ky(y)))

    for entity in modelspace:
        entity_type = entity.dxftype()

        if entity_type == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            segment = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            segment.SetLayer(pcbnew.Edge_Cuts)
            segment.SetWidth(mm(EDGE_WIDTH_MM))
            segment.SetStart(pt(start.x, start.y))
            segment.SetEnd(pt(end.x, end.y))
            board.Add(segment)

        elif entity_type == "ARC":
            cx = entity.dxf.center.x
            cy = entity.dxf.center.y
            radius = entity.dxf.radius
            start_angle = entity.dxf.start_angle
            end_angle = entity.dxf.end_angle
            sx = cx + radius * math.cos(math.radians(start_angle))
            sy = cy + radius * math.sin(math.radians(start_angle))
            ex = cx + radius * math.cos(math.radians(end_angle))
            ey = cy + radius * math.sin(math.radians(end_angle))

            arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
            arc.SetLayer(pcbnew.Edge_Cuts)
            arc.SetWidth(mm(EDGE_WIDTH_MM))
            arc.SetCenter(pt(cx, cy))
            arc.SetStart(pt(ex, ey))
            arc.SetEnd(pt(sx, sy))
            board.Add(arc)

        elif entity_type == "CIRCLE":
            cx = entity.dxf.center.x
            cy = entity.dxf.center.y
            radius = entity.dxf.radius
            circle = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
            circle.SetLayer(pcbnew.Edge_Cuts)
            circle.SetWidth(mm(EDGE_WIDTH_MM))
            circle.SetCenter(pt(cx, cy))
            circle.SetEnd(pcbnew.VECTOR2I(mm(kx(cx + radius)), mm(ky(cy))))
            board.Add(circle)


def outline_path(board_code, columns, switch_family):
    family_data = SWITCH_FAMILIES[switch_family]
    outline_suffix = family_data["outline"]
    return MCAD_ROOT / "pcb-outlines" / switch_family / f"ETZ-B11-{board_code}-{columns}-{outline_suffix}.dxf"


def board_targets():
    board_codes = ("LSP", "RSP", "LSC", "RSC")
    column_options = (5, 6)
    targets = []

    for switch_family in SWITCH_FAMILIES:
        family_dir = ECAD_ROOT / switch_family
        for board_code in board_codes:
            for columns in column_options:
                dxf_path = outline_path(board_code, columns, switch_family)
                pcb_path = family_dir / f"ETZ-B11-{board_code}-{columns}-{switch_family}.kicad_pcb"
                targets.append((dxf_path, pcb_path, switch_family, board_code))

    return targets


def generate_board(dxf_path, pcb_path, switch_family, board_code, dry_run=False):
    doc = ezdxf.readfile(str(dxf_path))
    modelspace = doc.modelspace()
    min_x, min_y, max_x, max_y = compute_bbox(modelspace)

    board_w = max_x - min_x
    board_h = max_y - min_y
    off_x = (A4_W_MM - board_w) / 2
    off_y = (A4_H_MM - board_h) / 2

    board_type = "SP" if board_code.endswith("SP") else "SC"
    total_thickness = PCB_STACKUP[(switch_family, board_type)][0]

    if dry_run:
        status = "would rewrite" if pcb_path.exists() else "would create"
        return f"{status} ({board_w:.3f} x {board_h:.3f} mm, {total_thickness}mm)"

    board = pcbnew.NewBoard(str(pcb_path))
    board.SetTitleBlock(pcbnew.TITLE_BLOCK())
    board.GetDesignSettings().SetBoardThickness(mm(total_thickness))

    origin_x, origin_y = GRID_ORIGINS["switch-plate" if board_type == "SP" else "switch-carrier"]
    is_right = board_code.startswith("R")
    switch_x = off_x + board_w - origin_x if is_right else off_x + origin_x
    switch_y = off_y + origin_y
    board.GetDesignSettings().SetGridOrigin(pcbnew.VECTOR2I(mm(switch_x), mm(switch_y)))

    add_edge_cuts(board, modelspace, min_x, min_y, max_x, max_y, off_x, off_y)

    pcb_path.parent.mkdir(parents=True, exist_ok=True)
    board.Save(str(pcb_path))
    return f"rewrote ({board_w:.3f} x {board_h:.3f} mm, {total_thickness}mm)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing PCB files")
    args = parser.parse_args()

    targets = board_targets()
    missing = [str(dxf.relative_to(MCAD_ROOT / "pcb-outlines")) for dxf, _, _, _ in targets if not dxf.exists()]
    if missing:
        print("error: missing outline DXFs:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        sys.exit(1)

    mode = "Checking" if args.dry_run else "Generating"
    print(f"{mode} {len(targets)} B11 PCB files from DXF outlines...\n")

    for dxf_path, pcb_path, switch_family, board_code in targets:
        status = generate_board(dxf_path, pcb_path, switch_family, board_code, dry_run=args.dry_run)
        print(f"  {status:<34} {dxf_path.name} -> {pcb_path.relative_to(ECAD_ROOT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
