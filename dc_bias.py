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


def parse_inputs(raw: Mapping[str, str]) -> tuple[DcBiasInput | None, dict[str, str]]:
    """Convert raw form strings into a DcBiasInput, or report per-field errors."""
    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for name in FIELDS:
        text = (raw.get(name) or "").strip()
        if not text:
            errors[name] = "กรุณากรอกตัวเลข"
            continue
        try:
            value = float(text)
        except ValueError:
            errors[name] = "กรุณากรอกตัวเลข"
            continue
        if not math.isfinite(value):
            errors[name] = "กรุณากรอกตัวเลข"
            continue
        values[name] = value

    for name in FIELDS:
        if name not in errors and values[name] <= 0.0:
            errors[name] = "ต้องมากกว่า 0"

    if errors:
        return None, errors

    return DcBiasInput(**values), {}


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

    param_warnings: tuple[str, ...] = ()
    if beta > 1000.0 or beta < 10.0:
        param_warnings += (
            f"β = {beta:g} อยู่นอกช่วง 10–1000 ที่แบบจำลองคงที่เหมาะกับงานออกแบบทั่วไป "
            "ผลลัพธ์อาจคลาดเคลื่อนจากของจริง",
        )
    if vbe < 0.5 or vbe > 0.9:
        param_warnings += (
            f"VBE = {vbe:g} V อยู่นอกช่วง 0.5–0.9 V ของรอยต่อ forward-biased จริง — "
            "ผลลัพธ์ไม่ควรใช้ตัดสินการทำงานของวงจรจริง",
        )

    if vth <= vbe:
        return DcBiasResult(
            vth=vth,
            rth=rth / KOHM_TO_OHM,
            ib_ua=0.0,
            ic_ma=0.0,
            ie_ma=0.0,
            vb=vth,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            region="Cutoff",
            warnings=(
                "Cutoff: VTH ≤ VBE ทำให้ไม่มีกระแสเบสไหล — "
                "แบบจำลอง Forward Active ใช้ไม่ได้ในโหมดนี้",
            )
            + param_warnings,
        )

    ib = (vth - vbe) / (rth + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if vce <= VCE_SAT or vce < 0.0:
        ic_max_ma = (vcc - VCE_SAT) / (rc + re) * 1e3
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
            region="Saturation",
            warnings=(
                f"Saturation: VCE ≤ {VCE_SAT:g} V — สมการ IC = β·IB ใช้ไม่ได้ในโหมดนี้ "
                f"กระแสอิ่มตัวสูงสุดประมาณ IC,max ≈ {ic_max_ma:.2f} mA",
            )
            + param_warnings,
        )

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
        warnings=param_warnings,
    )
