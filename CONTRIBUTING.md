# Contributing to etzee

etzee is an open hardware, firmware, and documentation project. Contributions are welcome, but the repo contains generated hardware files, so changes should stay reproducible and scoped.

## Before Opening a Pull Request

1. Keep changes focused on one topic.
2. Do not hand-edit generated B11 PCB content unless the change cannot be represented in tooling yet.
3. Run the relevant checks or dry-runs.
4. Update docs when behavior, naming, generated files, or workflows change.

## Licensing

By contributing, you certify the Developer Certificate of Origin 1.1:

https://developercertificate.org

Sign commits with:

```sh
git commit -s
```

By contributing a change to a file, you agree that the change is licensed under the same license as that file according to `LICENSE.md`.

## B11 PCB Tooling

Use KiCad's bundled Python for pcbnew-based scripts:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/b11/tools/update-pcbs.py --manufacturer jlcpcb --dry-run
```

Useful local checks:

```sh
python3 -m py_compile hardware/b11/tools/*.py hardware/tools/common/*.py hardware/tools/manufacturers/*.py
```

```sh
python3 - <<'PY'
import yaml
from pathlib import Path
for path in ['.github/workflows/mcad-b11.yaml', '.github/workflows/mcad-export.yaml', 'hardware/b11/mcad/parts.yaml']:
    yaml.safe_load(Path(path).read_text())
    print(path)
PY
```

## Generated Files

B11 generated PCB files are expected to be updated through:

```sh
hardware/b11/tools/update-pcbs.py
```

The current generated board naming convention is:

```text
ETZ-B11-{board_code}-{columns}-{switch_family}.kicad_pcb
```

## Issues

Use the issue templates where possible. Include:

- the affected device or module
- expected behavior
- actual behavior
- reproduction steps
- screenshots, KiCad file names, or command output when useful

## Communication

For design discussion and coordination, use the etzee Discord:

https://discord.gg/y3pcSCghcg
