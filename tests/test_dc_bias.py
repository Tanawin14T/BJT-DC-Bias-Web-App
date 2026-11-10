import unittest

from dc_bias import DcBiasInput, calculate, parse_inputs

REF = DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=100.0, vbe=0.70)


class TestReferenceOperatingPoint(unittest.TestCase):
    def test_reference_operating_point(self):
        r = calculate(REF)
        self.assertAlmostEqual(r.vth, 2.164, places=3)
        self.assertAlmostEqual(r.rth, 18.033, places=3)
        self.assertAlmostEqual(r.ib_ua, 12.299, places=3)
        self.assertAlmostEqual(r.ic_ma, 1.2299, places=4)
        self.assertAlmostEqual(r.ie_ma, 1.2422, places=4)
        self.assertAlmostEqual(r.ve, 1.2422, places=3)
        self.assertAlmostEqual(r.vb, 1.9422, places=3)
        self.assertAlmostEqual(r.vc, 9.2943, places=3)
        self.assertAlmostEqual(r.vce, 8.0522, places=3)
        self.assertEqual(r.region, "Forward Active")
        self.assertEqual(r.warnings, ())


class TestRegionHandling(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=1.0, rc=2.2, re=1.0, beta=100.0, vbe=0.70))
        self.assertEqual(r.region, "Cutoff")
        self.assertEqual(r.ic_ma, 0.0)
        self.assertEqual(r.ie_ma, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vc, 12.0, places=6)
        self.assertTrue(any("Cutoff" in w for w in r.warnings))

    def test_saturation_when_rc_too_large(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=10.0, re=0.1, beta=100.0, vbe=0.70))
        self.assertEqual(r.region, "Saturation")
        self.assertTrue(any("Saturation" in w for w in r.warnings))

    def test_low_beta_still_calculates_with_warning(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=5.0, vbe=0.70))
        self.assertGreater(r.ib_ua, 0.0)
        self.assertTrue(any("β" in w for w in r.warnings))


GOOD = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"}


class TestParseInputs(unittest.TestCase):
    def test_accepts_valid_strings(self):
        inp, errors = parse_inputs(GOOD)
        self.assertEqual(errors, {})
        self.assertIsNotNone(inp)
        self.assertAlmostEqual(inp.r1, 100.0)

    def test_rejects_non_numeric_and_blank(self):
        raw = dict(GOOD, vcc="abc", r1="")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertIn("vcc", errors)
        self.assertIn("r1", errors)

    def test_rejects_non_finite(self):
        raw = dict(GOOD, rc="nan", re="inf")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertIn("rc", errors)
        self.assertIn("re", errors)

    def test_rejects_non_positive(self):
        raw = dict(GOOD, r1="0", beta="0", vcc="-12")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertEqual(set(errors), {"r1", "beta", "vcc"})


class TestParameterRangeWarnings(unittest.TestCase):
    def test_vbe_outside_typical_range_warns(self):
        for vbe in (0.4, 1.0):
            r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=100.0, vbe=vbe))
            self.assertTrue(any("VBE" in w for w in r.warnings), msg=f"vbe={vbe} should warn")

    def test_vbe_inside_typical_range_does_not_warn(self):
        for vbe in (0.5, 0.9):
            r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=100.0, vbe=vbe))
            self.assertFalse(any("VBE" in w for w in r.warnings), msg=f"vbe={vbe} should not warn")


if __name__ == "__main__":
    unittest.main()
