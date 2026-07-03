#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Stage KiCad symbols converted from LCSC/EasyEDA models.

This tool intentionally imports symbols only. Footprints and 3D models in this
repo are hand-reviewed project assets and should not be overwritten by vendor
conversions.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VENV = REPO_ROOT / ".venv-lcsc"
DEFAULT_OUTPUT = REPO_ROOT / "build" / "lcsc-symbols" / "lcsc-components"
DEFAULT_IDS = (
    "C39159",  # DRV8837DSGR
    "C527464",  # DRV2605LDGSR
    "C189206",  # KLJ-8530-3627
    "C5280862",  # POGO-HEADER-2X4-P2.54
)


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(cmd: list[str], *, cwd: Path = REPO_ROOT) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_venv(venv_dir: Path) -> Path:
    python = venv_python(venv_dir)
    if not python.exists():
        print(f"Creating virtual environment: {venv_dir}")
        venv.EnvBuilder(with_pip=True).create(venv_dir)

    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "easyeda2kicad"])
    return python


def import_symbols(python: Path, lcsc_ids: tuple[str, ...], output: Path, overwrite: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(python),
        "-m",
        "easyeda2kicad",
        "--symbol",
        "--lcsc_id",
        *lcsc_ids,
        "--output",
        str(output),
    ]
    if overwrite:
        cmd.append("--overwrite")
    run(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "lcsc_ids",
        nargs="*",
        help="LCSC IDs to stage. Defaults to currently selected SP-board parts.",
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=DEFAULT_VENV,
        help=f"Virtual environment path. Default: {DEFAULT_VENV}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Output library path without suffix. "
            f"Default: {DEFAULT_OUTPUT} -> {DEFAULT_OUTPUT}.kicad_sym"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow easyeda2kicad to overwrite symbols in the staging library.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lcsc_ids = tuple(args.lcsc_ids) or DEFAULT_IDS
    if not all(part.startswith("C") and part[1:].isdigit() for part in lcsc_ids):
        print("LCSC IDs must look like C39159.", file=sys.stderr)
        return 2

    python = ensure_venv(args.venv)
    import_symbols(python, lcsc_ids, args.output, args.overwrite)
    print(f"Staged symbols: {args.output}.kicad_sym")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
