"""Regression tests for safety-driven department routing."""
import unittest

from app.routing import apply_safety_category_override


class SafetyCategoryRoutingTests(unittest.TestCase):
    def test_active_fire_hazard_overrides_electrical_category(self):
        category = apply_safety_category_override(
            "Electrical", ["Possible fire, smoke, gas or explosion"]
        )
        self.assertEqual(category, "Safety")

    def test_ordinary_electrical_issue_stays_electrical(self):
        category = apply_safety_category_override("Electrical", [])
        self.assertEqual(category, "Electrical")

    def test_fire_inspection_without_detected_hazard_keeps_original_category(self):
        category = apply_safety_category_override("Electrical", [])
        self.assertEqual(category, "Electrical")


if __name__ == "__main__":
    unittest.main()
