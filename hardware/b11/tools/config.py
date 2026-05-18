from pathlib import Path

SWITCH_PITCH_MM = 19.2

# Offset from board top-left corner to first switch center (mm), by board type.
GRID_ORIGINS = {
    "switch-plate":   (16.3, 16.3),
    "switch-carrier": (14.1, 14.1),
}

# Footprint names by switch family. All footprints live under LIB_ROOT.
# socket: Kailh hot-swap PCB socket, in lib/switches.pretty/
# led:    per-key indicator LED,      in lib/leds.pretty/
SWITCH_FAMILIES = {
    "MX": {
        "socket": "PG151101S11",
        "led":    "6028_LED",
    },
    "CHOC-V2": {
        "socket": "CPG135001S30",
        "led":    "6028_LED",
    },
    "KS-33": {
        "socket": "KS-2P02B01-01-a",
        "led":    "6028_LED",
    },
}

_TOOLS_DIR = Path(__file__).parent
_B11_DIR   = _TOOLS_DIR.parent

LIB_ROOT  = _B11_DIR.parents[1] / "lib"
ECAD_ROOT = _B11_DIR / "ecad"
MCAD_ROOT = _B11_DIR / "mcad"
