#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Generate manufacturer design-rule files for all B11 PCBs."""

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from config import DEFAULT_PCB_MANUFACTURER, ECAD_ROOT, PCB_MANUFACTURERS, SWITCH_FAMILIES
from hardware.tools import manufacturers


BOARD_RULES = {
    "ETZ-B11-LSC-6-KS-33": """

# Mechanical hole positions are fixed by the KS-33 switch specification.
(rule "KS-33 Internal Mechanical Hole Spacing"
   (constraint hole_to_hole (min 0.48mm))
   (condition "A.memberOfFootprint('SW*') && B.memberOfFootprint('SW*')")
)
""",
}


def targets():
    switch_targets = sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*.kicad_pcb")
    )
    common_targets = sorted((ECAD_ROOT / "common").glob("ETZ-B11-*.kicad_pcb"))
    return switch_targets + common_targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manufacturer", default="jlcpcb", choices=manufacturers.choices())
    parser.add_argument("--single", metavar="PCB_STEM", help="only process one PCB stem, e.g. ETZ-B11-DSP")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    args = parser.parse_args()

    manufacturer = manufacturers.get(args.manufacturer)
    pcb_paths = targets()
    if args.single:
        pcb_paths = [path for path in pcb_paths if path.stem == args.single]
        if not pcb_paths:
            print(f"error: no board found named {args.single}", file=sys.stderr)
            sys.exit(1)
    if not pcb_paths:
        print("error: no boards found", file=sys.stderr)
        sys.exit(1)

    mode = "Checking" if args.dry_run else "Generating"
    print(f"{mode} {manufacturer.NAME} DRU files for {len(pcb_paths)} boards...\n")

    for pcb_path in pcb_paths:
        dru_path = pcb_path.with_suffix(".kicad_dru")
        assigned_manufacturer = PCB_MANUFACTURERS.get(
            pcb_path.stem, DEFAULT_PCB_MANUFACTURER
        )
        if assigned_manufacturer != args.manufacturer:
            print(f"  {'skip':<11} {dru_path.name}  (uses {assigned_manufacturer})")
            continue

        design_rules = (
            manufacturer.DESIGN_RULES.rstrip() + BOARD_RULES.get(pcb_path.stem, "")
        ).rstrip() + "\n"
        changed = not dru_path.exists() or dru_path.read_text() != design_rules
        if changed and not args.dry_run:
            dru_path.write_text(design_rules)

        if args.dry_run:
            status = "would write" if changed else "same"
        else:
            status = "wrote" if changed else "same"
        print(f"  {status:<11} {dru_path.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
