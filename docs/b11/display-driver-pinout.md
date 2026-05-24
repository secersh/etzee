<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# B11 Display Driver Pinout

The B11 display matrix uses an IS31FL3741A LED driver and a 39 x 7 active LED
matrix. The driver supports 39 CS lines and 9 SW lines; `SW8` and `SW9` are
unused on the rev1 DSP module.

## IS31FL3741A Matrix Pins

The IS31FL3741A QFN-60 matrix pins are clustered like this:

| Package area | Pins | Nets |
| --- | --- | --- |
| Left/top side | 1-6 | `LED_CS34` .. `LED_CS39` |
| Bottom side | 16-24 | `LED_SW1` .. `LED_SW9` |
| Bottom/right corner | 26-30 | `LED_CS1` .. `LED_CS5` |
| Right side | 31-35, 37-45 | `LED_CS6` .. `LED_CS19` |
| Top/right side | 46-54, 56-60 | `LED_CS20` .. `LED_CS33` |

Pins `7`-`15`, `25`, `36`, `55`, and exposed pad `61` are driver control,
power, or ground pins and are not routed through the DSP edge connector.

## DSP Edge Connector

The rev1 DSP edge connector has four 12-pad castellated groups:

| Edge pads | Physical group | Nets |
| --- | --- | --- |
| 1-12 | left/top | `LED_CS29` .. `LED_CS18` |
| 13-24 | left/bottom | `LED_CS17` .. `LED_CS6` |
| 25-36 | right/top | `LED_CS30` .. `LED_CS39`, `NC`, `NC` |
| 37-48 | right/bottom | `LED_SW1` .. `LED_SW7`, `LED_CS1` .. `LED_CS5` |

This package-oriented map is intended to make SP-side fanout from the
IS31FL3741A easier. The map is mirrored left-to-right so the driver can sit
near the center/right of the SP board and fan out mostly to the nearer
right-side castellated groups.

The source of truth for generated tooling is
`hardware/b11/tools/placement/display_pinout.py`.
