"""Run in PyCharm: right-click -> Run 'Python tests'  (or: python -m unittest)"""
import unittest
from shade_demo import validate, make_features, Predictor

class TestValidate(unittest.TestCase):
    def test_ok(self):            self.assertTrue(validate(1000, 500, 1800)[0])
    def test_missing(self):       self.assertFalse(validate(None, 500, 1800)[0])
    def test_too_high(self):      self.assertFalse(validate(9999, 500, 1800)[0])
    def test_negative(self):      self.assertFalse(validate(-5, 500, 1800)[0])
    def test_zero_reference(self):self.assertFalse(validate(900, 450, 0)[0])

class TestFeatures(unittest.TestCase):
    def test_values(self):
        f = make_features(900, 100, 1800)
        self.assertEqual(len(f), 5)
        self.assertAlmostEqual(f[3], 0.5)
        self.assertEqual(f[4], 800)

class TestPredictor(unittest.TestCase):
    def setUp(self): self.p = Predictor()
    def test_bad_input_is_hold(self):
        self.assertEqual(self.p.predict(9999, 500, 1800)[0], "HOLD")
    def test_output_label_is_allowed(self):
        self.assertIn(self.p.predict(1100, 500, 1800)[0], ("BIN_A","BIN_B","BIN_C","HOLD"))
    def test_dark_light(self):
        self.assertEqual(self.p.predict(400, 500, 1800)[0], "BIN_A")
        self.assertEqual(self.p.predict(1800, 500, 1800)[0], "BIN_C")

if __name__ == "__main__":
    unittest.main()
