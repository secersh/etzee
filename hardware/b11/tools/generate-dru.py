#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Generate manufacturer design-rule files for all B11 PCBs."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from config import ECAD_ROOT, SWITCH_FAMILIES
from hardware.tools import manufacturers


def targets():
    return sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*.kicad_pcb")
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manufacturer", default="jlcpcb", choices=manufacturers.choices())
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    args = parser.parse_args()

    manufacturer = manufacturers.get(args.manufacturer)
    pcb_paths = targets()
    if not pcb_paths:
        print("error: no boards found", file=sys.stderr)
        sys.exit(1)

    mode = "Checking" if args.dry_run else "Generating"
    print(f"{mode} {manufacturer.NAME} DRU files for {len(pcb_paths)} boards...\n")

    for pcb_path in pcb_paths:
        dru_path = pcb_path.with_suffix(".kicad_dru")
        changed = not dru_path.exists() or dru_path.read_text() != manufacturer.DESIGN_RULES
        if changed and not args.dry_run:
            dru_path.write_text(manufacturer.DESIGN_RULES)

        if args.dry_run:
            status = "would write" if changed else "same"
        else:
            status = "wrote" if changed else "same"
        print(f"  {status:<11} {dru_path.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
