"""ngspice adapter for the Lab 04 CE voltage-divider amplifier.

Pure Python + standard library only. This module owns three jobs:

1. validate form strings before they can reach a command line or a netlist,
2. generate one netlist per analysis mode (.op / .ac / .tran),
3. run the external ``ngspice`` binary in an isolated directory and parse the
   *real* raw output into values with units.

It never returns a successful result when the engine, the run or the output is
missing. Engineering here comes from ngspice, not from hard-coded traces.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

ANALYSIS_MODES: dict[str, str] = {
    "dc": "DC · Operating Point (.op)",
    "ac": "AC · Frequency Response (.ac)",
    "transient": "Transient · Waveforms (.tran)",
}

# Generic, documented NPN model. It is NOT a claim about a specific transistor
# part number; replace the deck here (and in docs) when a starter kit specifies
# an instructor-verified model.
BJT_MODEL_NAME = "QCE_GENERIC"
BJT_MODEL = (
    ".model QCE_GENERIC NPN(IS=1E-14 BF=200 VAF=100 "
    "RB=10 CJC=3.5P CJE=8P TF=400P)"
)

DEFAULT_SIM_FORM: dict[str, str] = {
    "analysis": "dc",
    "sim_vcc": "12",
    "sim_r1": "100",
    "sim_r2": "22",
    "sim_rc": "2.2",
    "sim_re": "1",
    "sim_rl": "10",
    "sim_cin": "10",
    "sim_cout": "10",
    "amplitude": "0.01",
    "frequency": "1000",
    "fstart": "10",
    "fstop": "1000000",
    "ac_points": "100",
    "tran_stop": "5",
    "model": BJT_MODEL_NAME,
}

# (field, minimum, maximum, inclusive upper bound, Thai label)
_RANGES = (
    ("sim_vcc", 1.0, 100.0, "VCC"),
    ("sim_r1", 0.001, 10000.0, "R1"),
    ("sim_r2", 0.001, 10000.0, "R2"),
    ("sim_rc", 0.001, 10000.0, "RC"),
    ("sim_re", 0.001, 10000.0, "RE"),
    ("sim_rl", 0.001, 10000.0, "RL"),
    ("sim_cin", 0.001, 1000.0, "Cin"),
    ("sim_cout", 0.001, 1000.0, "Cout"),
    ("amplitude", 0.000001, 5.0, "Amplitude"),
    ("frequency", 1.0, 1e9, "Frequency"),
    ("fstart", 1.0, 1e9, "fstart"),
    ("fstop", 1.0, 1e9, "fstop"),
    ("ac_points", 10.0, 20000.0, "AC points"),
    ("tran_stop", 0.01, 1000.0, "Transient stop"),
)
_MODEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")


class SpiceError(Exception):
    """Base class for adapter-internal failures."""


class SpiceEngineError(SpiceError):
    """Engine missing, run failed, timed out, or output unusable."""


@dataclass(frozen=True)
class SpiceInput:
    """Validated circuit values. Resistances kΩ, capacitances µF, time ms."""

    analysis: str
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    amplitude: float
    frequency: float
    fstart: float
    fstop: float
    ac_points: int
    tran_stop: float
    model: str


@dataclass(frozen=True)
class OpResult:
    vb: float
    ve: float
    vc: float
    vce: float
    ic_ma: float


@dataclass(frozen=True)
class AcPoint:
    frequency_hz: float
    gain: float
    phase_deg: float
    vin_mag: float
    vout_mag: float


@dataclass(frozen=True)
class TranPoint:
    time_s: float
    vin_v: float
    vout_v: float


@dataclass
class RawPlot:
    plotname: str
    flags: str
    variables: list[str]
    points: list[list[float | complex]]


@dataclass
class SimulationResult:
    """One complete run. ``ok`` is True only when real output was parsed."""

    ok: bool
    analysis: str
    status: str
    message: str
    errors: dict[str, str] = field(default_factory=dict)
    engine: str = ""
    model: str = ""
    netlist: str = ""
    log: str = ""
    op: OpResult | None = None
    ac: list[AcPoint] | None = None
    tran: list[TranPoint] | None = None
    ac_summary: dict | None = None
    tran_summary: dict | None = None


def validate_inputs(raw: Mapping[str, str]) -> tuple[SpiceInput | None, dict[str, str]]:
    """Return a typed input or per-field errors; never let text reach a netlist."""
    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    analysis = (raw.get("analysis") or "").strip()
    if analysis not in ANALYSIS_MODES:
        errors["analysis"] = "เลือกโหมดวิเคราะห์ไม่ถูกต้อง"

    for name, minimum, maximum, label in _RANGES:
        text = (raw.get(name) or "").strip()
        try:
            value = float(text)
        except (TypeError, ValueError):
            errors[name] = "กรุณากรอกตัวเลข"
            continue
        if not math.isfinite(value):
            errors[name] = "กรุณากรอกตัวเลข"
            continue
        if value <= 0.0:
            errors[name] = "ต้องมากกว่า 0"
        elif not minimum <= value <= maximum:
            errors[name] = f"{label} อยู่นอกช่วงที่รองรับ ({minimum:g}–{maximum:g})"
        else:
            values[name] = value

    model = (raw.get("model") or "").strip() or BJT_MODEL_NAME
    if not _MODEL_RE.match(model):
        errors["model"] = "ชื่อโมเดลใช้ได้เฉพาะตัวอักษร ตัวเลข และ _ (เริ่มด้วยตัวอักษร)"
    else:
        values["model"] = model  # type: ignore[assignment]

    if "fstart" in values and "fstop" in values and values["fstop"] <= values["fstart"]:
        errors["fstop"] = "ต้องมากกว่า fstart"

    if errors:
        return None, errors

    return SpiceInput(
        analysis=analysis,
        vcc=values["sim_vcc"], r1=values["sim_r1"], r2=values["sim_r2"],
        rc=values["sim_rc"], re=values["sim_re"], rl=values["sim_rl"],
        cin=values["sim_cin"], cout=values["sim_cout"],
        amplitude=values["amplitude"], frequency=values["frequency"],
        fstart=values["fstart"], fstop=values["fstop"],
        ac_points=int(values["ac_points"]), tran_stop=values["tran_stop"],
        model=values["model"],  # type: ignore[arg-type]
    ), {}


def _plain_number(value: float) -> str:
    """SPICE-readable decimal text (no 1e+06 style exponent in directives)."""
    if value.is_integer():
        return f"{int(value)}"
    return f"{value:.10g}"


def build_netlist(inp: SpiceInput) -> str:
    """Create a single-analysis netlist for the validated reference circuit."""
    if inp.analysis == "dc":
        directive = ".op"
    elif inp.analysis == "ac":
        directive = (f".ac dec {inp.ac_points} "
                     f"{_plain_number(inp.fstart)} {_plain_number(inp.fstop)}")
    else:
        stop_s = inp.tran_stop / 1000.0
        directive = f".tran {_plain_number(stop_s)} {_plain_number(stop_s / 10.0)}"

    lines = [
        "* CE voltage-divider amplifier — Lab 04 (generated, not hand-edited)",
        f"* Analysis: {inp.analysis} | Vin measured at vb, Vout at out (across RL)",
        "* Coupling capacitors: Cin (source -> base), Cout (collector -> RL)",
        f"VCC vcc 0 DC {inp.vcc:g}",
        f"R1 vcc vb {inp.r1:g}k",
        f"R2 vb 0 {inp.r2:g}k",
        f"RC vcc rcn {inp.rc:g}k",
        "* VIC: zero-volt current probe, i(vic) is the collector current",
        "VIC rcn c DC 0",
        f"Q1 c vb e {inp.model}",
        f"RE e 0 {inp.re:g}k",
        f"CIN in vb {inp.cin:g}u",
        f"COUT c out {inp.cout:g}u",
        f"RL out 0 {inp.rl:g}k",
        f"VIN in 0 AC {inp.amplitude:g} SIN(0 {inp.amplitude:g} {inp.frequency:g})",
        BJT_MODEL if inp.model == BJT_MODEL_NAME else
        f".model {inp.model} NPN(IS=1E-14 BF=200 VAF=100 RB=10 CJC=3.5P CJE=8P TF=400P)",
        directive,
        ".end",
        "",
    ]
    return "\n".join(lines)


def _number(value: float | complex) -> float:
    return value.real if isinstance(value, complex) else float(value)


def parse_raw(text: str) -> RawPlot:
    """Parse ngspice ASCII raw output (real or complex) into arrays."""
    plotname = ""
    flags = ""
    variables: list[str] = []
    rows: list[list[float | complex]] = []
    section = ""

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Variables:"):
            section = "variables"
            continue
        if stripped.startswith("Values:"):
            section = "values"
            continue
        if section == "":
            key, sep, value = stripped.partition(":")
            if sep:
                key = key.strip().lower()
                if key == "plotname":
                    plotname = value.strip()
                elif key == "flags":
                    flags = value.strip()
            continue
        if section == "variables":
            parts = stripped.split()
            if len(parts) >= 2 and parts[0].isdigit():
                variables.append(parts[1].lower())
            continue
        if section == "values":
            parts = stripped.split()
            if not parts or not parts[0].isdigit():
                continue
            raw_values = parts[1:]
            if "complex" in flags.lower():
                row: list[float | complex] = []
                i = 0
                while i < len(raw_values):
                    token = raw_values[i]
                    if token.startswith("("):
                        joined = token
                        while ")" not in joined and i + 1 < len(raw_values):
                            i += 1
                            joined += raw_values[i]
                        match = re.match(r"\(([^,]+),([^)]*)\)", joined)
                        if not match:
                            raise SpiceEngineError("ไม่สามารถอ่านค่ากราฟ AC จาก raw file ได้")
                        row.append(complex(float(match.group(1)), float(match.group(2))))
                    elif "," in token:  # e.g. 1.000e+03,0.0
                        real, _, imag = token.partition(",")
                        row.append(complex(float(real), float(imag)))
                    else:
                        if i + 1 >= len(raw_values):
                            raise SpiceEngineError("ข้อมูล AC complex ไม่ครบคู่ real/imag")
                        row.append(complex(float(token), float(raw_values[i + 1])))
                        i += 1
                    i += 1
                rows.append(row)
            else:
                rows.append([float(token) for token in raw_values])

    if not plotname or not variables or not rows:
        raise SpiceEngineError("raw file ไม่มีข้อมูลกราฟที่อ่านได้ (อาจรัน analysis ไม่สำเร็จ)")
    return RawPlot(plotname=plotname, flags=flags, variables=variables, points=rows)


def _index(plot: RawPlot, name: str) -> int:
    try:
        return plot.variables.index(name)
    except ValueError as exc:
        raise SpiceEngineError(f"raw file ไม่มีตัวแปร {name} ที่ต้องใช้") from exc


def extract_op(plot: RawPlot) -> OpResult:
    last = plot.points[-1]
    vb = _number(last[_index(plot, "v(vb)")])
    ve = _number(last[_index(plot, "v(e)")])
    vc = _number(last[_index(plot, "v(c)")])
    ic = _number(last[_index(plot, "i(vic)")])
    return OpResult(vb=vb, ve=ve, vc=vc, vce=vc - ve, ic_ma=ic * 1e3)


def extract_ac(plot: RawPlot) -> list[AcPoint]:
    fi, vi, oi = _index(plot, "frequency"), _index(plot, "v(vb)"), _index(plot, "v(out)")
    points: list[AcPoint] = []
    for row in plot.points:
        vin, vout = complex(row[vi]), complex(row[oi])
        if abs(vin) == 0.0:  # undefined ratio — never invent a gain value
            continue
        ratio = vout / vin
        phase = math.degrees(math.atan2(ratio.imag, ratio.real))
        points.append(AcPoint(
            frequency_hz=_number(row[fi]), gain=abs(ratio), phase_deg=phase,
            vin_mag=abs(vin), vout_mag=abs(vout),
        ))
    if not points:
        raise SpiceEngineError("ไม่มีจุด AC ที่คำนวณ Gain ได้จาก raw file")
    return points


def extract_tran(plot: RawPlot) -> list[TranPoint]:
    ti, vi, oi = _index(plot, "time"), _index(plot, "v(vb)"), _index(plot, "v(out)")
    points = [TranPoint(
        time_s=_number(row[ti]), vin_v=_number(row[vi]), vout_v=_number(row[oi]),
    ) for row in plot.points]
    if not points:
        raise SpiceEngineError("raw file ไม่มีจุดเวลา Transient")
    if len(points) > 2000:  # keep SVG light without changing the simulation
        step = math.ceil(len(points) / 2000)
        points = points[::step] + ([points[-1]] if (len(points) - 1) % step else [])
    return points


def ac_summary(points: list[AcPoint]) -> dict:
    peak = max(points, key=lambda p: p.gain)
    reference = points[0].gain
    cutoff = next((p for p in points if p.gain <= reference / math.sqrt(2.0)), None)
    return {
        "max_gain": peak.gain,
        "f_at_max_gain": peak.frequency_hz,
        "f_3db": cutoff.frequency_hz if cutoff else None,
        "gain_at_start": reference,
    }


def tran_summary(points: list[TranPoint]) -> dict:
    vin_peak = max(abs(p.vin_v) for p in points)
    vout_peak = max(abs(p.vout_v) for p in points)
    mean_in = sum(p.vin_v for p in points) / len(points)
    mean_out = sum(p.vout_v for p in points) / len(points)
    covariance = sum((p.vin_v - mean_in) * (p.vout_v - mean_out) for p in points)
    inverted = covariance < 0.0
    return {
        "vin_peak_v": vin_peak,
        "vout_peak_v": vout_peak,
        "gain_estimate": vout_peak / vin_peak if vin_peak else None,
        "inverted": inverted,
        "phase_note": "กลับเฟส (~180°)" if inverted else "ไม่กลับเฟสในช่วงที่วัด",
    }


def _log_excerpt(*texts: str) -> str:
    combined = "\n".join(t for t in texts if t).strip()
    return combined[-2000:]


def run_simulation(
    raw_form: Mapping[str, str], *, engine: str | None = None, timeout: float = 30.0,
) -> SimulationResult:
    """Validate, run ngspice once, and return parsed values or a clear error."""
    analysis = (raw_form.get("analysis") or "dc").strip()
    inp, errors = validate_inputs(raw_form)
    if errors:
        return SimulationResult(
            ok=False, analysis=analysis, status="error",
            message="ข้อมูลในฟอร์มไม่ถูกต้อง กรุณาแก้ตามข้อความด้านล่าง",
            errors=errors,
        )

    executable = engine or os.environ.get("NGSPICE_PATH") or shutil.which("ngspice")
    if not executable:
        return SimulationResult(
            ok=False, analysis=inp.analysis, status="error",
            message="ไม่พบ ngspice — ตรวจ PATH หรือตั้งค่า NGSPICE_PATH แล้วลองใหม่",
            engine="", model=inp.model,
        )

    netlist = build_netlist(inp)
    try:
        with tempfile.TemporaryDirectory(prefix="bjt-spice-") as workdir:
            directory = Path(workdir)
            (directory / "circuit.cir").write_text(netlist, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [executable, "-b", "-o", "run.log", "-r", "run.raw", "circuit.cir"],
                    cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, timeout=timeout, check=False,
                )
            except subprocess.TimeoutExpired:
                return SimulationResult(
                    ok=False, analysis=inp.analysis, status="error",
                    message=f"ngspice timeout: การจำลองใช้เวลาเกิน {timeout:g} วินาที",
                    engine=executable, model=inp.model, netlist=netlist,
                )
            except OSError as exc:
                return SimulationResult(
                    ok=False, analysis=inp.analysis, status="error",
                    message=f"เรียก ngspice ไม่ได้: {exc}",
                    engine=executable, model=inp.model, netlist=netlist,
                )

            log_path = directory / "run.log"
            log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            if proc.returncode != 0:
                return SimulationResult(
                    ok=False, analysis=inp.analysis, status="error",
                    message="ngspice รันไม่สำเร็จ (return code "
                            f"{proc.returncode}): {_log_excerpt(log_text, proc.stderr, proc.stdout)}",
                    engine=executable, model=inp.model, netlist=netlist,
                    log=_log_excerpt(log_text, proc.stderr, proc.stdout),
                )

            raw_path = directory / "run.raw"
            if not raw_path.exists() or raw_path.stat().st_size == 0:
                return SimulationResult(
                    ok=False, analysis=inp.analysis, status="error",
                    message="ngspice ไม่ได้เขียนไฟล์ผล (run.raw ว่างหรือไม่มี) — "
                            f"{_log_excerpt(log_text, proc.stderr)}",
                    engine=executable, model=inp.model, netlist=netlist,
                    log=_log_excerpt(log_text, proc.stderr),
                )

            plot = parse_raw(raw_path.read_text(encoding="utf-8", errors="replace"))
            result = SimulationResult(
                ok=True, analysis=inp.analysis, status="success",
                message="รัน ngspice สำเร็จ และอ่านผลจาก raw file จริง",
                engine=executable, model=inp.model, netlist=netlist,
                log=_log_excerpt(log_text, proc.stderr),
            )
            if inp.analysis == "dc":
                result.op = extract_op(plot)
            elif inp.analysis == "ac":
                result.ac = extract_ac(plot)
                result.ac_summary = ac_summary(result.ac)
            else:
                result.tran = extract_tran(plot)
                result.tran_summary = tran_summary(result.tran)
            return result
    except SpiceError as exc:
        return SimulationResult(
            ok=False, analysis=inp.analysis, status="error", message=str(exc),
            engine=executable, model=inp.model, netlist=netlist,
        )
