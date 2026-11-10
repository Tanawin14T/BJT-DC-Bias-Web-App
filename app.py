"""Flask entry point: HTTP only, all engineering lives in dc_bias.py."""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import FIELDS, calculate, parse_inputs

app = Flask(__name__)

DEFAULTS: dict[str, str] = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


@app.get("/")
def index():
    return render_template("index.html", form=DEFAULTS, errors={}, result=None)


@app.post("/calculate")
def calculate_route():
    raw = {name: request.form.get(name, "") for name in FIELDS}
    inp, errors = parse_inputs(raw)
    if errors:
        return render_template("index.html", form=raw, errors=errors, result=None), 400
    return render_template("index.html", form=raw, errors={}, result=calculate(inp))


if __name__ == "__main__":
    app.run(debug=True)
