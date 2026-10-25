#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Apply the switch-carrier case-contact DXF as component keepouts.

The DXF is the geometry source of truth. This importer validates and converts
its closed contours; it never moves footprints or modifies the source sketch.
"""

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT, MCAD_ROOT


TARGET = ECAD_ROOT / "KS-33" / "ETZ-B11-LSC-6-KS-33.kicad_pcb"
KEEPOUT_DXF = (
    MCAD_ROOT
    / "pcb-keepouts"
    / "KS-33"
    / "ETZ-B11-LSC-6-KS-33-case-contact.dxf"
)
ZONE_PREFIX = "CASE_CONTACT_B"
ARC_CHORD_MM = 0.05
ALIGNMENT_TOLERANCE_MM = 0.01


def _point_key(point):
    return round(point[0], 6), round(point[1], 6)


def _entity_endpoints(entity):
    if entity.dxftype() == "LINE":
        return (
            _point_key((entity.dxf.start.x, entity.dxf.start.y)),
            _point_key((entity.dxf.end.x, entity.dxf.end.y)),
        )
    if entity.dxftype() == "ARC":
        center = entity.dxf.center
        radius = entity.dxf.radius

        def endpoint(angle):
            radians = math.radians(angle)
            return _point_key(
                (center.x + radius * math.cos(radians), center.y + radius * math.sin(radians))
            )

        return endpoint(entity.dxf.start_angle), endpoint(entity.dxf.end_angle)
    raise ValueError(f"unsupported keepout entity: {entity.dxftype()}")


def _entity_points(entity):
    start, end = _entity_endpoints(entity)
    if entity.dxftype() == "LINE":
        return [start, end]

    center = entity.dxf.center
    radius = entity.dxf.radius
    start_angle = entity.dxf.start_angle
    sweep = (entity.dxf.end_angle - start_angle) % 360.0
    arc_length = math.radians(sweep) * radius
    segments = max(2, math.ceil(arc_length / ARC_CHORD_MM))
    points = []
    for index in range(segments + 1):
        angle = math.radians(start_angle + sweep * index / segments)
        points.append(
            _point_key((center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)))
        )
    points[0] = start
    points[-1] = end
    return points


def _closed_contours(modelspace):
    edges = {}
    adjacency = defaultdict(list)
    for entity in modelspace:
        if entity.dxftype() not in ("LINE", "ARC"):
            continue
        start, end = _entity_endpoints(entity)
        key = tuple(sorted((start, end)))
        if key in edges:
            raise ValueError(f"keepout DXF contains a duplicate {entity.dxftype()} segment")
        edges[key] = entity
        adjacency[start].append(key)
        adjacency[end].append(key)

    bad_nodes = [point for point, connected in adjacency.items() if len(connected) != 2]
    if bad_nodes:
        raise ValueError(f"keepout DXF does not contain closed contours near {bad_nodes[0]}")

    contours = []
    unused = set(edges)
    while unused:
        first_edge = next(iter(unused))
        start = first_edge[0]
        current = start
        contour = [start]

        while True:
            candidates = [edge for edge in adjacency[current] if edge in unused]
            if not candidates:
                if current != start:
                    raise ValueError("keepout contour ended before returning to its start")
                break

            edge_key = candidates[0]
            unused.remove(edge_key)
            entity = edges[edge_key]
            entity_start, entity_end = _entity_endpoints(entity)
            points = _entity_points(entity)
            if current == entity_end:
                points.reverse()
                next_point = entity_start
            else:
                next_point = entity_end
            contour.extend(points[1:])
            current = next_point

            if current == start:
                break

        if contour[-1] == contour[0]:
            contour.pop()
        contours.append(contour)

    return sorted(
        contours,
        key=lambda contour: (
            min(point[0] for point in contour),
            min(point[1] for point in contour),
            max(point[0] for point in contour),
            max(point[1] for point in contour),
        ),
    )


def _signed_area(contour):
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(contour, contour[1:] + contour[:1])
    ) / 2.0


def _point_inside(point, contour):
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(contour, contour[1:] + contour[:1]):
        if (y1 > y) == (y2 > y):
            continue
        crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        if crossing_x > x:
            inside = not inside
    return inside


def _regions(contours):
    """Group nested DXF contours as polygon holes instead of solid islands."""
    parents = {}
    for index, contour in enumerate(contours):
        containing = [
            candidate
            for candidate, outer in enumerate(contours)
            if candidate != index and _point_inside(contour[0], outer)
        ]
        parents[index] = min(
            containing,
            key=lambda candidate: abs(_signed_area(contours[candidate])),
            default=None,
        )

    regions = []
    for index, contour in enumerate(contours):
        if parents[index] is not None:
            continue
        holes = [
            contours[candidate]
            for candidate, parent in parents.items()
            if parent == index
        ]
        regions.append((contour, holes))
    return regions


def _alignment(modelspace, board):
    import pcbnew

    source_holes = sorted(
        ((entity.dxf.center.x, entity.dxf.center.y) for entity in modelspace if entity.dxftype() == "CIRCLE"),
        key=lambda point: (point[0], -point[1]),
    )
    board_holes = sorted(
        (
            (pcbnew.ToMM(item.GetCenter().x), pcbnew.ToMM(item.GetCenter().y))
            for item in board.GetDrawings()
            if item.GetLayer() == pcbnew.Edge_Cuts and item.GetShape() == pcbnew.SHAPE_T_CIRCLE
        ),
        key=lambda point: (point[0], point[1]),
    )
    if len(source_holes) != 4 or len(board_holes) != 4:
        raise ValueError(
            f"expected four alignment holes, found {len(source_holes)} in DXF and {len(board_holes)} on PCB"
        )

    offsets = [
        (board_x - source_x, board_y + source_y)
        for (source_x, source_y), (board_x, board_y) in zip(source_holes, board_holes)
    ]
    offset_x = sum(item[0] for item in offsets) / len(offsets)
    offset_y = sum(item[1] for item in offsets) / len(offsets)
    error = max(
        math.hypot(item[0] - offset_x, item[1] - offset_y)
        for item in offsets
    )
    if error > ALIGNMENT_TOLERANCE_MM:
        raise ValueError(f"DXF alignment holes differ from PCB by {error:.3f} mm")
    return offset_x, offset_y, error


def place(pcb_path, dry_run=False):
    import pcbnew

    document = ezdxf.readfile(str(KEEPOUT_DXF))
    modelspace = document.modelspace()
    contours = _closed_contours(modelspace)
    regions = _regions(contours)
    board = pcbnew.LoadBoard(str(pcb_path))
    offset_x, offset_y, alignment_error = _alignment(modelspace, board)

    previous = [zone for zone in board.Zones() if zone.GetZoneName().startswith(ZONE_PREFIX)]
    for zone in previous:
        board.Remove(zone)

    def make_chain(contour):
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x_mm, y_mm in contour:
            chain.Append(
                pcbnew.VECTOR2I(
                    pcbnew.FromMM(x_mm + offset_x),
                    pcbnew.FromMM(-y_mm + offset_y),
                )
            )
        chain.SetClosed(True)
        return chain

    for index, (outer, holes) in enumerate(regions, start=1):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(pcbnew.B_Cu)
        zone.SetIsRuleArea(True)
        zone.SetZoneName(f"{ZONE_PREFIX}_{index}")
        zone.SetDoNotAllowFootprints(True)
        zone.SetDoNotAllowTracks(False)
        zone.SetDoNotAllowVias(False)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowCopperPour(False)
        zone.SetBorderHatchPitch(pcbnew.FromMM(0.5))

        if holes:
            contact_area = pcbnew.SHAPE_POLY_SET()
            contact_area.AddOutline(make_chain(outer))

            exclusions = pcbnew.SHAPE_POLY_SET()
            for hole in holes:
                exclusions.AddOutline(make_chain(hole))

            contact_area.BooleanSubtract(exclusions)
            contact_area.Fracture()
            for outline_index in range(contact_area.OutlineCount()):
                zone.AddPolygon(contact_area.Outline(outline_index))
        else:
            zone.AddPolygon(make_chain(outer))

        board.Add(zone)

    if not dry_run:
        board.Save(str(pcb_path))

    action = "would replace" if dry_run else "replaced"
    print(
        f"  {Path(pcb_path).name} ({action} {len(previous)} keepouts with "
        f"{len(regions)} regions/{len(contours)} DXF contours; "
        f"alignment error {alignment_error:.4f} mm)"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, default=TARGET, help="carrier PCB to update")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    place(args.single, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
