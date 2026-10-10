"""
ReflectSort — Application Integration Tests (Member 3 Layer)
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Tests Predictor, input validation, bin mapping, batch CSV processing,
logging, and safety fallback behavior.
"""

from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from application.shade_demo import (
    ADC_MAX,
    ADC_MIN,
    CONF_THRESHOLD,
    SHADE_TO_BIN,
    Predictor,
    log_prediction,
    run_csv_batch,
    validate_input,
)
from shared.configuration import LABEL_TO_BIN, PROJECT_ROOT


class TestInputValidation(unittest.TestCase):
    """Test raw sensor reading validation rules."""

    def test_valid_readings(self):
        ok, msg = validate_input(510, 150, 900)
        self.assertTrue(ok)
        self.assertIn("Valid", msg)

    def test_valid_without_reference(self):
        ok, msg = validate_input(510, 150)
        self.assertTrue(ok)

    def test_missing_inputs(self):
        ok, msg = validate_input(None, 150)
        self.assertFalse(ok)
        self.assertIn("Missing", msg)

    def test_non_numeric_input(self):
        ok, msg = validate_input("invalid", 150)
        self.assertFalse(ok)
        self.assertIn("numeric", msg)

    def test_non_finite_inputs(self):
        ok, msg = validate_input(float("nan"), 150)
        self.assertFalse(ok)
        self.assertIn("finite", msg)

        ok, msg = validate_input(500, float("inf"))
        self.assertFalse(ok)
        self.assertIn("finite", msg)

    def test_adc_out_of_bounds_high(self):
        ok, msg = validate_input(ADC_MAX + 10, 150)
        self.assertFalse(ok)
        self.assertIn("outside 12-bit ADC range", msg)

    def test_adc_out_of_bounds_negative(self):
        ok, msg = validate_input(-1, 150)
        self.assertFalse(ok)
        self.assertIn("outside 12-bit ADC range", msg)

    def test_zero_or_negative_ambient(self):
        ok, msg = validate_input(500, 0)
        self.assertFalse(ok)
        self.assertIn("ambient_ldr must be > 0", msg)

        ok, msg = validate_input(500, -10)
        self.assertFalse(ok)
        self.assertIn("outside 12-bit ADC range", msg)


class TestApplicationPredictor(unittest.TestCase):
    """Test Predictor inference, confidence gating, and bin mapping."""

    @classmethod
    def setUpClass(cls):
        cls.predictor = Predictor()

    def test_nominal_shade_predictions(self):
        """Nominal readings within dataset bands must map to BIN_A, BIN_B, BIN_C."""
        cases = [
            (245, 148, "BIN_A"),  # Dark shade
            (510, 148, "BIN_B"),  # Medium shade
            (790, 148, "BIN_C"),  # Light shade
        ]
        for s, a, expected_bin in cases:
            decision, conf, note = self.predictor.predict(s, a, 900)
            self.assertEqual(decision, expected_bin)
            self.assertGreaterEqual(conf, CONF_THRESHOLD)

    def test_out_of_training_range_returns_hold(self):
        """Readings exceeding model training bounds must return HOLD without error."""
        # 2500 is within 12-bit ADC (0-4095) but exceeds training_max (~941)
        decision, conf, note = self.predictor.predict(2500, 150, 900)
        self.assertEqual(decision, "HOLD")
        self.assertEqual(conf, 0.0)
        self.assertIn("outside model training range", note)

    def test_invalid_adc_reading_returns_hold(self):
        decision, conf, note = self.predictor.predict(9999, 150, 900)
        self.assertEqual(decision, "HOLD")
        self.assertEqual(conf, 0.0)
        self.assertIn("Rejected input", note)

    def test_zero_ambient_returns_hold(self):
        decision, conf, note = self.predictor.predict(500, 0, 900)
        self.assertEqual(decision, "HOLD")
        self.assertEqual(conf, 0.0)
        self.assertIn("Rejected input", note)

    def test_label_mapping_consistency(self):
        """Application bin mapping must match shared configuration."""
        self.assertEqual(SHADE_TO_BIN, LABEL_TO_BIN)
        self.assertEqual(SHADE_TO_BIN["Dark"], "BIN_A")
        self.assertEqual(SHADE_TO_BIN["Medium"], "BIN_B")
        self.assertEqual(SHADE_TO_BIN["Light"], "BIN_C")


class TestBatchCSVAndLogging(unittest.TestCase):
    """Test CSV batch predictions and log writing."""

    def test_csv_batch_execution(self):
        predictor = Predictor()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            in_csv = tmp_path / "test_input.csv"
            out_log = tmp_path / "test_log.csv"

            # Create test CSV
            with open(in_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["sample_ldr", "ambient_ldr", "reference_value"])
                writer.writerow([245, 148, 900])
                writer.writerow([510, 148, 900])
                writer.writerow([9999, 148, 900])  # Invalid ADC
                writer.writerow([500, 0, 900])     # Zero ambient

            results = run_csv_batch(predictor, str(in_csv), log_file=out_log)
            self.assertEqual(len(results), 4)
            self.assertEqual(results[0]["decision"], "BIN_A")
            self.assertEqual(results[1]["decision"], "BIN_B")
            self.assertEqual(results[2]["decision"], "HOLD")
            self.assertEqual(results[3]["decision"], "HOLD")

            # Verify log output file exists and has correct rows
            self.assertTrue(out_log.exists())
            with open(out_log, mode="r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                self.assertEqual(len(rows), 4)
                self.assertEqual(rows[0]["decision"], "BIN_A")


if __name__ == "__main__":
    unittest.main()
