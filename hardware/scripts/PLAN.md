# Generator Scripts Refactor Plan

## Directory Structure

```
hardware/
  b11/
    tools/                          ← b11-specific tools (new)
      config.py
      placement.py                  ← shared helpers (extracted later)
      place-switches.py
      place-leds.py
      place-display-leds.py
    ecad/
      MX/
        ETZ-B11-LSP-5-MX.kicad_pcb
        ETZ-B11-RSP-5-MX.kicad_pcb
        ETZ-B11-LSC-5-MX.kicad_pcb
        ETZ-B11-RSC-5-MX.kicad_pcb
        ETZ-B11-LSP-6-MX.kicad_pcb
        ETZ-B11-RSP-6-MX.kicad_pcb
        ETZ-B11-LSC-6-MX.kicad_pcb
        ETZ-B11-RSC-6-MX.kicad_pcb
      CHOC-V2/
        ETZ-B11-LSP-5-CHOC-V2.kicad_pcb
        ... (same set)
      KS-33/
        ETZ-B11-LSP-5-KS-33.kicad_pcb
        ... (created manually, populated ad-hoc)
  scripts/                          ← generic utils, untouched
    fetch-pcb-outlines.py
    step-to-pcb-outline.py
    step-to-courtyard.py
```

## Naming Convention

PCB files: `ETZ-B11-{L|R}{SP|SC}-{cols}-{FAMILY}`

| Family | Suffix |
|--------|--------|
| MX clones | `MX` |
| Kailh Choc v2 | `CHOC-V2` |
| KS-33 | `KS-33` |

Family parsed from stem: `re.search(r'ETZ-B11-[LR]S[PC]-\d+-(MX|CHOC-V2|KS-33)', stem)`

---

## Phase 1 — Config & Data ✅ in progress

**Goal:** Single source of truth for all placement parameters. No behavior changes yet.

- [x] Create `hardware/b11/tools/config.py`
  - `PITCH_MM = 19.2`
  - `GRID_ORIGINS` — replaces `switch-origins.yaml` (SP: 16.3,16.3 / SC: 14.1,14.1)
  - `SWITCH_FAMILIES` dict (`MX`, `CHOC-V2`, `KS-33`) with socket + LED footprint names
  - `LIB_ROOT`, `ECAD_ROOT`, `MCAD_ROOT` path constants
- [ ] Delete `hardware/b11/mcad/switch-origins.yaml`

---

## Phase 2 — Shared Helpers

**Goal:** Extract duplicated orchestrator/worker boilerplate into `placement.py`.

- [ ] Create `hardware/b11/tools/placement.py` with:
  - `existing_refs(board)` → set of reference strings (non-destructive check)
  - `run_single(pcb_path, worker_fn, *args)` — subprocess dispatch pattern
  - `run_all(targets, worker_fn)` — orchestrator loop

---

## Phase 3 — Rewrite Placement Scripts

**Goal:** Scripts are family-aware, non-destructive, read from config.

- [ ] `place-switches.py` — merges `place-b11-switches-np.py` + `place-b11-switches-lp.py`
  - Glob `ecad/{MX,CHOC-V2,KS-33}/ETZ-B11-*SC-*.kicad_pcb`
  - Parse family from stem → socket footprint from `SWITCH_FAMILIES`
  - Grid origin from `GRID_ORIGINS["SC"]`
  - Skip refs already in board (non-destructive)
- [ ] `place-leds.py` — same pattern for LED footprints on carriers
- [ ] `place-display-leds.py` — fix hardcoded KiCad path only

---

## Phase 4 — Rename & Archive

**Goal:** Filesystem matches new convention, old scripts retired.

- [ ] Create `ecad/MX/`, `ecad/CHOC-V2/` subdirectories
- [ ] Rename 16 PCB files: `*-N → *-MX`, `*-L → *-CHOC-V2`, move into subfolders
- [ ] Archive old scripts → `hardware/scripts/_archive/`
  - `generate-b11-sp-sc.py`
  - `place-b11-switches-np.py`
  - `place-b11-switches-lp.py`
  - `place-b11-leds.py`
  - `place-b11-display-leds.py`

---

## Notes

- Scripts never create PCB files — human creates blank board, scripts populate ad-hoc
- KS-33 socket footprint TBD — placeholder in config until component is selected
- `fetch-pcb-outlines.py`, `step-to-pcb-outline.py`, `step-to-courtyard.py` — untouched
- CI matrix build update deferred until OnShape model is updated with KS-33 values
