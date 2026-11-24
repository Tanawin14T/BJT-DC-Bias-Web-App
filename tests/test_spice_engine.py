"""Tests for the ngspice adapter: netlist, parsing and failure paths.

These tests do not require ngspice to be installed. Real-engine checks are
recorded separately in docs/validation.md as NOT RUN when the binary is absent.
"""

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import spice_engine as se


GOOD = {
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
}


def raw_text(plotname, flags, variables, rows):
    lines = [
        "Title: synthetic test plot",
        f"Plotname: {plotname}",
        f"Flags: {flags}",
        f"No. Variables: {len(variables)}",
        f"No. Points: {len(rows)}",
        "Variables:",
    ]
    for idx, name in enumerate(variables):
        lines.append(f"\t{idx}\t{name}\tvoltage")
    lines.append("Values:")
    for idx, row in enumerate(rows):
        lines.append("\t" + str(idx) + "\t" + "\t".join(row))
    return "\n".join(lines) + "\n"


class TestValidation(unittest.TestCase):
    def test_accepts_reference_fixture(self):
        inp, errors = se.validate_inputs(GOOD)
        self.assertEqual(errors, {})
        self.assertIsNotNone(inp)
        self.assertAlmostEqual(inp.vcc, 12.0)
        self.assertAlmostEqual(inp.frequency, 1000.0)

    def test_rejects_zero_emitter_resistor(self):
        inp, errors = se.validate_inputs(dict(GOOD, sim_re="0"))
        self.assertIsNone(inp)
        self.assertIn("sim_re", errors)

    def test_rejects_bad_source_values(self):
        _, errors = se.validate_inputs(dict(GOOD, amplitude="-1", frequency="0"))
        self.assertIn("amplitude", errors)
        self.assertIn("frequency", errors)

    def test_rejects_injection_into_model_name(self):
        _, errors = se.validate_inputs(dict(GOOD, model="npn\n.end"))
        self.assertIn("model", errors)

    def test_rejects_unknown_analysis(self):
        _, errors = se.validate_inputs(dict(GOOD, analysis="magic"))
        self.assertIn("analysis", errors)

    def test_rejects_sweep_without_positive_span(self):
        _, errors = se.validate_inputs(dict(GOOD, fstart="1e6", fstop="100"))
        self.assertIn("fstop", errors)


class TestNetlist(unittest.TestCase):
    def setUp(self):
        self.inp, errors = se.validate_inputs(GOOD)
        self.assertEqual(errors, {})

    def test_dc_uses_op_and_coupling_caps_are_open(self):
        netlist = se.build_netlist(self.inp)
        self.assertIn(".op", netlist)
        self.assertNotIn(".ac", netlist)
        self.assertNotIn(".tran", netlist)
        self.assertIn("Cin", netlist)
        self.assertIn(".model", netlist)
        self.assertIn("VIC", netlist)

    def test_ac_uses_decade_sweep(self):
        inp, _ = se.validate_inputs(dict(GOOD, analysis="ac", ac_points="50"))
        netlist = se.build_netlist(inp)
        self.assertIn(".ac dec 50 10 1000000", netlist)

    def test_transient_uses_sin_source(self):
        inp, _ = se.validate_inputs(dict(GOOD, analysis="transient", tran_stop="5"))
        netlist = se.build_netlist(inp)
        self.assertIn(".tran", netlist)
        self.assertIn("SIN(0 0.01 1000", netlist)

    def test_transient_step_resolves_1khz_sine(self):
        inp, _ = se.validate_inputs(dict(GOOD, analysis="transient", tran_stop="5"))
        directive = next(line for line in se.build_netlist(inp).splitlines()
                         if line.startswith(".tran"))
        # ngspice syntax is .tran TSTEP TSTOP (step first, stop second).
        _, step, stop = directive.split()
        self.assertAlmostEqual(float(stop), 0.005)
        # <= 50 us gives at least 20 samples per 1 kHz period, so the measured
        # AC amplitude is not an artefact of an undersampled sine.
        self.assertLessEqual(float(step), 50e-6)


