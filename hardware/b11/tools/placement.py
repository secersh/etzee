"""
Shared helpers for B11 footprint placement scripts.

Each placement script runs boards in subprocesses to get a clean pcbnew SWIG
context. This module provides the pieces that are identical across all of them.
"""

import subprocess
import sys
from pathlib import Path


# ── Layout ────────────────────────────────────────────────────────────────────

def layout(n_cols):
    """Return (row, col) grid positions for a B11 carrier of the given column count."""
    positions = []
    thumb_indent = 2
    thumb_count  = 4 if n_cols == 6 else 3
    for row in range(3):
        for col in range(n_cols):
            positions.append((row, col))
    for col in range(thumb_indent, thumb_indent + thumb_count):
        positions.append((3, col))
    return positions


# ── Board metadata ─────────────────────────────────────────────────────────────

def board_meta(stem):
    """Parse (side, board_type, n_cols) from a PCB filename stem.

    Example: 'ETZ-B11-RSC-6-MX' → ('R', 'switch-carrier', 6)
    """
    import re
    m = re.search(r'ETZ-B11-([LR])(SP|SC)-(\d+)', stem)
    if not m:
        raise ValueError(f"cannot parse board metadata from stem: {stem!r}")
    side       = m.group(1)
    board_type = "switch-plate" if m.group(2) == "SP" else "switch-carrier"
    n_cols     = int(m.group(3))
    return side, board_type, n_cols


# ── pcbnew helpers ─────────────────────────────────────────────────────────────

def init_swig():
    """Pre-initialise PCB_IO and FOOTPRINT SWIG types.

    Must be called before LoadBoard to prevent KiCad from corrupting the SWIG
    type registry. Returns the plugin handle — keep it alive for the duration
    of the process.
    """
    import pcbnew
    return pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)


def grid_origin_mm(board):
    """Return the board's grid origin as (x_mm, y_mm)."""
    import pcbnew
    origin = board.GetDesignSettings().GetGridOrigin()
    return pcbnew.ToMM(origin.x), pcbnew.ToMM(origin.y)


def existing_refs(board):
    """Return the set of reference strings already present on the board."""
    return {fp.GetReference() for fp in board.GetFootprints()}


# ── Subprocess orchestrator ────────────────────────────────────────────────────

def dispatch_worker(script_path, pcb_path, lib_dir, origin_x, origin_y):
    """Run a single-board worker in a subprocess.

    The calling script must handle '--single' in sys.argv and call its own
    _place_single() with the positional args that follow.
    """
    result = subprocess.run(
        [sys.executable, str(script_path), "--single",
         str(pcb_path.resolve()),
         str(lib_dir.resolve()),
         str(origin_x),
         str(origin_y)],
        capture_output=True, text=True
    )
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)


def run_all(targets, script_path, origins, lib_dir, label="boards"):
    """Iterate over target PCBs and dispatch each to a worker subprocess."""
    if not targets:
        print(f"error: no {label} found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(targets)} {label}...\n")
    for pcb_path in sorted(targets):
        _, board_type, _ = board_meta(pcb_path.stem)
        origin            = origins[board_type]
        print(f"  -> {pcb_path.name}")
        dispatch_worker(script_path, pcb_path, lib_dir, origin[0], origin[1])
    print(f"\nDone.")
