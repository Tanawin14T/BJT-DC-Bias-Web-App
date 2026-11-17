"""DC bias calculations for NPN common-emitter circuits.

Supports three single-supply bias networks: fixed bias (RB), emitter bias
(RB + RE) and voltage-divider bias (R1 + R2 + RE). This module is pure
engineering logic: it must not import Flask, HTML or any web concern. All
resistances enter in kohm and are converted to ohm once, inside this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

KOHM_TO_OHM = 1000.0
VCE_SAT = 0.20

MODES: tuple[str, ...] = ("fixed", "emitter", "divider")

MODE_LABELS: dict[str, str] = {
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
    "divider": "Voltage Divider Bias",
}

MODE_FORMULAS: dict[str, str] = {
    "fixed": "IB = (VCC − VBE) / RB · VE = 0 V (Emitter ต่อกราวด์)",
    "emitter": "IB = (VCC − VBE) / [RB + (β + 1)RE]",
    "divider": "VTH = VCC·R2/(R1+R2) · RTH = R1R2/(R1+R2) · "
               "IB = (VTH − VBE) / [RTH + (β + 1)RE]",
}

# Kept for callers of the Lab 2 API (divider only).
FIELDS: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

ALL_FIELDS: tuple[str, ...] = ("vcc", "rb", "r1", "r2", "rc", "re", "beta", "vbe")

FIELDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "rc", "re", "beta", "vbe"),
    "divider": FIELDS,
}


@dataclass(frozen=True)
class DcBiasInput:
    """Circuit values as entered by the user. Resistances are in kohm.

    ``rb`` and ``mode`` have defaults so Lab 2 call sites that construct a
    divider input with the original seven fields keep working unchanged.
    """

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float
    rb: float = 0.0
    mode: str = "divider"


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


def parse_inputs(raw: Mapping[str, str], mode: str = "divider") -> tuple[DcBiasInput | None, dict[str, str]]:
    """Convert raw form strings into a DcBiasInput, or report per-field errors.

    Only the fields used by the selected mode are validated. Fields belonging
    to another mode are ignored (and stored as zero) so that switching modes
    never produces an error from a stale, hidden textbox.
    """
    if mode not in FIELDS_BY_MODE:
        return None, {"mode": f"โหมดวงจรไม่รู้จัก: {mode}"}

    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for name in FIELDS_BY_MODE[mode]:
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

    for name in FIELDS_BY_MODE[mode]:
        if name not in errors and values[name] <= 0.0:
            errors[name] = "ต้องมากกว่า 0"

    if errors:
        return None, errors

    data: dict[str, float] = {name: 0.0 for name in ALL_FIELDS}
    data.update(values)
    data["mode"] = mode  # type: ignore[assignment]
    return DcBiasInput(**data), {}


def _parameter_warnings(beta: float, vbe: float) -> tuple[str, ...]:
    warnings: tuple[str, ...] = ()
    if beta > 1000.0 or beta < 10.0:
        warnings += (
            f"β = {beta:g} อยู่นอกช่วง 10–1000 ที่แบบจำลองคงที่เหมาะกับงานออกแบบทั่วไป "
            "ผลลัพธ์อาจคลาดเคลื่อนจากของจริง",
        )
    if vbe < 0.5 or vbe > 0.9:
        warnings += (
            f"VBE = {vbe:g} V อยู่นอกช่วง 0.5–0.9 V ของรอยต่อ forward-biased จริง — "
            "ผลลัพธ์ไม่ควรใช้ตัดสินการทำงานของวงจรจริง",
        )
    return warnings


def _solve(inp: DcBiasInput, vth: float, rth_ohm: float, re_ohm: float) -> DcBiasResult:
    """Solve from the Thevenin source seen at the base.

    Divider: VTH/RTH come from R1/R2. Fixed and emitter bias: the base is fed
    from VCC through RB, so VTH = VCC and RTH = RB. Fixed bias has RE = 0.
    """
    vcc = inp.vcc
    rc = inp.rc * KOHM_TO_OHM
    beta = inp.beta
    vbe = inp.vbe

    param_warnings = _parameter_warnings(beta, vbe)

    if vth <= vbe:
        return DcBiasResult(
            vth=vth,
            rth=rth_ohm / KOHM_TO_OHM,
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

    ib = (vth - vbe) / (rth_ohm + (beta + 1.0) * re_ohm)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re_ohm
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if vce <= VCE_SAT or vce < 0.0:
        ic_max_ma = (vcc - VCE_SAT) / (rc + re_ohm) * 1e3
        return DcBiasResult(
            vth=vth,
            rth=rth_ohm / KOHM_TO_OHM,
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
        rth=rth_ohm / KOHM_TO_OHM,
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


def calculate_fixed(inp: DcBiasInput) -> DcBiasResult:
    """RB from VCC to base, emitter tied directly to ground."""
    return _solve(inp, vth=inp.vcc, rth_ohm=inp.rb * KOHM_TO_OHM, re_ohm=0.0)


def calculate_emitter(inp: DcBiasInput) -> DcBiasResult:
    """RB from VCC to base, RE from emitter to ground (single supply)."""
    return _solve(inp, vth=inp.vcc, rth_ohm=inp.rb * KOHM_TO_OHM,
                  re_ohm=inp.re * KOHM_TO_OHM)


def calculate_divider(inp: DcBiasInput) -> DcBiasResult:
    """Lab 2 circuit: R1/R2 divider at the base plus RE at the emitter."""
    r1 = inp.r1 * KOHM_TO_OHM
    r2 = inp.r2 * KOHM_TO_OHM
    re = inp.re * KOHM_TO_OHM
    vth = inp.vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)
    return _solve(inp, vth=vth, rth_ohm=rth, re_ohm=re)


_CALCULATORS = {
    "fixed": calculate_fixed,
    "emitter": calculate_emitter,
    "divider": calculate_divider,
}


def calculate(inp: DcBiasInput) -> DcBiasResult:
    """Dispatch to the calculator selected by ``inp.mode``."""
    try:
        calculator = _CALCULATORS[inp.mode]
    except KeyError as exc:
        raise ValueError(f"โหมดวงจรไม่รู้จัก: {inp.mode}") from exc
    return calculator(inp)
