#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Run the B11 generated PCB update flow."""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
TOOLS_DIR = Path(__file__).parent
GENERATION_DIR = TOOLS_DIR / "generation"
PLACEMENT_DIR = TOOLS_DIR / "placement"
ROUTING_DIR = TOOLS_DIR / "routing"

sys.path.insert(0, str(REPO_ROOT))
from hardware.tools import manufacturers

STAGES = ("outlines", "placement", "routing", "fab")


def run_step(label, command):
    print(f"\n==> {label}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manufacturer", default="jlcpcb", choices=manufacturers.choices(),
                        help="PCB manufacturer profile for stackup and rules")
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all",
                        help="limit update to one stage")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    parser.add_argument("--fetch-outlines", action="store_true",
                        help="download/convert outline DXFs before generating boards")
    parser.add_argument("--release", help="MCAD release tag to use with --fetch-outlines")
    args = parser.parse_args()

    selected = set(STAGES if args.stage == "all" else (args.stage,))
    dry_run = ["--dry-run"] if args.dry_run else []
    manufacturer = ["--manufacturer", args.manufacturer]

    if args.fetch_outlines:
        if args.dry_run:
            release_note = f" from release {args.release}" if args.release else " from latest MCAD release"
            print(f"dry-run: would fetch/convert PCB outline DXFs{release_note}", flush=True)
        else:
            run_step("Fetch/convert PCB outline DXFs", [
                sys.executable,
                str(GENERATION_DIR / "fetch-outlines.py"),
                *(["--release", args.release] if args.release else []),
            ])

    if "outlines" in selected:
        run_step("Generate PCB files from outlines", [
            sys.executable,
            str(GENERATION_DIR / "generate-pcbs.py"),
            *dry_run,
        ])

    if "placement" in selected:
        run_step("Place switch sockets", [
            sys.executable,
            str(PLACEMENT_DIR / "place-switch-sockets.py"),
            *dry_run,
        ])
        run_step("Place switch LEDs", [
            sys.executable,
            str(PLACEMENT_DIR / "place-switch-leds.py"),
            *dry_run,
        ])
        run_step("Place display LEDs", [
            sys.executable,
            str(PLACEMENT_DIR / "place-display-leds.py"),
            *dry_run,
        ])
        run_step("Place DSP edge holes", [
            sys.executable,
            str(PLACEMENT_DIR / "place-dsp-edge-holes.py"),
            *dry_run,
        ])

    if "routing" in selected:
        run_step("Route display LEDs", [
            sys.executable,
            str(ROUTING_DIR / "route-display-leds.py"),
            *dry_run,
        ])

    if "fab" in selected:
        run_step("Apply stackups", [
            sys.executable,
            str(GENERATION_DIR / "apply-stackup.py"),
            *manufacturer,
            *dry_run,
        ])
        run_step("Generate design rules", [
            sys.executable,
            str(GENERATION_DIR / "generate-dru.py"),
            *manufacturer,
            *dry_run,
        ])

    print("\nB11 generated PCB update flow complete.")


if __name__ == "__main__":
    main()
