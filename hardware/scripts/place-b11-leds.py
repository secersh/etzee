#!/usr/bin/env python3
"""
Place SMD 6028 back-mount LED footprints on all B11 carrier PCBs.

Targets: ETZ-B11-{LSC,RSC}-{5,6}-{N,L}.kicad_pcb
Footprint: LED_SMD_6028_BackMount from hardware/lib/LED.pretty/

Layout mirrors the switch grid (same row/col positions).
LED is offset +LED_OFFSET_Y mm south of each switch center.

Pitch: 19.2 mm × 19.2 mm (matches both NP and LP switch grids).
Right-side boards: col offsets go in the -X direction.
All LEDs placed at 0° (pads along X axis, slot horizontal, faces B.Cu).

Run with KiCad's Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9
"""

import subprocess
import sys
from pathlib import Path

ECAD_DIR     = Path(__file__).parent.parent / "b11/ecad"
ORIGINS_FILE = Path(__file__).parent.parent / "b11/mcad/switch-origins.yaml"
LIB_DIR      = Path(__file__).parent.parent / "lib/LED.pretty"
FOOTPRINT    = "LED_SMD_6028_BackMount"
PITCH_MM     = 19.2
LED_OFFSET_Y = 5.9   # mm south of switch center


def layout(n_cols):
    """(row, col) positions — same grid as switch placement."""
    positions = []
    thumb_indent = 2
    thumb_count = 4 if n_cols == 6 else 3
    for row in range(3):
        for col in range(n_cols):
            positions.append((row, col))
    for col in range(thumb_indent, thumb_indent + thumb_count):
        positions.append((3, col))
    return positions


def _place_single(pcb_path_str, lib_dir_str, origin_x, origin_y):
    """Called in a fresh subprocess — pcbnew SWIG context is clean."""
    import pcbnew

    pcb_path = Path(pcb_path_str)
    lib_dir  = Path(lib_dir_str)
    stem     = pcb_path.stem
    is_right = "-RSC-" in stem
    n_cols   = 6 if "-6-" in stem else 5

    def mm(v):
        return pcbnew.FromMM(v)

    plug = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)

    positions = layout(n_cols)

    # Pre-load all footprint instances BEFORE LoadBoard to keep the SWIG type
    # registry intact — LoadBoard corrupts it for any type not yet initialised.
    footprints = [plug.FootprintLoad(str(lib_dir.resolve()), FOOTPRINT)
                  for _ in positions]

    board = pcbnew.LoadBoard(str(pcb_path))

    grid_origin = board.GetDesignSettings().GetGridOrigin()
    go_x = pcbnew.ToMM(grid_origin.x)
    go_y = pcbnew.ToMM(grid_origin.y)

    for fp in list(board.GetFootprints()):
        if FOOTPRINT in fp.GetValue():
            board.Remove(fp)

    for i, (row, col) in enumerate(positions):
        fp = footprints[i]

        x = (go_x - col * PITCH_MM) if is_right else (go_x + col * PITCH_MM)
        y = go_y + row * PITCH_MM + LED_OFFSET_Y

        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(0)
        fp.SetReference(f"LED{i + 1}")
        fp.SetValue(FOOTPRINT)

        board.Add(fp)

    board.Save(str(pcb_path))
    print(f"  ✅  {pcb_path.name}  ({len(positions)} LEDs, {'right' if is_right else 'left'}, {n_cols}-col)")


def main():
    try:
        import yaml
    except ImportError:
        print("error: pyyaml not found", file=sys.stderr)
        sys.exit(1)

    with open(ORIGINS_FILE) as f:
        origins = yaml.safe_load(f)["origins"]

    targets = sorted(ECAD_DIR.glob("ETZ-B11-*SC-*.kicad_pcb"))
    if not targets:
        print("error: no carrier PCBs found", file=sys.stderr)
        sys.exit(1)

    print(f"Placing LEDs on {len(targets)} carrier PCBs...\n")

    for pcb_path in targets:
        stem   = pcb_path.stem
        origin = origins[stem]
        print(f"  🔄  {pcb_path.name}")
        result = subprocess.run(
            [sys.executable, __file__, "--single",
             str(pcb_path.resolve()),
             str(LIB_DIR.resolve()),
             str(origin["x"]),
             str(origin["y"])],
            capture_output=True, text=True
        )
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit(result.returncode)

    print(f"\n✅  Done.")


if __name__ == "__main__":
    if "--single" in sys.argv:
        idx = sys.argv.index("--single")
        _place_single(sys.argv[idx + 1], sys.argv[idx + 2],
                      float(sys.argv[idx + 3]), float(sys.argv[idx + 4]))
    else:
        main()
