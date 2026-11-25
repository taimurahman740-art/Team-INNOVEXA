"""Tests for the Random Forest priority baseline (feature 5).

These check behaviour and safety rules, not accuracy; see app/evaluate_priority.py.
"""
import unittest
from unittest.mock import patch

from app import priority_model
from app.priority_model import area_traffic, features, get_model, predict_priority


class PriorityModelTests(unittest.TestCase):
    def test_model_trains_on_sample_data(self):
        model = get_model()
        self.assertTrue(model.available, model.error)
        self.assertEqual(model.training_rows, 44)

    def test_prediction_is_a_valid_priority_with_explanation(self):
        r = predict_priority("Plumbing", "Blocked sink", "The sink is blocked and water drains slowly.", "Dormitory bathroom", 0, "Medium")
        self.assertIn(r["final"], {"Low", "Medium", "High"})
        self.assertEqual(r["method"], "random_forest")
        self.assertAlmostEqual(sum(r["probabilities"].values()), 1.0, places=2)
        self.assertTrue(any("traffic" in f for f in r["factors"]))

    def test_safety_floor_always_wins(self):
        r = predict_priority("Facility", "Chair", "A chair is wobbly.", "Dormitory room", 6, "Low")
        self.assertEqual(r["final"], "High")

    def test_area_traffic_levels(self):
        self.assertEqual(area_traffic("Main building entrance"), 2)
        self.assertEqual(area_traffic("Engineering building classroom"), 1)
        self.assertEqual(area_traffic("Dormitory room 412"), 0)

    def test_feature_vector_shape(self):
        self.assertEqual(len(features("IT", "No wifi", "Wi-Fi is unavailable", "Library", 0)), len(priority_model.FEATURE_NAMES))

    def test_falls_back_to_rules_without_model(self):
        broken = priority_model.PriorityModel.__new__(priority_model.PriorityModel)
        broken.model, broken.error, broken.training_rows = None, "ImportError: no sklearn", 0
        with patch.object(priority_model, "_model", broken):
            r = predict_priority("Plumbing", "Leak", "Pipe is leaking", "Library", 0, "Medium")
        self.assertEqual((r["method"], r["final"]), ("rules", "Medium"))


if __name__ == "__main__":
    unittest.main()
