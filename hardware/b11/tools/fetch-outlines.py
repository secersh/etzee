#!/usr/bin/env python3
"""Download B11 PCB STEP exports from an MCAD release and convert them to DXF outlines."""

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = "secersh/etzee"
TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parents[2]
OUTLINES_DIR = TOOLS_DIR.parent / "mcad/pcb-outlines"

COMMON_PCB_PARTS = {"ETZ-B11-LGB"}
SWITCH_PCB_PARTS = {"ETZ-B11-LSP", "ETZ-B11-RSP", "ETZ-B11-LSC", "ETZ-B11-RSC"}

ASSET_BOARD_VARIANTS = {
    "common": (None, None),
    "5-MX": (5, "MX"),
    "6-MX": (6, "MX"),
    "5-CHOC-V2": (5, "CHOC-V2"),
    "6-CHOC-V2": (6, "CHOC-V2"),
    "5-KS-33": (5, "KS-33"),
    "6-KS-33": (6, "KS-33"),
}


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, cwd=REPO_ROOT, **kwargs)


def gh(*args, **kwargs):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, cwd=REPO_ROOT, **kwargs)


def latest_release_tag():
    result = gh("release", "list", "--repo", REPO, "--limit", "1", "--json", "tagName")
    return json.loads(result.stdout)[0]["tagName"]


def release_assets(tag):
    result = gh("release", "view", tag, "--repo", REPO, "--json", "assets")
    return [asset["name"] for asset in json.loads(result.stdout)["assets"]]


def board_variant_from_asset(asset_name):
    stem = asset_name.replace("mcad-step-b11-", "").replace(".zip", "")
    return ASSET_BOARD_VARIANTS.get(stem)


def outline_destination(part_number, board_variant):
    columns, switch_family = board_variant
    if switch_family is None:
        if part_number not in COMMON_PCB_PARTS:
            return None
        return OUTLINES_DIR / "common" / f"{part_number}.dxf"

    if part_number not in SWITCH_PCB_PARTS:
        return None
    return OUTLINES_DIR / switch_family / f"{part_number}-{columns}-{switch_family}.dxf"


def step_to_pcb_outline(step_file, dxf_file):
    try:
        import cadquery as cq
    except ImportError:
        print("error: cadquery not found; install hardware/b11/tools/requirements.txt", file=sys.stderr)
        raise SystemExit(1)

    model = cq.importers.importStep(str(step_file))
    faces = model.faces().vals()
    flat_faces = [
        (face.Area(), face)
        for face in faces
        if abs(face.normalAt().z) > 0.9
    ]

    if not flat_faces:
        raise RuntimeError(f"no flat faces found in {step_file}")

    flat_faces.sort(key=lambda item: item[0], reverse=True)
    _, largest = flat_faces[0]
    result = cq.Workplane().add(largest)
    cq.exporters.export(result, str(dxf_file))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", help="release tag to use; defaults to latest")
    parser.add_argument("--dry-run", action="store_true", help="report downloads/conversions without writing files")
    args = parser.parse_args()

    tag = args.release or latest_release_tag()
    assets = release_assets(tag)
    step_assets = [asset for asset in assets if asset.startswith("mcad-step-b11-") and asset.endswith(".zip")]

    if not step_assets:
        print("error: no mcad-step-b11 assets found in release", file=sys.stderr)
        sys.exit(1)

    OUTLINES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using release: {tag}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for asset in step_assets:
            board_variant = board_variant_from_asset(asset)
            if not board_variant:
                print(f"  skip unknown asset: {asset}")
                continue

            print(f"\n{asset} -> board variant {board_variant}")
            if args.dry_run:
                print(f"  would download {asset}")
                continue

            run(["gh", "release", "download", tag, "--repo", REPO, "--pattern", asset, "--dir", str(tmpdir)])
            zip_path = tmpdir / asset

            with zipfile.ZipFile(zip_path) as zip_file:
                for name in zip_file.namelist():
                    stem = Path(name).stem.upper()
                    dxf_path = outline_destination(stem, board_variant)
                    if dxf_path is None:
                        continue

                    zip_file.extract(name, tmpdir)
                    step_path = tmpdir / name
                    dxf_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"  {name} -> {dxf_path.name}")
                    step_to_pcb_outline(step_path, dxf_path)

    print(f"\nDXF outlines written to {OUTLINES_DIR}")


if __name__ == "__main__":
    main()
