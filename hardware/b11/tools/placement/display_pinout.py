# SPDX-License-Identifier: Apache-2.0

"""Shared B11 display LED driver and DSP edge-connector pinout data."""

# IS31FL3741A QFN-60 pin names, from the Lumissil IS31FL3741A datasheet
# pin configuration. Pad 61 is the exposed pad and should be tied to GND.
IS31FL3741A_PINS = {
    1: "LED_CS34",
    2: "LED_CS35",
    3: "LED_CS36",
    4: "LED_CS37",
    5: "LED_CS38",
    6: "LED_CS39",
    7: "INTB",
    8: "ADDR",
    9: "SDA",
    10: "SCL",
    11: "SDB",
    12: "GND",
    13: "ISET",
    14: "AVCC",
    15: "PVCC",
    16: "LED_SW1",
    17: "LED_SW2",
    18: "LED_SW3",
    19: "LED_SW4",
    20: "LED_SW5",
    21: "LED_SW6",
    22: "LED_SW7",
    23: "LED_SW8",
    24: "LED_SW9",
    25: "PVCC",
    26: "LED_CS1",
    27: "LED_CS2",
    28: "LED_CS3",
    29: "LED_CS4",
    30: "LED_CS5",
    31: "LED_CS6",
    32: "LED_CS7",
    33: "LED_CS8",
    34: "LED_CS9",
    35: "LED_CS10",
    36: "GND",
    37: "LED_CS11",
    38: "LED_CS12",
    39: "LED_CS13",
    40: "LED_CS14",
    41: "LED_CS15",
    42: "LED_CS16",
    43: "LED_CS17",
    44: "LED_CS18",
    45: "LED_CS19",
    46: "LED_CS20",
    47: "LED_CS21",
    48: "LED_CS22",
    49: "LED_CS23",
    50: "LED_CS24",
    51: "LED_CS25",
    52: "LED_CS26",
    53: "LED_CS27",
    54: "LED_CS28",
    55: "GND",
    56: "LED_CS29",
    57: "LED_CS30",
    58: "LED_CS31",
    59: "LED_CS32",
    60: "LED_CS33",
    61: "GND",
}


# Rev1 DSP castellated LED edge pinout, optimized for fanout from an
# IS31FL3741A placed near the center/right of the SP board. Pads walk
# counter-clockwise around the side castellations. The groups are:
#   1..11   left/top
#   12..23  left/bottom
#   24..35  right/bottom
#   36..46  right/top
#
# The map is mirrored left-to-right so the SP-side driver can fan out mostly
# toward the nearer right-side castellated groups. SW8/SW9 are intentionally
# unused for the 7-column DSP.
DSP_EDGE_PINOUT = {
    1: "LED_CS29",
    2: "LED_CS28",
    3: "LED_CS27",
    4: "LED_CS26",
    5: "LED_CS25",
    6: "LED_CS24",
    7: "LED_CS23",
    8: "LED_CS22",
    9: "LED_CS21",
    10: "LED_CS20",
    11: "LED_CS19",
    12: "LED_CS18",
    13: "LED_CS16",
    14: "LED_CS15",
    15: "LED_CS14",
    16: "LED_CS13",
    17: "LED_CS12",
    18: "LED_CS11",
    19: "LED_CS10",
    20: "LED_CS9",
    21: "LED_CS8",
    22: "LED_CS7",
    23: "LED_CS6",
    24: "LED_CS5",
    25: "LED_CS4",
    26: "LED_CS3",
    27: "LED_CS2",
    28: "LED_CS1",
    29: "LED_SW7",
    30: "LED_SW6",
    31: "LED_SW5",
    32: "LED_SW4",
    33: "LED_SW3",
    34: "LED_SW2",
    35: "LED_SW1",
    36: "LED_CS17",
    37: "LED_CS39",
    38: "LED_CS38",
    39: "LED_CS37",
    40: "LED_CS36",
    41: "LED_CS35",
    42: "LED_CS34",
    43: "LED_CS33",
    44: "LED_CS32",
    45: "LED_CS31",
    46: "LED_CS30",
}


ALS_EDGE_PINOUT = {
    1: "ALS_VDD",
    2: "ALS_SCL",
    3: "ALS_SDA",
    4: "ALS_GND",
}
