#!/usr/bin/env python3
"""
Apply JLCPCB 2-layer stackup to all B11 PCBs.

Thickness is determined from the board filename:
  MX          → 1.6 mm (SP and SC)
  CHOC-V2     → 1.6 mm (SP and SC, rounded from 1.65 mm plate nominal)
  KS-33 SC    → 1.6 mm
  KS-33 SP    → 1.2 mm

Text-based replacement — no KiCad Python required.
Run with any Python 3.
"""

import re
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ECAD_ROOT, SWITCH_FAMILIES, PCB_STACKUP

FAMILY_RE = re.compile(r'ETZ-B11-[LR](SP|SC)-\d+-(MX|CHOC-V2|KS-33)')


def _stackup(core_thickness, epsilon_r):
    return (
        '\t\t(stackup\n'
        '\t\t\t(layer "F.SilkS"\n'
        '\t\t\t\t(type "Top Silk Screen")\n'
        '\t\t\t\t(color "White")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Paste"\n'
        '\t\t\t\t(type "Top Solder Paste")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Mask"\n'
        '\t\t\t\t(type "Top Solder Mask")\n'
        '\t\t\t\t(color "Black")\n'
        '\t\t\t\t(thickness 0.01524)\n'
        '\t\t\t\t(material "JLCPCB Soldermask")\n'
        '\t\t\t\t(epsilon_r 3.8)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.035)\n'
        '\t\t\t)\n'
        f'\t\t\t(layer "dielectric 1"\n'
        f'\t\t\t\t(type "core")\n'
        f'\t\t\t\t(color "FR4 natural")\n'
        f'\t\t\t\t(thickness {core_thickness})\n'
        f'\t\t\t\t(material "Nan Ya Plastics NP-155F Core")\n'
        f'\t\t\t\t(epsilon_r {epsilon_r})\n'
        f'\t\t\t\t(loss_tangent 0.02)\n'
        f'\t\t\t)\n'
        '\t\t\t(layer "B.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.035)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Mask"\n'
        '\t\t\t\t(type "Bottom Solder Mask")\n'
        '\t\t\t\t(color "Black")\n'
        '\t\t\t\t(thickness 0.01524)\n'
        '\t\t\t\t(material "JLCPCB Soldermask")\n'
        '\t\t\t\t(epsilon_r 3.8)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Paste"\n'
        '\t\t\t\t(type "Bottom Solder Paste")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.SilkS"\n'
        '\t\t\t\t(type "Bottom Silk Screen")\n'
        '\t\t\t\t(color "White")\n'
        '\t\t\t)\n'
        '\t\t\t(copper_finish "None")\n'
        '\t\t\t(dielectric_constraints yes)\n'
        '\t\t)'
    )


def _replace_stackup(text, new_block):
    marker = '\t\t(stackup'
    start = text.find(marker)
    if start == -1:
        return None, "no (stackup ...) block found"

    depth, end = 0, start
    for i, ch in enumerate(text[start:], start):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if text[end:end + 1] == '\n':
        end += 1

    return text[:start] + new_block + '\n' + text[end:], None


def _replace_general_thickness(text, total_thickness):
    pattern = re.compile(r'(\n\t\(general\n\t\t\(thickness )([0-9.]+)(\)\n)')
    new_text, count = pattern.subn(
        rf'\g<1>{total_thickness}\g<3>',
        text,
        count=1,
    )
    if count == 0:
        return text, "no general thickness found"
    return new_text, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    args = parser.parse_args()

    targets = []
    for family in SWITCH_FAMILIES:
        targets.extend((ECAD_ROOT / family).glob("ETZ-B11-*.kicad_pcb"))
    targets = sorted(targets)

    if not targets:
        print("error: no boards found", file=sys.stderr)
        sys.exit(1)

    print(f"Applying JLCPCB stackup to {len(targets)} boards...\n")

    for pcb_path in targets:
        m = FAMILY_RE.search(pcb_path.stem)
        if not m:
            print(f"  skip  {pcb_path.name}  (cannot parse filename)")
            continue

        board_type, family = m.group(1), m.group(2)
        total, core, eps = PCB_STACKUP[(family, board_type)]
        text = pcb_path.read_text()
        new_text, err = _replace_stackup(text, _stackup(core, eps))

        if err:
            print(f"  skip  {pcb_path.name}  ({err})")
            continue

        new_text, err = _replace_general_thickness(new_text, total)
        if err:
            print(f"  skip  {pcb_path.name}  ({err})")
            continue

        changed = new_text != text
        if changed and not args.dry_run:
            pcb_path.write_text(new_text)

        status = "would update" if args.dry_run and changed else ("ok" if changed else "same")
        print(f"  {status:<12} {pcb_path.name}  ({total}mm)")

    print("\nDone.")


if __name__ == "__main__":
    main()
