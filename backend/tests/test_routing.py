"""Regression tests for safety-driven department routing."""
import unittest

from app.routing import apply_safety_category_override
from app.services import assess_safety_risk


class SafetyCategoryRoutingTests(unittest.TestCase):
    def test_active_fire_hazard_overrides_electrical_category(self):
        reasons = assess_safety_risk(
            "Fire detected in building",
            "Flames and smoke are coming from the electrical room.",
        )[2]
        self.assertIn("Possible fire, smoke, gas or explosion", reasons)
        category = apply_safety_category_override("Electrical", reasons)
        self.assertEqual(category, "Safety")

    def test_ordinary_electrical_issue_stays_electrical(self):
        reasons = assess_safety_risk(
            "Broken classroom light", "The ceiling light does not turn on."
        )[2]
        category = apply_safety_category_override("Electrical", reasons)
        self.assertEqual(category, "Electrical")

    def test_fire_inspection_without_detected_hazard_keeps_original_category(self):
        reasons = assess_safety_risk(
            "Fire inspection", "No fire or smoke was detected in the building."
        )[2]
        self.assertEqual(reasons, [])
        category = apply_safety_category_override("Electrical", reasons)
        self.assertEqual(category, "Electrical")


if __name__ == "__main__":
    unittest.main()
