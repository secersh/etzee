#!/usr/bin/env python3
"""
Generate JLCPCB standard design rules (.kicad_dru) for all B11 PCBs.

Places {board-name}.kicad_dru alongside each .kicad_pcb.
Non-destructive: existing files are overwritten (rules are always authoritative).

Run with any Python 3.
Reference: https://jlcpcb.com/capabilities/pcb-capabilities (2-layer standard)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ECAD_ROOT, SWITCH_FAMILIES

DRU = """\
(version 1)

# ── Copper ──────────────────────────────────────────────────────────────────
(rule "JLCPCB Min Clearance"
   (constraint clearance (min 0.127mm))
)
(rule "JLCPCB Min Track Width"
   (constraint track_width (min 0.127mm))
)

# ── Vias ─────────────────────────────────────────────────────────────────────
(rule "JLCPCB Min Via Drill"
   (constraint hole_size (min 0.3mm))
   (condition "A.Type == 'Via'")
)
(rule "JLCPCB Min Via Annular Ring"
   (constraint annular_width (min 0.13mm))
   (condition "A.Type == 'Via'")
)

# ── Through-hole ─────────────────────────────────────────────────────────────
(rule "JLCPCB Min Drill"
   (constraint hole_size (min 0.2mm))
)
(rule "JLCPCB Hole-to-Hole Clearance"
   (constraint hole_to_hole (min 0.5mm))
)

# ── Board edge ───────────────────────────────────────────────────────────────
(rule "JLCPCB Copper to Board Edge"
   (constraint edge_clearance (min 0.3mm))
)

# ── Silkscreen ───────────────────────────────────────────────────────────────
(rule "JLCPCB Min Silkscreen Width"
   (constraint track_width (min 0.153mm))
   (condition "A.Type == 'Text' || A.Type == 'GraphicShape'")
)
"""


def main():
    targets = []
    for family in SWITCH_FAMILIES:
        targets.extend((ECAD_ROOT / family).glob("ETZ-B11-*.kicad_pcb"))
    targets = sorted(targets)

    if not targets:
        print("error: no boards found", file=sys.stderr)
        sys.exit(1)

    print(f"Generating JLCPCB DRU files for {len(targets)} boards...\n")

    for pcb_path in targets:
        dru_path = pcb_path.with_suffix(".kicad_dru")
        dru_path.write_text(DRU)
        print(f"  {dru_path.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
