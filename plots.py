"""Server-side SVG plots built from parsed ngspice data.

No chart library and no JavaScript physics: the browser only displays the
scaled coordinates produced here. Every axis carries a unit.
"""

from __future__ import annotations

import math

from spice_engine import AcPoint, TranPoint

_W, _H = 760, 300
_LEFT, _RIGHT, _TOP, _BOTTOM = 70, 18, 18, 46


def _scale(value: float, low: float, high: float, start: float, end: float) -> float:
    if high == low:
        return (start + end) / 2.0
    return start + (value - low) / (high - low) * (end - start)


def _polyline(rows: list[tuple[float, float]], xmap, ymap, color: str) -> str:
    if not rows:
        return ""
    points = " ".join(f"{xmap(x):.2f},{ymap(y):.2f}" for x, y in rows)
    return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>'


def _frame(x_label: str, y_labels: list[str], x_ticks: list[tuple[float, str]],
           y_ticks: list[tuple[float, str]], xmap, ymap, height: int = _H) -> str:
    inner_bottom = height - _BOTTOM
    parts = [
        f'<svg viewBox="0 0 {_W} {height}" width="100%" role="img" '
        f'aria-label="ngspice กราฟ: {x_label}" style="max-width:100%;height:auto">',
        f'<rect x="0" y="0" width="{_W}" height="{height}" fill="#fbfdff"/>',
        f'<line x1="{_LEFT}" y1="{_TOP}" x2="{_LEFT}" y2="{inner_bottom}" stroke="#7d97a9" stroke-width="1.3"/>',
        f'<line x1="{_LEFT}" y1="{inner_bottom}" x2="{_W - _RIGHT}" y2="{inner_bottom}" '
        'stroke="#7d97a9" stroke-width="1.3"/>',
    ]
    for value, label in x_ticks:
        x = xmap(value)
        parts.append(f'<line x1="{x:.2f}" y1="{_TOP}" x2="{x:.2f}" y2="{inner_bottom}" '
                     'stroke="#e2ebf2" stroke-width="1"/>')
        parts.append(f'<text x="{x:.2f}" y="{inner_bottom + 17}" font-size="11" fill="#486275" '
                     f'text-anchor="middle">{label}</text>')
    for value, label in y_ticks:
        y = ymap(value)
        parts.append(f'<line x1="{_LEFT}" y1="{y:.2f}" x2="{_W - _RIGHT}" y2="{y:.2f}" '
                     'stroke="#e2ebf2" stroke-width="1"/>')
        parts.append(f'<text x="{_LEFT - 8}" y="{y + 4:.2f}" font-size="11" fill="#486275" '
                     f'text-anchor="end">{label}</text>')
    parts.append(f'<text x="{(_W + _LEFT) / 2:.1f}" y="{height - 6}" font-size="12" '
                 f'fill="#264c6f" text-anchor="middle">{x_label}</text>')
    for idx, label in enumerate(y_labels):
        parts.append(f'<text x="{_LEFT + 6 + idx * 120}" y="{_TOP + 13}" font-size="11" '
                     f'fill="#486275">{label}</text>')
    return "\n".join(parts)


def ac_plot(points: list[AcPoint]) -> str:
    """Two stacked panels: |gain| in dB and phase in degrees vs log frequency."""
    if not points:
        return '<p class="note">ไม่มีข้อมูล AC จาก ngspice จะแสดงกราฟ</p>'

    xs = [math.log10(max(p.frequency_hz, 1e-12)) for p in points]
    db = [20.0 * math.log10(max(p.gain, 1e-12)) for p in points]
    xmin, xmax = min(xs), max(xs)
    dmin, dmax = min(db) - 3.0, max(db) + 3.0
    pmin, pmax = min(p.phase_deg for p in points) - 10.0, max(p.phase_deg for p in points) + 10.0
    if pmax - pmin < 20.0:
        pmin, pmax = pmin - 10.0, pmax + 10.0

    xmap = lambda x: _scale(x, xmin, xmax, _LEFT, _W - _RIGHT)
    dbmap = lambda y: _scale(y, dmin, dmax, _H - _BOTTOM, _TOP + 8)
    pmap = lambda y: _scale(y, pmin, pmax, _H - _BOTTOM, _TOP + 8)

    x_ticks = []
    for i in range(5):
        value = xmin + (xmax - xmin) * i / 4.0
        hz = 10 ** value
        label = f"{hz:.2g}" if hz < 1e5 else f"{hz:.1e}"
        x_ticks.append((value, label))

    magnitude = [
        _frame("Frequency (Hz)", ["Gain (dB) · Vout/Vin"], x_ticks,
               [(v, f"{v:.0f}") for v in (dmin, (dmin + dmax) / 2, dmax)],
               xmap, dbmap),
        _polyline(list(zip(xs, db)), xmap, dbmap, "#0c8176"),
        "</svg>",
    ]
    phase = [
        _frame("Frequency (Hz)", ["Phase (deg) · Vout/Vin"], x_ticks,
               [(v, f"{v:.0f}") for v in (pmin, (pmin + pmax) / 2, pmax)],
               xmap, pmap),
        _polyline(list(zip(xs, [p.phase_deg for p in points])), xmap, pmap, "#b1692e"),
        "</svg>",
    ]
    return "\n".join(magnitude + phase)


def tran_plot(points: list[TranPoint]) -> str:
    """Vin / Vout versus time in milliseconds, from real .tran samples."""
    if not points:
        return '<p class="note">ไม่มีข้อมูล Transient จาก ngspice จะแสดงกราฟ</p>'

    times = [p.time_s * 1e3 for p in points]
    tmin, tmax = min(times), max(times)
    values = [v for p in points for v in (p.vin_v, p.vout_v)]
    vmin, vmax = min(values), max(values)
    pad = max((vmax - vmin) * 0.1, 1e-4)
    vmin, vmax = vmin - pad, vmax + pad

    xmap = lambda x: _scale(x, tmin, tmax, _LEFT, _W - _RIGHT)
    ymap = lambda y: _scale(y, vmin, vmax, _H - _BOTTOM, _TOP + 6)

    x_ticks = [(tmin + (tmax - tmin) * i / 4.0,
                f"{tmin + (tmax - tmin) * i / 4.0:.2f}") for i in range(5)]
    y_ticks = [(v, f"{v:.3g}") for v in (vmin, (vmin + vmax) / 2, vmax)]
    svg = [_frame("Time (ms)", ["Voltage (V)"], x_ticks, y_ticks, xmap, ymap)]
    if vmin < 0 < vmax:
        zero = ymap(0.0)
        svg.append(f'<line x1="{_LEFT}" y1="{zero:.2f}" x2="{_W - _RIGHT}" y2="{zero:.2f}" '
                   'stroke="#9cb2c2" stroke-width="1" stroke-dasharray="4 3"/>')
    svg.append(_polyline(list(zip(times, [p.vin_v for p in points])), xmap, ymap, "#0c8176"))
    svg.append(_polyline(list(zip(times, [p.vout_v for p in points])), xmap, ymap, "#c27735"))
    svg.append(f'<text x="{_W - _RIGHT - 8}" y="{_TOP + 14}" font-size="12" '
               'fill="#0c8176" text-anchor="end">Vin (vb)</text>')
    svg.append(f'<text x="{_W - _RIGHT - 8}" y="{_TOP + 30}" font-size="12" '
               'fill="#c27735" text-anchor="end">Vout (out)</text>')
    svg.append("</svg>")
    return "\n".join(svg)
