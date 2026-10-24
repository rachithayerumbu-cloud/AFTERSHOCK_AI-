"""
AFTERSHOCK AI — Demonstration Machine-Learning Risk Classifier Tests
Module: tests/test_risk_model.py
"""

import unittest
from risk_model import (
    InfrastructureRiskModel,
    assess_all_asset_risks,
    RISK_LABELS,
    FEATURE_NAMES,
)
from simulator import get_all_assets


class TestRiskModel(unittest.TestCase):
    """Test suite for Random Forest classifier, synthetic training reproducibility, and risk outputs."""

    def setUp(self):
        self.model = InfrastructureRiskModel(random_state=42)

    def test_model_initialization(self):
        """Model must initialize and successfully train without errors."""
        self.assertTrue(self.model.is_trained)
        self.assertEqual(len(self.model.feature_names), 4)

    def test_reproducibility_fixed_seed(self):
        """Two models trained with the same fixed seed produce identical predictions."""
        model_a = InfrastructureRiskModel(random_state=42)
        model_b = InfrastructureRiskModel(random_state=42)
        test_features = [8.0, 7.5, 2, 0]
        pred_a = model_a.predict_risk(test_features)
        pred_b = model_b.predict_risk(test_features)
        self.assertEqual(pred_a["predicted_class"], pred_b["predicted_class"])
        self.assertEqual(pred_a["confidence_score"], pred_b["confidence_score"])

    def test_all_assets_receive_supported_risk_labels(self):
        """Every configured asset receives a supported risk label."""
        report = assess_all_asset_risks()
        valid_labels = set(RISK_LABELS.values())
        self.assertGreater(len(report["assets"]), 0)
        for item in report["assets"]:
            self.assertIn(item["risk_label"], valid_labels)
            self.assertGreaterEqual(item["confidence_score"], 0.0)
            self.assertLessEqual(item["confidence_score"], 1.0)

    def test_probability_distribution_sums_to_one(self):
        """Class probabilities must sum to 1.0."""
        test_features = [9.0, 8.5, 3, 0]
        pred = self.model.predict_risk(test_features)
        prob_sum = sum(pred["class_probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=2)

    def test_invalid_feature_inputs_handled(self):
        """Invalid feature length or out-of-range features raise ValueError."""
        # Wrong length (3 instead of 4)
        with self.assertRaises(ValueError):
            self.model.predict_risk([5.0, 5.0, 1])

        # Negative criticality
        with self.assertRaises(ValueError):
            self.model.predict_risk([-1.0, 5.0, 1, 0])

        # Non-numeric
        with self.assertRaises(ValueError):
            self.model.predict_risk(["high", 5.0, 1, 0])

    def test_synthetic_disclaimer_present(self):
        """Outputs must explicitly identify that synthetic data was used for demonstration."""
        report = assess_all_asset_risks()
        self.assertIn("warning", report)
        self.assertIn("synthetic", report["warning"].lower())


if __name__ == "__main__":
    unittest.main()

