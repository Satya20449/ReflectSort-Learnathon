"""
ReflectSort — Machine Learning Integration Tests (Member 2 Pipeline)
Course: Machine Learning – Embedded Systems Design (ML-ESD)
Team: ML-ESD-TEAM-117 | Project ID: PROJECT-12-VARIANT-06

Tests model loading, feature contract, prediction probability,
and reproducible synthetic training pipeline.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from ml.train_model import FEATURES, TARGET, train_model
from shared.configuration import (
    DEFAULT_MODEL_RELATIVE_PATH,
    EXPECTED_CLASSES,
    EXPECTED_FEATURES,
    PROJECT_ROOT,
)


class TestMLModelArtifact(unittest.TestCase):
    """Tests for the approved shade_model.joblib model artifact."""

    @classmethod
    def setUpClass(cls):
        cls.model_path = PROJECT_ROOT / DEFAULT_MODEL_RELATIVE_PATH
        if not cls.model_path.exists():
            raise unittest.SkipTest(f"Model file not found at {cls.model_path}")
        cls.bundle = joblib.load(cls.model_path)

    def test_bundle_structure(self):
        """Model bundle must be a dictionary containing required metadata keys."""
        self.assertIsInstance(self.bundle, dict)
        required_keys = ["pipeline", "features", "classes", "training_min", "training_max", "data_source"]
        for key in required_keys:
            self.assertIn(key, self.bundle, f"Missing required bundle key: {key}")

    def test_pipeline_composition(self):
        """Pipeline must contain a StandardScaler followed by a classifier."""
        pipeline = self.bundle["pipeline"]
        self.assertIsInstance(pipeline, Pipeline)
        step_names = [name for name, _ in pipeline.steps]
        self.assertIn("scaler", step_names)
        self.assertIn("classifier", step_names)

    def test_feature_contract(self):
        """Bundle must enforce the exact 3-feature contract."""
        self.assertEqual(list(self.bundle["features"]), EXPECTED_FEATURES)
        self.assertEqual(self.bundle["features"], ["sample_LDR", "ambient_LDR", "reflectance_ratio"])

    def test_target_classes(self):
        """Target classes must be ['Dark', 'Light', 'Medium']."""
        self.assertEqual(sorted(self.bundle["classes"]), sorted(EXPECTED_CLASSES))

    def test_training_ranges_exist(self):
        """Training boundaries must be defined for all features."""
        for feat in EXPECTED_FEATURES:
            self.assertIn(feat, self.bundle["training_min"])
            self.assertIn(feat, self.bundle["training_max"])
            self.assertLess(self.bundle["training_min"][feat], self.bundle["training_max"][feat])

    def test_representative_predictions(self):
        """Pipeline must correctly classify nominal samples."""
        pipeline = self.bundle["pipeline"]
        cases = [
            (240.0, 150.0, "Dark"),
            (510.0, 150.0, "Medium"),
            (750.0, 150.0, "Light"),
        ]
        for s, a, expected_shade in cases:
            row = pd.DataFrame([[s, a, s / a]], columns=EXPECTED_FEATURES)
            pred = pipeline.predict(row)[0]
            self.assertEqual(pred, expected_shade, f"Expected {expected_shade} for S={s}, A={a}; got {pred}")

    def test_predict_proba_validity(self):
        """Probabilities must sum to 1.0 and yield high confidence for nominal samples."""
        pipeline = self.bundle["pipeline"]
        row = pd.DataFrame([[510.0, 150.0, 510.0 / 150.0]], columns=EXPECTED_FEATURES)
        probs = pipeline.predict_proba(row)[0]
        self.assertAlmostEqual(float(probs.sum()), 1.0, places=5)
        self.assertGreaterEqual(float(probs.max()), 0.60)


class TestMLTrainingPipeline(unittest.TestCase):
    """Tests reproducible retraining script."""

    def test_retrain_in_temporary_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            model_out = tmp_path / "test_model.joblib"
            outputs_out = tmp_path / "outputs"
            data_file = PROJECT_ROOT / "ml" / "data" / "demo_data_simulated.csv"

            if not data_file.exists():
                self.skipTest("Training CSV not found")

            bundle = train_model(
                data_path=data_file,
                model_output_path=model_out,
                outputs_dir=outputs_out,
                random_seed=117,
            )

            self.assertTrue(model_out.exists())
            self.assertTrue((outputs_out / "evaluation_summary.json").exists())
            self.assertTrue((outputs_out / "classification_report.txt").exists())
            self.assertTrue((outputs_out / "confusion_matrix.csv").exists())
            self.assertGreaterEqual(bundle["training_seed"], 0)


if __name__ == "__main__":
    unittest.main()
