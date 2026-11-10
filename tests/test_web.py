import unittest

from app import app


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{name}"', body)
        self.assertIn("Calculate DC Bias", body)


    def test_post_calculate_shows_result(self):
        res = self.client.post("/calculate", data={
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"})
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("8.05", body)
        self.assertIn("Forward Active", body)

    def test_post_invalid_shows_error(self):
        res = self.client.post("/calculate", data={
            "vcc": "abc", "r1": "0", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"})
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("กรุณากรอกตัวเลข", body)
        self.assertNotIn("Traceback", body)


if __name__ == "__main__":
    unittest.main()