class TestRawParsing(unittest.TestCase):
    def test_parse_op_values(self):
        plot = se.parse_raw(raw_text(
            "Operating Point", "real",
            ["v(vb)", "v(e)", "v(c)", "i(vic)"],
            [["1.900000e+00", "1.200000e+00", "9.400000e+00", "1.180000e-03"]],
        ))
        op = se.extract_op(plot)
        self.assertAlmostEqual(op.vb, 1.9, places=6)
        self.assertAlmostEqual(op.ve, 1.2, places=6)
        self.assertAlmostEqual(op.vc, 9.4, places=6)
        self.assertAlmostEqual(op.vce, 8.2, places=6)
        self.assertAlmostEqual(op.ic_ma, 1.18, places=6)

    def test_parse_ac_complex_gain_and_phase(self):
        # vout = -10 * vin -> gain 10, phase 180 degrees
        plot = se.parse_raw(raw_text(
            "AC Analysis", "complex",
            ["frequency", "v(vb)", "v(out)"],
            [
                ["1.000e+03,0.0", "1.000e-03,0.0", "-1.000e-02,0.0"],
                ["1.000e+04,0.0", "2.000e-03,0.0", "-2.000e-02,0.0"],
            ],
        ))
        points = se.extract_ac(plot)
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[0].frequency_hz, 1000.0)
        self.assertAlmostEqual(points[0].gain, 10.0, places=6)
        self.assertAlmostEqual(abs(points[0].phase_deg), 180.0, places=5)
        self.assertAlmostEqual(points[1].gain, 10.0, places=6)

    def test_parse_transient_points(self):
        plot = se.parse_raw(raw_text(
            "Transient Analysis", "real",
            ["time", "v(vb)", "v(out)"],
            [["0.0", "0.01", "-0.1"], ["0.001", "-0.01", "0.1"]],
        ))
        points = se.extract_tran(plot)
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[1].time_s, 0.001)
        self.assertTrue(se.tran_summary(points)["inverted"])

    def test_transient_gain_ignores_dc_offset(self):
        # vb sits at ~2 V DC while the AC-coupled output has ~0 V DC. A peak
        # ratio taken from the raw voltages would wrongly report ~0.01 gain.
        # Four quarter-period samples repeat symmetrically, so the mean is
        # exactly the DC level and the physical peak is exactly 10 mV / 100 mV.
        points = [
            se.TranPoint(t, 2.0 + vin, vout)
            for t, vin, vout in [
                (0.0, 0.0, 0.0),
                (0.00025, 0.01, -0.1),
                (0.0005, 0.0, 0.0),
                (0.00075, -0.01, 0.1),
                (0.001, 0.0, 0.0),
            ]
        ]
        summary = se.tran_summary(points)
        self.assertAlmostEqual(summary["vin_peak_v"], 0.01, places=6)
        self.assertAlmostEqual(summary["vout_peak_v"], 0.1, places=6)
        self.assertAlmostEqual(summary["gain_estimate"], 10.0, places=5)
        self.assertTrue(summary["inverted"])

    def test_missing_variable_raises_engine_error(self):
        plot = se.parse_raw(raw_text("AC Analysis", "complex", ["frequency"], [["1,0"]]))
        with self.assertRaises(se.SpiceEngineError):
            se.extract_ac(plot)

    def test_parse_real_ngspice_raw_one_value_per_line(self):
        # ASCII raw from ngspice-47: the point index sits alone at the start of
        # the first line, then ONE value per line (unlike our compact fixtures).
        raw = "\n".join([
            "Title: real ngspice raw",
            "Plotname: Operating Point",
            "Flags: real",
            "No. Variables: 4",
            "No. Points: 1",
            "Variables:",
            "\t0\tv(vb)\tvoltage",
            "\t1\tv(e)\tvoltage",
            "\t2\tv(c)\tvoltage",
            "\t3\ti(vic)\tcurrent",
            "Values:",
            "0\t\t2.047611099469625e+00",
            "\t1.385831956524021e+00",
            "\t8.965361121787979e+00",
            "\t1.379381308278194e-03",
        ]) + "\n"
        op = se.extract_op(se.parse_raw(raw))
        self.assertAlmostEqual(op.vb, 2.047611099469625, places=9)
        self.assertAlmostEqual(op.vce, 8.965361121787979 - 1.385831956524021, places=9)
        self.assertAlmostEqual(op.ic_ma, 1.379381308278194, places=9)

    def test_parse_real_ngspice_complex_raw_one_pair_per_line(self):
        raw = "\n".join([
            "Title: real ngspice raw",
            "Plotname: AC Analysis",
            "Flags: complex",
            "No. Variables: 3",
            "No. Points: 2",
            "Variables:",
            "\t0\tfrequency\tfrequency\tgrid=3",
            "\t1\tv(vb)\tvoltage",
            "\t2\tv(out)\tvoltage",
            "Values:",
            "0\t\t1.000000000000000e+01,0.000000000000000e+00",
            "\t9.909116403787324e-03,9.492034238271518e-04",
            "\t-1.693820946258750e-02,-3.880955753983664e-03",
            "1\t\t1.122018454301963e+01,0.000000000000000e+00",
            "\t9.927672741911094e-03,8.475607734498202e-04",
            "\t-1.700000000000000e-02,-4.000000000000000e-03",
        ]) + "\n"
        points = se.extract_ac(se.parse_raw(raw))
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[0].frequency_hz, 10.0, places=6)
        self.assertGreater(points[0].gain, 1.0)


