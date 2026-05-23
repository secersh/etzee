# etzee License

The etzee repository contains hardware designs, firmware/software, documentation, and supporting assets.

Project-authored material uses a lean two-license model:

- Hardware design source is licensed under CERN Open Hardware Licence Version 2 - Strongly Reciprocal (`CERN-OHL-S-2.0`).
- Everything else is licensed under Apache License 2.0 (`Apache-2.0`) unless a file states otherwise.

## License Map

| Material | Path examples | License |
|----------|---------------|---------|
| Hardware source, PCB designs, schematics, footprints, MCAD source, 3D models, and manufacturing source files | `hardware/**/*.kicad_pcb`, `hardware/**/*.kicad_pro`, `hardware/**/*.kicad_dru`, `hardware/**/*.dxf`, `hardware/**/*.step`, `hardware/**/*.stp`, `lib/*.pretty/`, `lib/3d-models/` | CERN Open Hardware Licence Version 2 - Strongly Reciprocal (`CERN-OHL-S-2.0`) |
| Firmware, scripts, protocol/software implementations, CI/tooling code, configuration, documentation, and repository text | `firmware/`, `hardware/**/*.py`, `.github/`, `docs/`, `README.md`, `*.md`, `*.yaml`, `*.yml`, `*.toml`, `requirements.txt` | Apache License 2.0 (`Apache-2.0`) |

Generated manufacturing outputs inherit the license of the source material used to generate them unless explicitly stated otherwise.

## Attribution

Copyright belongs to the etzee project authors.

The etzee project is owned and maintained by its founders as peers. Current founder-maintainers are listed in `MAINTAINERS.md`.

When redistributing or modifying this work, preserve license notices and attribute the etzee project and relevant contributors.

## License Texts

The full legal texts are included in this repository:

- `LICENSES/Apache-2.0.txt`
- `LICENSES/CERN-OHL-S-2.0.txt`

## Trademarks and Identity

The licenses above do not grant trademark rights in the etzee name, logos, visual identity, or branding marks except as required for reasonable attribution.

Forks and modified distributions should use a distinct project name unless they are clearly presented as unmodified etzee releases.
