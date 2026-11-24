"""HTTP-level checks for the Lab 04 simulator route.

ngspice itself is replaced by a stub result here; no simulation values are
fabricated in the application. See docs/validation.md for real-engine status.
"""

import unittest
from unittest.mock import patch

import spice_engine as se
from app import app


VALID_SIM = {
    "analysis": "ac",
    "sim_vcc": "12", "sim_r1": "100", "sim_r2": "22",
    "sim_rc": "2.2", "sim_re": "1", "sim_rl": "10",
    "sim_cin": "10", "sim_cout": "10",
    "amplitude": "0.01", "frequency": "1000",
    "fstart": "10", "fstop": "1000000", "ac_points": "100", "tran_stop": "5",
}


def success_result():
    return se.SimulationResult(
        ok=True, analysis="ac", status="success", message="simulation completed",
        engine="ngspice", model=se.BJT_MODEL_NAME,
        ac=[se.AcPoint(1000.0, 10.0, -180.0, 0.001, 0.01)],
        ac_summary={"max_gain": 10.0, "f_at_max_gain": 1000.0, "f_3db": None},
    )


def error_result(message):
    return se.SimulationResult(
        ok=False, analysis="ac", status="error", message=message,
        engine="ngspice", model=se.BJT_MODEL_NAME,
    )


class TestSimulatorPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_exposes_simulator_form(self):
        body = self.client.get("/").get_data(as_text=True)
        for name in ("analysis", "sim_re", "sim_rl", "amplitude", "frequency"):
            self.assertIn(f'name="{name}"', body)
        for label in ("Run Simulation", "ngspice", "Common-Emitter", "DC Bias"):
            self.assertIn(label, body)

    def test_simulate_success_renders_real_result_markers(self):
        with patch("app.run_simulation", return_value=success_result()):
            res = self.client.post("/simulate", data=VALID_SIM)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn('id="sim-results"', body)
        self.assertIn("ngspice", body)
        self.assertIn("1.000e+03", body)
        self.assertIn("10.00", body)
        self.assertIn("Bode", body)

    def test_simulate_engine_error_has_no_success_panel(self):
        msg = "ไม่พบ ngspice — ตรวจ PATH หรือ NGSPICE_PATH"
        with patch("app.run_simulation", return_value=error_result(msg)):
            res = self.client.post("/simulate", data=VALID_SIM)
        self.assertEqual(res.status_code, 503)
        body = res.get_data(as_text=True)
        self.assertIn(msg, body)
        self.assertNotIn('id="sim-results"', body)

    def test_simulate_invalid_re_returns_400(self):
        with patch("app.run_simulation") as run:
            res = self.client.post("/simulate", data=dict(VALID_SIM, sim_re="0"))
        run.assert_not_called()
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("ต้องมากกว่า 0", body)
        self.assertNotIn('id="sim-results"', body)


if __name__ == "__main__":
    unittest.main()
