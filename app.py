"""Flask entry point: HTTP only, all engineering lives in dc_bias.py."""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    ALL_FIELDS,
    FIELDS_BY_MODE,
    MODE_FORMULAS,
    MODE_LABELS,
    calculate,
    parse_inputs,
)
from plots import ac_plot, tran_plot
from spice_engine import (
    ANALYSIS_MODES,
    BJT_MODEL_NAME,
    DEFAULT_SIM_FORM,
    run_simulation,
    validate_inputs,
)

app = Flask(__name__)

DEFAULT_MODE = "divider"

RESISTANCE_FIELDS = ("rb", "r1", "r2", "rc", "re")
UNIT_LABELS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}
UNIT_TO_KOHM = {"ohm": 0.001, "kohm": 1.0, "mohm": 1000.0}
UNIT_DEFAULTS = {f"u_{name}": "kohm" for name in RESISTANCE_FIELDS}

DEFAULTS: dict[str, str] = {
    "vcc": "12",
    "rb": "1000",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


def _form_values(source) -> dict[str, str]:
    """Keep values already typed so switching modes does not erase them."""
    values = dict(DEFAULTS)
    values.update(UNIT_DEFAULTS)
    for name in ALL_FIELDS:
        value = source.get(name)
        if value is not None:
            values[name] = value
    for key in UNIT_DEFAULTS:
        value = source.get(key)
        if value in UNIT_TO_KOHM:
            values[key] = value
    return values


def _as_kohm(form: dict[str, str]) -> dict[str, str]:
    """Convert the chosen input unit to kohm — the only unit dc_bias.py accepts."""
    data = dict(form)
    for name in RESISTANCE_FIELDS:
        try:
            data[name] = format(float(form[name]) * UNIT_TO_KOHM.get(form.get(f"u_{name}"), 1.0), ".12g")
        except (ValueError, TypeError, KeyError):
            pass  # leave the raw text so the existing validation reports it
    return data


def _render(mode: str, form: dict[str, str], errors: dict[str, str], result, status: int = 200,
            *, sim_form=None, sim_errors=None, sim_result=None, analysis="dc",
            bode_svg="", wave_svg=""):
    return render_template(
        "index.html",
        mode=mode,
        modes=MODE_LABELS,
        unit_options=UNIT_LABELS,
        mode_label=MODE_LABELS[mode],
        formula=MODE_FORMULAS[mode],
        active_fields=FIELDS_BY_MODE[mode],
        form=form,
        errors=errors,
        result=result,
        sim_form=sim_form if sim_form is not None else dict(DEFAULT_SIM_FORM),
        sim_errors=sim_errors or {},
        sim_result=sim_result,
        analysis_modes=ANALYSIS_MODES,
        analysis=analysis,
        bjt_model=BJT_MODEL_NAME,
        bode_svg=bode_svg,
        wave_svg=wave_svg,
    ), status


@app.route("/", methods=["GET", "POST"])
def index():
    source = request.form if request.method == "POST" else request.args
    raw_mode = source.get("mode", DEFAULT_MODE)
    mode = raw_mode if raw_mode in MODE_LABELS else DEFAULT_MODE
    return _render(mode, _form_values(source), {}, None)


@app.post("/calculate")
def calculate_route():
    raw_mode = request.form.get("mode", DEFAULT_MODE)
    form = _form_values(request.form)
    if raw_mode not in MODE_LABELS:
        return _render(
            DEFAULT_MODE, form,
            {"mode": f"โหมดวงจรไม่รู้จัก: {raw_mode} — กรุณาเลือกใหม่"},
            None, 400,
        )

    inp, errors = parse_inputs(_as_kohm(form), raw_mode)
    if errors:
        return _render(raw_mode, form, errors, None, 400)
    return _render(raw_mode, form, {}, calculate(inp))


@app.post("/simulate")
def simulate_route():
    """Validate the CE form, run ngspice through the adapter, render its data."""
    sim_form = {
        key: (request.form.get(key) or default).strip()
        for key, default in DEFAULT_SIM_FORM.items()
    }
    analysis = sim_form["analysis"]
    lab_mode = request.form.get("lab_mode", DEFAULT_MODE)
    if lab_mode not in MODE_LABELS:
        lab_mode = DEFAULT_MODE
    bias_form = _form_values(request.form)

    inp, errors = validate_inputs(sim_form)
    if errors:
        return _render(
            lab_mode, bias_form, {}, None, 400,
            sim_form=sim_form, sim_errors=errors, analysis=analysis,
        )

    result = run_simulation(sim_form)
    if not result.ok:
        return _render(
            lab_mode, bias_form, {}, None, 400 if result.errors else 503,
            sim_form=sim_form, sim_errors=result.errors, sim_result=result,
            analysis=result.analysis,
        )

    return _render(
        lab_mode, bias_form, {}, None, 200,
        sim_form=sim_form, sim_result=result, analysis=result.analysis,
        bode_svg=ac_plot(result.ac) if result.ac else "",
        wave_svg=tran_plot(result.tran) if result.tran else "",
    )


if __name__ == "__main__":
    app.run(debug=True)
