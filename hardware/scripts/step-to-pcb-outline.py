#!/usr/bin/env python3
"""
Extract the largest flat face from a STEP file and export it as a DXF board outline.

Usage: step-to-pcb-outline.py <input.step> <output.dxf>
"""

import sys
import cadquery as cq


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.step> <output.dxf>", file=sys.stderr)
        sys.exit(1)

    step_file, dxf_file = sys.argv[1], sys.argv[2]

    model = cq.importers.importStep(step_file)

    # Find flat faces — normal pointing mostly in Z (top or bottom faces of a PCB)
    faces = model.faces().vals()
    flat_faces = [
        (f.Area(), f)
        for f in faces
        if abs(f.normalAt().z) > 0.9
    ]

    if not flat_faces:
        print(f"error: no flat faces found in {step_file}", file=sys.stderr)
        sys.exit(1)

    # Pick the largest flat face — the board outline
    flat_faces.sort(key=lambda x: x[0], reverse=True)
    _, largest = flat_faces[0]

    result = cq.Workplane().add(largest)
    cq.exporters.export(result, dxf_file)
    print(f"  ✅  {dxf_file}")


if __name__ == "__main__":
    main()
