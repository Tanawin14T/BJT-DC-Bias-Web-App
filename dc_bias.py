"""DC bias calculations for a BJT common-emitter voltage-divider bias circuit.

This module is pure engineering logic: it must not import Flask, HTML or any
web concern. All resistances enter in kohm and are converted to ohm once,
inside this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

KOHM_TO_OHM = 1000.0
VCE_SAT = 0.20

FIELDS: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")


@dataclass(frozen=True)
class DcBiasInput:
    """Circuit values as entered by the user. Resistances are in kohm."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class DcBiasResult:
    """DC operating point plus the assumptions it was computed under."""

    vth: float
    rth: float
    ib_ua: float
    ic_ma: float
    ie_ma: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]


def calculate(inp: DcBiasInput) -> DcBiasResult:
    """Compute the DC operating point under the fixed-beta forward-active model."""
    vcc = inp.vcc
    r1 = inp.r1 * KOHM_TO_OHM
    r2 = inp.r2 * KOHM_TO_OHM
    rc = inp.rc * KOHM_TO_OHM
    re = inp.re * KOHM_TO_OHM
    beta = inp.beta
    vbe = inp.vbe

    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    ib = (vth - vbe) / (rth + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    return DcBiasResult(
        vth=vth,
        rth=rth / KOHM_TO_OHM,
        ib_ua=ib * 1e6,
        ic_ma=ic * 1e3,
        ie_ma=ie * 1e3,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region="Forward Active",
        warnings=(),
    )
