#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

"""Synchronize switch-carrier PCB pad nets from its common schematic."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import ECAD_ROOT


SCHEMATIC_PATH = ECAD_ROOT / "common" / "ETZ-B11-SC.kicad_sch"
TARGET = ECAD_ROOT / "KS-33" / "ETZ-B11-LSC-6-KS-33.kicad_pcb"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def _tokenize(text):
    tokens = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
        elif char in "()":
            tokens.append(char)
            index += 1
        elif char == '"':
            index += 1
            value = []
            while index < len(text) and text[index] != '"':
                if text[index] == "\\" and index + 1 < len(text):
                    index += 1
                value.append(text[index])
                index += 1
            if index >= len(text):
                raise ValueError("unterminated quoted string in netlist")
            tokens.append("".join(value))
            index += 1
        else:
            start = index
            while index < len(text) and not text[index].isspace() and text[index] not in "()":
                index += 1
            tokens.append(text[start:index])
    return tokens


def _parse_sexpr(text):
    stack = []
    root = None
    for token in _tokenize(text):
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise ValueError("multiple root expressions in netlist")
            else:
                root = node
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unexpected closing parenthesis in netlist")
            stack.pop()
        elif not stack:
            raise ValueError("value outside an expression in netlist")
        else:
            stack[-1].append(token)
    if stack or root is None:
        raise ValueError("incomplete netlist expression")
    return root


def _children(node, name):
    return [child for child in node[1:] if isinstance(child, list) and child and child[0] == name]


def _value(node, name, default=None):
    matches = _children(node, name)
    return matches[0][1] if matches and len(matches[0]) > 1 else default


def _read_netlist(path):
    root = _parse_sexpr(path.read_text())
    components_node = _children(root, "components")[0]
    nets_node = _children(root, "nets")[0]

    paths = {}
    for component in _children(components_node, "comp"):
        ref = _value(component, "ref")
        timestamp = _value(component, "tstamps")
        if ref and timestamp:
            paths[ref] = timestamp

    nets = []
    for net in _children(nets_node, "net"):
        name = _value(net, "name")
        if not name or name.startswith("unconnected-("):
            continue
        nodes = []
        for node in _children(net, "node"):
            ref = _value(node, "ref")
            pin = _value(node, "pin")
            if ref and pin:
                nodes.append((ref, pin))
        if nodes:
            nets.append((name, nodes))
    return paths, nets


def _find_or_add_net(board, name):
    import pcbnew

    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def sync(pcb_path, dry_run=False):
    import pcbnew

    if not KICAD_CLI.exists():
        raise RuntimeError(f"KiCad CLI not found at {KICAD_CLI}")

    with tempfile.TemporaryDirectory(prefix="etzee-sc-netlist-") as temp_dir:
        netlist_path = Path(temp_dir) / "ETZ-B11-SC.net"
        subprocess.run(
            [str(KICAD_CLI), "sch", "export", "netlist", "-o", str(netlist_path), str(SCHEMATIC_PATH)],
            check=True,
        )
        schematic_paths, nets = _read_netlist(netlist_path)

    board = pcbnew.LoadBoard(str(pcb_path))
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    schematic_refs = set(schematic_paths)
    missing_refs = sorted(schematic_refs - set(footprints))
    if missing_refs:
        raise RuntimeError("PCB is missing schematic footprints: " + ", ".join(missing_refs))

    for ref in schematic_refs:
        footprint = footprints[ref]
        for pad in footprint.Pads():
            pad.SetNetCode(0)
        footprint.SetPath(pcbnew.KIID_PATH("/" + schematic_paths[ref]))

    assigned = 0
    for name, nodes in nets:
        net = _find_or_add_net(board, name)
        for ref, pin in nodes:
            footprint = footprints.get(ref)
            if footprint is None:
                continue
            pad = next((item for item in footprint.Pads() if item.GetNumber() == pin), None)
            if pad is None:
                raise RuntimeError(f"{ref} has no pad {pin} required by schematic net {name}")
            pad.SetNet(net)
            assigned += 1

    if not dry_run:
        board.Save(str(pcb_path))

    action = "would synchronize" if dry_run else "synchronized"
    print(f"  {Path(pcb_path).name} ({action} {assigned} pads across {len(nets)} nets)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, default=TARGET, help="carrier PCB to update")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sync(args.single, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
