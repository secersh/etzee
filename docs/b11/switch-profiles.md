# B11 Switch Profiles

Mechanical stackup parameters per B11 switch family. These values drive the OnShape switch-family configurations and the generated PCB variants.

| Parameter | MX | CHOC-V2 | KS-33 |
|-----------|----|---------|-------|
| Switch plate mechanical thickness (mm) | 1.5-1.9 | 1.65 | 1.2 |
| Switch plate PCB order thickness (mm) | 1.6 | 1.6 | 1.2 |
| Carrier board mechanical thickness (mm) | 1.6 | 1.6 | 1.5-1.6 |
| Carrier board PCB order thickness (mm) | 1.6 | 1.6 | 1.6 |
| Top plate to top carrier offset (mm) | 5.0 | 2.2 | 2.5 |

The PCB order thickness rows are the rounded manufacturer thicknesses used by `hardware/b11/tools/config.py`.

Offset is the vertical distance from the top surface of the switch plate to the top surface of the carrier board.