class TestFailureHandling(unittest.TestCase):
    def _fake_run(self, **kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    def test_missing_engine_is_error_not_success(self):
        with patch.dict(os.environ, {"NGSPICE_PATH": ""}), patch("shutil.which", return_value=None):
            result = se.run_simulation(GOOD)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "error")
        self.assertIn("ngspice", result.message)

    def test_nonzero_exit_is_error(self):
        with patch("shutil.which", return_value="ngspice"), patch(
            "spice_engine.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fatal: bad netlist"),
        ):
            result = se.run_simulation(GOOD)
        self.assertFalse(result.ok)
        self.assertIn("fatal: bad netlist", result.message)

    def test_empty_raw_is_error(self):
        def make_empty_raw(*args, **kwargs):
            raw = Path(kwargs["cwd"]) / "run.raw"
            raw.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with patch("shutil.which", return_value="ngspice"), patch(
            "spice_engine.subprocess.run", side_effect=make_empty_raw,
        ):
            result = se.run_simulation(GOOD)
        self.assertFalse(result.ok)
        self.assertTrue(result.message)

    def test_timeout_is_error(self):
        with patch("shutil.which", return_value="ngspice"), patch(
            "spice_engine.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ngspice", timeout=30),
        ):
            result = se.run_simulation(GOOD)
        self.assertFalse(result.ok)
        self.assertIn("timeout", result.message.lower())

    def test_subprocess_is_list_no_shell_with_timeout(self):
        seen = {}

        def capture(args, **kwargs):
            seen.update(args=args, kwargs=kwargs)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        with patch("shutil.which", return_value="ngspice"), patch(
            "spice_engine.subprocess.run", side_effect=capture,
        ):
            se.run_simulation(GOOD)
        self.assertIsInstance(seen["args"], list)
        self.assertEqual(seen["args"][0], "ngspice")
        self.assertNotEqual(seen["kwargs"].get("shell"), True)
        self.assertIsNotNone(seen["kwargs"].get("timeout"))
        self.assertNotEqual(Path(seen["kwargs"]["cwd"]).name, "BJT-DC-Bias-Web-App")


if __name__ == "__main__":
    unittest.main()
