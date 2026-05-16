#!/usr/bin/env python3
"""
Generate KiCad B.CrtYd fp_lines from a STEP model.

Reads the model path and KiCad transform (offset + rotate) directly from a
.kicad_mod file, applies the transform, takes cross-sections at many Z levels,
unions the silhouettes, then outputs a courtyard polygon as fp_line segments.

Usage:
  python3 step-to-courtyard.py <footprint.kicad_mod> [clearance_mm]

  clearance_mm  extra margin beyond model silhouette (default: 0.15 mm)

Output is printed to stdout — paste into the footprint's B.CrtYd section.

Requires: cadquery, numpy, scipy
  pip install cadquery numpy scipy
"""

import re
import sys
import math
from pathlib import Path

import numpy as np
import cadquery as cq


LAYER        = "B.CrtYd"
STROKE_WIDTH = 0.127
Z_SLICES     = 16      # number of Z slices for silhouette union


# ── parse footprint ────────────────────────────────────────────────────────────

def parse_model_entry(kicad_mod_path: Path):
    text = kicad_mod_path.read_text()
    model_re  = re.search(r'\(model\s+"([^"]+)"', text)
    offset_re = re.search(r'\(offset\s+\(xyz\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\)', text)
    rotate_re = re.search(r'\(rotate\s+\(xyz\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\)', text)
    if not (model_re and offset_re and rotate_re):
        raise ValueError("Could not parse model/offset/rotate from footprint")
    model_path = (kicad_mod_path.parent / model_re.group(1)).resolve()
    offset = tuple(float(x) for x in offset_re.groups())
    rotate = tuple(float(x) for x in rotate_re.groups())
    return model_path, offset, rotate


# ── geometry ──────────────────────────────────────────────────────────────────

def load_and_transform(step_path: Path, offset, rotate) -> cq.Shape:
    """Load STEP and apply KiCad model transform (Rx, Ry, Rz then translate)."""
    raw = cq.importers.importStep(str(step_path))
    ox, oy, oz = offset
    rx, ry, rz = rotate
    wp = cq.Workplane().add(raw.val())
    if rx: wp = wp.rotate((0, 0, 0), (1, 0, 0), rx)
    if ry: wp = wp.rotate((0, 0, 0), (0, 1, 0), ry)
    if rz: wp = wp.rotate((0, 0, 0), (0, 0, 1), rz)
    # KiCad footprint Y+ is DOWN; CadQuery Y+ is UP → negate Y offset
    wp = wp.translate((ox, -oy, oz))
    return wp.val()


def collect_silhouette_points(shape: cq.Shape, n_slices: int) -> np.ndarray:
    """
    Slice the shape at n_slices Z levels, collect outer-wire edge endpoints
    from ALL faces at each slice, and return them as an Nx2 array in
    CadQuery XY coords (Y+ up).
    """
    bb = shape.BoundingBox()
    z_min, z_max = bb.zmin, bb.zmax
    pts = []

    for i in range(n_slices):
        z = z_min + (z_max - z_min) * i / max(n_slices - 1, 1)
        try:
            result = cq.Workplane("XY").add(shape).section(z)
            compound = result.vals()[0]
            for face in compound.Faces():
                for edge in face.outerWire().Edges():
                    p1 = edge.startPoint()
                    p2 = edge.endPoint()
                    pts.append((p1.x, p1.y))
                    pts.append((p2.x, p2.y))
        except Exception:
            pass

    return np.array(pts) if pts else np.empty((0, 2))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull_polygon(pts: np.ndarray, clearance: float):
    """
    Compute convex hull (Andrew's monotone chain) of pts, expand outward by
    clearance mm, return ordered list of (x, y) vertices in CadQuery coords.
    """
    if len(pts) < 3:
        return []

    pts_sorted = sorted(set(map(tuple, pts.tolist())))
    if len(pts_sorted) < 3:
        return []

    lower, upper = [], []
    for p in pts_sorted:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts_sorted):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull_verts = lower[:-1] + upper[:-1]

    # centroid for outward expansion
    cx = sum(v[0] for v in hull_verts) / len(hull_verts)
    cy = sum(v[1] for v in hull_verts) / len(hull_verts)
    expanded = []
    for x, y in hull_verts:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        if dist > 0:
            x += dx / dist * clearance
            y += dy / dist * clearance
        expanded.append((x, y))

    return expanded


# ── coordinate conversion ─────────────────────────────────────────────────────
# After applying the transform with negated Y offset (translate Y = -oy),
# CadQuery XY coordinates already equal KiCad footprint XY. No further flip.

def to_kicad(x, y):
    return round(x, 3), round(y, 3)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("usage: step-to-courtyard.py <footprint.kicad_mod> [clearance_mm]",
              file=sys.stderr)
        sys.exit(1)

    fp_path   = Path(sys.argv[1]).resolve()
    clearance = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15

    print(f"Footprint : {fp_path.name}", file=sys.stderr)
    model_path, offset, rotate = parse_model_entry(fp_path)
    print(f"Model     : {model_path.name}", file=sys.stderr)
    print(f"Rotate    : Rx={rotate[0]} Ry={rotate[1]} Rz={rotate[2]}", file=sys.stderr)
    print(f"Offset    : x={offset[0]} y={offset[1]} z={offset[2]}", file=sys.stderr)
    print(f"Clearance : {clearance} mm", file=sys.stderr)

    if not model_path.exists():
        print(f"error: model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    print("Loading STEP...", file=sys.stderr)
    shape = load_and_transform(model_path, offset, rotate)

    bb = shape.BoundingBox()
    print(f"BBox      : X[{bb.xmin:.2f},{bb.xmax:.2f}] "
          f"Y[{bb.ymin:.2f},{bb.ymax:.2f}] "
          f"Z[{bb.zmin:.2f},{bb.zmax:.2f}]", file=sys.stderr)
    print(f"BBox KiCad: X[{bb.xmin:.2f},{bb.xmax:.2f}] "
          f"Y[{bb.ymin:.2f},{bb.ymax:.2f}]", file=sys.stderr)

    print(f"Slicing ({Z_SLICES} levels)...", file=sys.stderr)
    pts = collect_silhouette_points(shape, Z_SLICES)
    print(f"Silhouette: {len(pts)} points", file=sys.stderr)

    if len(pts) < 3:
        print("error: not enough silhouette points", file=sys.stderr)
        sys.exit(1)

    verts = convex_hull_polygon(pts, clearance)
    print(f"Hull      : {len(verts)} vertices", file=sys.stderr)

    # output as closed polygon of fp_lines
    print()
    print(f"; {fp_path.stem} — B.CrtYd generated by step-to-courtyard.py"
          f" (clearance={clearance}mm, convex hull)")
    for i in range(len(verts)):
        x1, y1 = to_kicad(*verts[i])
        x2, y2 = to_kicad(*verts[(i + 1) % len(verts)])
        print(f'  (fp_line (start {x1} {y1}) (end {x2} {y2}) '
              f'(stroke (width {STROKE_WIDTH}) (type solid)) (layer "{LAYER}"))')


if __name__ == "__main__":
    main()
