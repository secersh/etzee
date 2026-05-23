# SPDX-License-Identifier: Apache-2.0

import re
from pathlib import Path

SWITCH_PITCH_MM = 19.2

# Offset from board top-left corner to first switch center (mm), by board type.
GRID_ORIGINS = {
    "switch-plate":   (16.3, 16.3),
    "switch-carrier": (14.1, 14.1),
}

# Per-family data. Thicknesses from docs/b11/switch-profiles.md.
#   sp_thick: switch plate PCB order thickness (mm), rounded from switch-profiles.md
#   sc_thick: switch carrier PCB order thickness (mm), rounded from switch-profiles.md
# socket: hot-swap PCB socket footprint in lib/switches.pretty/
# led:    per-key indicator LED footprint in lib/leds.pretty/
# outline: MCAD outline suffix used by pcb-outlines/<family>/*.dxf
SWITCH_FAMILIES = {
    "MX": {
        "socket":   "PG151101S11",
        "led":      "6028_LED",
        "outline":  "MX",
        "sp_thick": 1.6,
        "sc_thick": 1.6,
    },
    "CHOC-V2": {
        "socket":   "CPG135001S30",
        "led":      "6028_LED",
        "outline":  "CHOC-V2",
        "sp_thick": 1.6,
        "sc_thick": 1.6,
    },
    "KS-33": {
        "socket":   "KS-2P02B01-01-a",
        "led":      "6028_LED",
        "outline":  "KS-33",
        "sp_thick": 1.2,
        "sc_thick": 1.6,
    },
}

# Derived stackup table used by apply-stackup.py.
# (family, board_type) → (total_mm, core_mm, epsilon_r)
# Core = total - 2×35µm copper - 2×15.24µm soldermask.
# epsilon_r from JLCPCB NP-155F datasheet: thicker boards use 4.43, thinner 4.53.
def _stackup_entry(total):
    core = round(total - 2 * 0.035 - 2 * 0.01524, 5)
    eps  = 4.43 if total >= 1.4 else 4.53
    return (total, core, eps)

PCB_STACKUP = {
    (fam, bt): _stackup_entry(data[f"{bt.lower()}_thick"])
    for fam, data in SWITCH_FAMILIES.items()
    for bt in ("SP", "SC")
}

FAMILY_PATTERN = "|".join(re.escape(family) for family in SWITCH_FAMILIES)

_TOOLS_DIR = Path(__file__).parent
_B11_DIR   = _TOOLS_DIR.parent

LIB_ROOT  = _B11_DIR.parents[1] / "lib"
ECAD_ROOT = _B11_DIR / "ecad"
MCAD_ROOT = _B11_DIR / "mcad"
