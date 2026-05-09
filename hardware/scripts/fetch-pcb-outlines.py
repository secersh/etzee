#!/usr/bin/env python3
"""
Download PCB part STEP files from the latest MCAD release and convert to DXF board outlines.

Reads hardware/b11/mcad/parts.yaml to determine which parts are PCB outlines (build: matrix).
Downloads the corresponding STEP files from the latest GitHub release.
Converts each STEP to DXF using step-to-pcb-outline.py.
Outputs DXF files to hardware/b11/mcad/pcb-outlines/.

Usage: fetch-pcb-outlines.py [--release <tag>]
Requires: gh CLI authenticated, cadquery installed
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

REPO = "secersh/etzee"
PARTS_FILE = Path(__file__).parent.parent / "b11/mcad/parts.yaml"
OUTLINES_DIR = Path(__file__).parent.parent / "b11/mcad/pcb-outlines"
CONVERT_SCRIPT = Path(__file__).parent / "step-to-pcb-outline.py"

PCB_PARTS = {"ETZ-B11-LSP", "ETZ-B11-RSP", "ETZ-B11-LSC", "ETZ-B11-RSC"}

# Maps release asset suffix → variant suffix used in output filenames
ASSET_VARIANT_MAP = {
    "normal-5col": "5-N",
    "normal-6col": "6-N",
    "low-5col":    "5-L",
    "low-6col":    "6-L",
    # new-style naming (post workflow refactor)
    "5-N": "5-N",
    "5-L": "5-L",
    "6-N": "6-N",
    "6-L": "6-L",
}


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def gh(*args, **kwargs):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, **kwargs)


def latest_release_tag():
    result = gh("release", "list", "--repo", REPO, "--limit", "1", "--json", "tagName")
    return json.loads(result.stdout)[0]["tagName"]


def release_assets(tag):
    result = gh("release", "view", tag, "--repo", REPO, "--json", "assets")
    return [a["name"] for a in json.loads(result.stdout)["assets"]]


def variant_from_asset(asset_name):
    # asset_name e.g. mcad-step-b11-normal-5col.zip or mcad-step-b11-5-N.zip
    stem = asset_name.replace("mcad-step-b11-", "").replace(".zip", "")
    return ASSET_VARIANT_MAP.get(stem)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", help="Release tag to use (default: latest)")
    args = parser.parse_args()

    OUTLINES_DIR.mkdir(parents=True, exist_ok=True)

    tag = args.release or latest_release_tag()
    print(f"Using release: {tag}")

    assets = release_assets(tag)
    step_assets = [a for a in assets if a.startswith("mcad-step-b11-") and a.endswith(".zip")]

    if not step_assets:
        print("error: no mcad-step assets found in release", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        for asset in step_assets:
            variant = variant_from_asset(asset)
            if not variant:
                print(f"  ⚠️  skipping unknown asset: {asset}")
                continue

            print(f"\n📦 {asset} → variant {variant}")
            zip_path = tmpdir / asset
            run(["gh", "release", "download", tag, "--repo", REPO,
                 "--pattern", asset, "--dir", str(tmpdir)])

            with zipfile.ZipFile(zip_path) as z:
                for name in z.namelist():
                    stem = Path(name).stem.upper()
                    if stem in PCB_PARTS:
                        step_path = tmpdir / name
                        z.extract(name, tmpdir)
                        dxf_name = f"{stem}-{variant}.dxf"
                        dxf_path = OUTLINES_DIR / dxf_name
                        print(f"  🔄  {name} → {dxf_name}")
                        run([sys.executable, str(CONVERT_SCRIPT),
                             str(step_path), str(dxf_path)])

    print(f"\n✅  DXF outlines written to {OUTLINES_DIR}")


if __name__ == "__main__":
    main()
