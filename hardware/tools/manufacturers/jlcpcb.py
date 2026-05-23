"""JLCPCB standard 2-layer fabrication profile."""

NAME = "jlcpcb"

DESIGN_RULES = """\
(version 1)

# ── Copper ──────────────────────────────────────────────────────────────────
(rule "JLCPCB Min Clearance"
   (constraint clearance (min 0.127mm))
)
(rule "JLCPCB Min Track Width"
   (constraint track_width (min 0.127mm))
)

# ── Vias ─────────────────────────────────────────────────────────────────────
(rule "JLCPCB Min Via Drill"
   (constraint hole_size (min 0.3mm))
   (condition "A.Type == 'Via'")
)
(rule "JLCPCB Min Via Annular Ring"
   (constraint annular_width (min 0.13mm))
   (condition "A.Type == 'Via'")
)

# ── Through-hole ─────────────────────────────────────────────────────────────
(rule "JLCPCB Min Drill"
   (constraint hole_size (min 0.2mm))
)
(rule "JLCPCB Hole-to-Hole Clearance"
   (constraint hole_to_hole (min 0.5mm))
)

# ── Board edge ───────────────────────────────────────────────────────────────
(rule "JLCPCB Copper to Board Edge"
   (constraint edge_clearance (min 0.3mm))
)

# ── Silkscreen ───────────────────────────────────────────────────────────────
(rule "JLCPCB Min Silkscreen Width"
   (constraint track_width (min 0.153mm))
   (condition "A.Type == 'Text' || A.Type == 'GraphicShape'")
)
"""


def stackup(total_thickness):
    core_thickness = round(total_thickness - 2 * 0.035 - 2 * 0.01524, 5)
    epsilon_r = 4.43 if total_thickness >= 1.4 else 4.53

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
        '\t\t\t\t(material "JLCPCB Soldermask")\n'
        '\t\t\t\t(epsilon_r 3.8)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "F.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.035)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "dielectric 1"\n'
        '\t\t\t\t(type "core")\n'
        '\t\t\t\t(color "FR4 natural")\n'
        f'\t\t\t\t(thickness {core_thickness})\n'
        '\t\t\t\t(material "Nan Ya Plastics NP-155F Core")\n'
        f'\t\t\t\t(epsilon_r {epsilon_r})\n'
        '\t\t\t\t(loss_tangent 0.02)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Cu"\n'
        '\t\t\t\t(type "copper")\n'
        '\t\t\t\t(thickness 0.035)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Mask"\n'
        '\t\t\t\t(type "Bottom Solder Mask")\n'
        '\t\t\t\t(color "Black")\n'
        '\t\t\t\t(thickness 0.01524)\n'
        '\t\t\t\t(material "JLCPCB Soldermask")\n'
        '\t\t\t\t(epsilon_r 3.8)\n'
        '\t\t\t\t(loss_tangent 0)\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.Paste"\n'
        '\t\t\t\t(type "Bottom Solder Paste")\n'
        '\t\t\t)\n'
        '\t\t\t(layer "B.SilkS"\n'
        '\t\t\t\t(type "Bottom Silk Screen")\n'
        '\t\t\t\t(color "White")\n'
        '\t\t\t)\n'
        '\t\t\t(copper_finish "None")\n'
        '\t\t\t(dielectric_constraints yes)\n'
        '\t\t)'
    )
