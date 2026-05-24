#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Apply manufacturer stackups to all B11 PCBs."""

import argparse
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TOOLS_DIR))

from config import COMMON_PCBS, ECAD_ROOT, PCB_STACKUP, SWITCH_FAMILIES, FAMILY_PATTERN
from hardware.tools import manufacturers
from hardware.tools.common.stackup import apply_stackup_text

FAMILY_RE = re.compile(rf'ETZ-B11-[LR](SP|SC)-\d+-({FAMILY_PATTERN})')


def targets():
    switch_targets = sorted(
        pcb
        for family in SWITCH_FAMILIES
        for pcb in (ECAD_ROOT / family).glob("ETZ-B11-*.kicad_pcb")
    )
    common_targets = sorted((ECAD_ROOT / "common").glob("ETZ-B11-*.kicad_pcb"))
    return switch_targets + common_targets


def thickness_for(pcb_path):
    match = FAMILY_RE.search(pcb_path.stem)
    if match:
        board_type, family = match.group(1), match.group(2)
        return PCB_STACKUP[(family, board_type)][0]
    if pcb_path.stem in COMMON_PCBS:
        return PCB_STACKUP[("common", pcb_path.stem)][0]
    return None


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

    mode = "Checking" if args.dry_run else "Applying"
    print(f"{mode} {manufacturer.NAME} stackup on {len(pcb_paths)} boards...\n")

    for pcb_path in pcb_paths:
        total_thickness = thickness_for(pcb_path)
        if total_thickness is None:
            print(f"  skip         {pcb_path.name}  (cannot parse filename)")
            continue

        text = pcb_path.read_text()
        new_text, err = apply_stackup_text(text, manufacturer, total_thickness)

        if err:
            print(f"  skip         {pcb_path.name}  ({err})")
            continue

        changed = new_text != text
        if changed and not args.dry_run:
            pcb_path.write_text(new_text)

        if args.dry_run:
            status = "would update" if changed else "same"
        else:
            status = "updated" if changed else "same"
        print(f"  {status:<12} {pcb_path.name}  ({total_thickness}mm)")

    print("\nDone.")


if __name__ == "__main__":
    main()
