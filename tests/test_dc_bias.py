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


if __name__ == "__main__":
    unittest.main()
