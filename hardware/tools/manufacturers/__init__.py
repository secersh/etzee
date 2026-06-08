# SPDX-License-Identifier: Apache-2.0

"""Manufacturer backend registry."""

from . import jlcpcb, pcbway_hdi

MANUFACTURERS = {
    jlcpcb.NAME: jlcpcb,
    pcbway_hdi.NAME: pcbway_hdi,
}


def choices():
    return sorted(MANUFACTURERS)


def get(name):
    try:
        return MANUFACTURERS[name]
    except KeyError:
        valid = ", ".join(choices())
        raise ValueError(f"unknown manufacturer {name!r}; valid choices: {valid}")
