#!/usr/bin/env python3
"""
Place MX hot-swap switch footprints on all B11 normal-profile carrier PCBs.

Targets: ETZ-B11-{LSC,RSC}-{5,6}-N.kicad_pcb
Footprint: MX-Hotswap-1U from hardware/lib/MX_V2/MX_Hotswap.pretty/

Layout (left side, coords in 19.2 mm grid units from first switch / grid origin):
  6-col:  row 0-2 → cols 0-5 (full)
          row 3   → cols 2-5 (thumb, 4 keys)
  5-col:  row 0-2 → cols 0-4 (full)
          row 3   → cols 2-4 (thumb, 3 keys)

Right-side boards are mirrored: col offsets go in the -X direction.
Footprints on right-side boards are rotated 180°.

Each board is processed in a subprocess to get a clean pcbnew SWIG context.

Run with KiCad's Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ECAD_DIR     = Path(__file__).parent.parent / "b11/ecad"
ORIGINS_FILE = Path(__file__).parent.parent / "b11/mcad/switch-origins.yaml"
LIB_DIR      = Path(__file__).parent.parent / "lib/MX_V2/MX_Hotswap.pretty"
FOOTPRINT    = "MX-Hotswap-1U"
PITCH_MM     = 19.2
MODEL_PATH   = "${KIPRJMOD}/../../lib/MX_V2/MX_Hotswap.pretty/MX-Hotswap-Socket.step"


def layout(n_cols):
    """(row, col) positions relative to grid origin (first switch)."""
    positions = []
    thumb_indent = 2
    thumb_count = 4 if n_cols == 6 else 3
    for row in range(3):
        for col in range(n_cols):
            positions.append((row, col))
    for col in range(thumb_indent, thumb_indent + thumb_count):
        positions.append((3, col))
    return positions


def make_patched_lib(src_lib, model_path):
    """Copy the .pretty library to tmp and rewrite the 3D model path."""
    tmp = Path(tempfile.mkdtemp(suffix=".pretty"))
    src = src_lib / f"{FOOTPRINT}.kicad_mod"
    dst = tmp / f"{FOOTPRINT}.kicad_mod"
    content = src.read_text().replace('"./MX-Hotswap-Socket.step"', f'"{model_path}"')
    dst.write_text(content)
    return tmp


# ── single-board worker (runs in its own subprocess) ─────────────────────────

def _place_single(pcb_path_str, lib_dir_str, origin_x, origin_y):
    """Called in a fresh subprocess — pcbnew SWIG context is clean."""
    import pcbnew

    pcb_path  = Path(pcb_path_str)
    lib_dir   = Path(lib_dir_str)
    stem      = pcb_path.stem
    is_right  = "-RSC-" in stem
    n_cols    = 6 if "-6-" in stem else 5

    def mm(v):
        return pcbnew.FromMM(v)

    # Create plug and load a footprint BEFORE LoadBoard to register SWIG types.
    # LoadBoard corrupts the SWIG type registry for PCB_IO and FOOTPRINT if they
    # have not been initialised first. Keep both references alive throughout.
    plug = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    _warmup = plug.FootprintLoad(str(lib_dir.resolve()), FOOTPRINT)

    board = pcbnew.LoadBoard(str(pcb_path))

    grid_origin = board.GetDesignSettings().GetGridOrigin()
    go_x = pcbnew.ToMM(grid_origin.x)
    go_y = pcbnew.ToMM(grid_origin.y)

    for fp in list(board.GetFootprints()):
        if "MX-Hotswap" in fp.GetValue():
            board.Remove(fp)

    positions = layout(n_cols)

    for i, (row, col) in enumerate(positions):
        fp = plug.FootprintLoad(str(lib_dir.resolve()), FOOTPRINT)

        x = (go_x - col * PITCH_MM) if is_right else (go_x + col * PITCH_MM)
        y = go_y + row * PITCH_MM

        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(180)   # south-facing LED
        fp.SetReference(f"SW{i + 1}")
        fp.SetValue(FOOTPRINT)

        for pad in fp.Pads():
            n = pad.GetNumber()
            net_name = f"ROW{row}" if n == "1" else (f"COL{col}" if n == "2" else None)
            if net_name:
                net = board.FindNet(net_name)
                if net is None:
                    net = pcbnew.NETINFO_ITEM(board, net_name)
                    board.Add(net)
                pad.SetNet(net)

        board.Add(fp)

    board.Save(str(pcb_path))
    print(f"  ✅  {pcb_path.name}  ({len(positions)} switches, {'right' if is_right else 'left'}, {n_cols}-col)")


# ── orchestrator ──────────────────────────────────────────────────────────────

def main():
    try:
        import yaml
    except ImportError:
        print("error: pyyaml not found", file=sys.stderr)
        sys.exit(1)

    with open(ORIGINS_FILE) as f:
        origins = yaml.safe_load(f)["origins"]

    targets = sorted(ECAD_DIR.glob("ETZ-B11-*SC-*-N.kicad_pcb"))
    if not targets:
        print("error: no carrier PCBs found", file=sys.stderr)
        sys.exit(1)

    patched_lib = make_patched_lib(LIB_DIR, MODEL_PATH)
    print(f"Placing switches on {len(targets)} carrier PCBs...\n")

    try:
        for pcb_path in targets:
            stem   = pcb_path.stem
            origin = origins[stem]
            print(f"  🔄  {pcb_path.name}")
            result = subprocess.run(
                [sys.executable, __file__, "--single",
                 str(pcb_path.resolve()),
                 str(patched_lib.resolve()),
                 str(origin["x"]),
                 str(origin["y"])],
                capture_output=True, text=True
            )
            sys.stdout.write(result.stdout)
            if result.returncode != 0:
                sys.stderr.write(result.stderr)
                sys.exit(result.returncode)
    finally:
        shutil.rmtree(patched_lib)

    print(f"\n✅  Done.")


if __name__ == "__main__":
    if "--single" in sys.argv:
        idx = sys.argv.index("--single")
        _place_single(sys.argv[idx + 1], sys.argv[idx + 2],
                      float(sys.argv[idx + 3]), float(sys.argv[idx + 4]))
    else:
        main()
