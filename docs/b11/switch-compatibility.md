# B11 Switch Compatibility

B11 currently generates separate PCB variants per switch family. The family name is used in ECAD board paths, MCAD PCB outline paths, and MCAD release artifact suffixes.

| Switch family | Compatible switches | Profile | Socket footprint | PCB family |
|---------------|---------------------|---------|------------------|------------|
| MX | Cherry MX and common MX-compatible switches from Kailh, Gateron, and others | Normal | `PG151101S11` | `MX` |
| CHOC-V2 | Kailh Choc v2 / PG1353 | Low | `CPG135001S30` | `CHOC-V2` |
| KS-33 | Gateron KS-33 / KS-2P02B01-01-a | Low | `KS-2P02B01-01-a` | `KS-33` |

Generated B11 switch PCB variants use this layout:

| Family | ECAD boards | PCB outlines | MCAD artifact suffixes |
|--------|-------------|--------------|------------------------|
| MX | `hardware/b11/ecad/MX/` | `hardware/b11/mcad/pcb-outlines/MX/` | `5-MX`, `6-MX` |
| CHOC-V2 | `hardware/b11/ecad/CHOC-V2/` | `hardware/b11/mcad/pcb-outlines/CHOC-V2/` | `5-CHOC-V2`, `6-CHOC-V2` |
| KS-33 | `hardware/b11/ecad/KS-33/` | `hardware/b11/mcad/pcb-outlines/KS-33/` | `5-KS-33`, `6-KS-33` |

All current B11 switch variants use a 19.2 mm x 19.2 mm switch grid pitch. Switch-specific footprints, plate geometry, and board stackups are handled by the B11 PCB generation tools.
