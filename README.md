# etzee

etzee is an open modular input-device ecosystem. It combines keyboards, utility modules, magnetic pogo-pin connectors, local displays, haptics, and firmware that can discover and communicate across connected modules.

The project is early and hardware-heavy. The current active board is B11; M0 and M9 are planned modules.

## Devices

| Device | Type | Status | Notes |
|--------|------|--------|-------|
| B11 | Primary keyboard board | Active | Split or monoblock keyboard, 5/6 columns per half, switch-family PCB variants |
| M0 | Module | Planned | USB-C module with haptic dial and round touch display |
| M9 | Module | Planned | USB-C 3x3 mechanical keypad with display |

## B11

B11 is the first primary etzee keyboard. Current design goals:

- split or monoblock use
- Bluetooth-first firmware target
- hot-swappable switch carriers
- integrated dot-matrix display on switch plates
- south-facing per-key LEDs
- magnetic pogo-pin module connectors
- 5-column and 6-column half variants
- MX, Choc v2, and KS-33 switch-family variants
- generated KiCad PCB files from tracked MCAD-derived outlines

Current B11 docs:

- [switch compatibility](docs/b11/switch-compatibility.md)
- [switch profiles](docs/b11/switch-profiles.md)
- [keycap compatibility](docs/b11/keycap-compatibility.md)

## Repository Layout

```text
.github/workflows/          GitHub Actions workflows
docs/b11/                   B11 hardware compatibility and profile docs
docs/firmware/              firmware and protocol docs
firmware/                   firmware workspaces
hardware/b11/ecad/          B11 KiCad projects and generated boards
hardware/b11/mcad/          B11 MCAD export config and PCB outlines
hardware/b11/tools/         B11 PCB generation/update tools
hardware/tools/             shared hardware tooling
lib/                        shared KiCad footprints, 3D models, datasheets
```

## Generated PCB Workflow

B11 generated boards are updated through one batch script:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/b11/tools/update-pcbs.py --manufacturer jlcpcb --dry-run
```

Remove `--dry-run` to update generated PCB files locally. The updater can generate PCB outlines, place switch sockets, place switch LEDs, place display LEDs, apply manufacturer stackups, and generate manufacturer design rules.

Current generated B11 PCB variants:

| Family | Columns | Boards |
|--------|---------|--------|
| MX | 5, 6 | `LSP`, `RSP`, `LSC`, `RSC` |
| CHOC-V2 | 5, 6 | `LSP`, `RSP`, `LSC`, `RSC` |
| KS-33 | 5, 6 | `LSP`, `RSP`, `LSC`, `RSC` |

Board names use:

```text
ETZ-B11-{board_code}-{columns}-{switch_family}.kicad_pcb
```

Example:

```text
ETZ-B11-LSP-5-KS-33.kicad_pcb
```

## MCAD Exports

B11 MCAD export inputs are defined in [hardware/b11/mcad/parts.yaml](hardware/b11/mcad/parts.yaml). The GitHub workflow exports common parts once and matrix parts once per board variant:

- `5-MX`, `6-MX`
- `5-CHOC-V2`, `6-CHOC-V2`
- `5-KS-33`, `6-KS-33`

PCB outline DXFs live under:

```text
hardware/b11/mcad/pcb-outlines/{MX,CHOC-V2,KS-33}/
```

## Firmware

Firmware is based around ZMK-compatible targets. The htoyto protocol is the project-specific communication concept for inter-module discovery and messaging.

- [htoyto protocol overview](docs/firmware/htoyto.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: keep generated files reproducible, keep hardware changes scoped, and run the relevant dry-runs before opening a pull request.

For discussion and implementation feedback, join the etzee Discord:

https://discord.gg/y3pcSCghcg

## License

This repository uses different open licenses for different material types. See [LICENSE.md](LICENSE.md) for the full licensing map.
