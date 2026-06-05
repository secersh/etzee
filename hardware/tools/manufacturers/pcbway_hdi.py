# SPDX-License-Identifier: Apache-2.0

"""PCBWay HDI fabrication profile for dense B11 display PCBs."""

NAME = "pcbway_hdi"

# Conservative starting rules from PCBWay's published advanced/HDI capability
# tables. These are intended for DFM/routing work, not a substitute for a
# project-specific stackup approval from PCBWay.
#
# Baseline advanced rules:
#   - 0.065/0.065 mm trace/space
#   - 0.15 mm mechanical finished hole
#   - 3 mil annular ring
#   - 4 mil laser holes as standard; 3 mil requires evaluation
# HDI laser blind/buried vias require PCBWay confirmation of the exact buildup,
# dielectric thickness, and via fill/capping requirements.
DESIGN_RULES = """\
(version 1)

# ── Copper ──────────────────────────────────────────────────────────────────
(rule "PCBWay HDI Min Clearance"
   (constraint clearance (min 0.065mm))
)
(rule "PCBWay HDI Min Track Width"
   (constraint track_width (min 0.065mm))
)

# ── Laser microvias ─────────────────────────────────────────────────────────
(rule "PCBWay HDI Min Laser Via Drill"
   (constraint hole_size (min 0.1016mm))
   (condition "A.Type == 'Via'")
)
(rule "PCBWay HDI Min Laser Via Annular Ring"
   (constraint annular_width (min 0.075mm))
   (condition "A.Type == 'Via'")
)

# ── Through-hole and castellated pads ───────────────────────────────────────
(rule "PCBWay HDI Min Mechanical Drill"
   (constraint hole_size (min 0.15mm))
   (condition "A.Type != 'Via'")
)
(rule "PCBWay HDI Hole-to-Hole Clearance"
   (constraint hole_to_hole (min 0.50mm))
)

# ── Board edge ───────────────────────────────────────────────────────────────
(rule "PCBWay HDI Copper to Board Edge"
   (constraint edge_clearance (min 0.30mm))
   (condition "A.Reference != 'J1' && A.Reference != 'J_ALS1'")
)

# ── Silkscreen ───────────────────────────────────────────────────────────────
(rule "PCBWay HDI Min Silkscreen Width"
   (constraint track_width (min 0.153mm))
   (condition "A.Type == 'Text' || A.Type == 'GraphicShape'")
)
"""


def stackup(total_thickness):
    if abs(total_thickness - 0.4) > 0.001:
        raise ValueError("pcbway_hdi profile currently expects 0.4mm total thickness")

    return (
        '\t\t(stackup\n'
        '\t\t\t(layer "F.SilkS"\n'
        '\t\t\t\t(type "Top Silk Screen")\n'
        '\t\t\t\t(color "White")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Paste"\n'
        '\t\t\t\t(type "Top Solder Paste")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Mask"\n'
        '\t\t\t\t(type "Top Solder Mask")\n'
        '\t\t\t\t(color "Black")\n'
        '\t\t\t\t(thickness 0.01524)\n'
        '\t\t\t\t(material "PCBWay soldermask")\n'
        '\t\t\t\t(epsilon_r 3.3)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.018)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "dielectric 1"\n'
        '\t\t\t\t(type "prepreg")\n'
        '\t\t\t\t(color "PTFE natural")\n'
        '\t\t\t\t(thickness 0.065)\n'
        '\t\t\t\t(material "HDI prepreg, confirm with PCBWay")\n'
        '\t\t\t\t(epsilon_r 4.5)\n'
        '\t\t\t\t(loss_tangent 0.02)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "In1.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.018)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "dielectric 2"\n'
        '\t\t\t\t(type "core")\n'
        '\t\t\t\t(color "FR4 natural")\n'
        '\t\t\t\t(thickness 0.16752)\n'
        '\t\t\t\t(material "HDI core, confirm with PCBWay")\n'
        '\t\t\t\t(epsilon_r 4.5)\n'
        '\t\t\t\t(loss_tangent 0.02)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "In2.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.018)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "dielectric 3"\n'
        '\t\t\t\t(type "prepreg")\n'
        '\t\t\t\t(color "PTFE natural")\n'
        '\t\t\t\t(thickness 0.065)\n'
        '\t\t\t\t(material "HDI prepreg, confirm with PCBWay")\n'
        '\t\t\t\t(epsilon_r 4.5)\n'
        '\t\t\t\t(loss_tangent 0.02)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.018)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Mask"\n'
        '\t\t\t\t(type "Bottom Solder Mask")\n'
        '\t\t\t\t(color "Black")\n'
        '\t\t\t\t(thickness 0.01524)\n'
        '\t\t\t\t(material "PCBWay soldermask")\n'
        '\t\t\t\t(epsilon_r 3.3)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Paste"\n'
        '\t\t\t\t(type "Bottom Solder Paste")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.SilkS"\n'
        '\t\t\t\t(type "Bottom Silk Screen")\n'
        '\t\t\t\t(color "White")\n'
        '\t\t\t)\n'
        '\t\t\t(copper_finish "ENIG")\n'
        '\t\t\t(dielectric_constraints yes)\n'
        '\t\t)'
    )
