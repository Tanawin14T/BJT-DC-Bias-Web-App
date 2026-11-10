import unittest

from dc_bias import DcBiasInput, calculate

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


if __name__ == "__main__":
    unittest.main()
