"""Basic regression tests for issue triage services. Run: python -m unittest discover -s tests"""
import unittest
from app.services import assess_safety_risk, classify_issue, suggest_category, suggest_department, suggest_priority

class TriageServiceTests(unittest.TestCase):
    def test_exposed_wire_is_high_priority(self):
        self.assertEqual(suggest_priority("Exposed wire", "Sparking near a socket"), "High")

    def test_leak_is_medium_priority(self):
        self.assertEqual(suggest_priority("Water leak", "Pipe is leaking"), "Medium")

    def test_category_maps_to_department(self):
        self.assertEqual(suggest_department("Electrical"), "Electrical Maintenance")

    def test_classifier_returns_valid_label_and_probability(self):
        label, confidence = classify_issue("Broken light", "Classroom lamp does not turn on")
        self.assertIn(label, {"Electrical", "Plumbing", "Cleaning", "Safety", "Facility", "Other"})
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_exposed_wire_is_high_risk(self):
        score, level, reasons = assess_safety_risk("Exposed wire", "Sparking near the classroom")
        self.assertEqual(level, "High")
        self.assertGreaterEqual(score, 5)
        self.assertTrue(reasons)

    def test_no_risk_keywords_is_low(self):
        score, level, reasons = assess_safety_risk("Broken chair", "A chair leg is damaged")
        self.assertEqual((score, level, reasons), (0, "Low", []))

    def test_gas_smell_is_high_risk(self):
        score, level, reasons = assess_safety_risk("Strong gas smell", "There is a rotten egg smell in the kitchen")
        self.assertEqual(level, "High")
        self.assertGreaterEqual(score, 5)
        self.assertIn("Possible fire, smoke, gas or explosion", reasons)

    def test_water_near_electrical_outlet_is_moderate_risk(self):
        score, level, reasons = assess_safety_risk("Water on floor", "Water is leaking near a power outlet")
        self.assertEqual(level, "Moderate")
        self.assertGreaterEqual(score, 2)
        self.assertTrue(reasons)

    def test_blocked_fire_exit_is_moderate_risk(self):
        score, level, reasons = assess_safety_risk("Exit blocked", "The fire exit is blocked")
        self.assertEqual(level, "Moderate")
        self.assertTrue(reasons)

    def test_gas_bill_is_not_a_gas_leak(self):
        score, level, reasons = assess_safety_risk("Gas bill question", "I need help understanding my monthly gas bill")
        self.assertEqual((score, level, reasons), (0, "Low", []))

    def test_routine_light_replacement_is_not_high_risk(self):
        score, level, reasons = assess_safety_risk("Classroom light", "One ceiling bulb needs replacement")
        self.assertNotEqual(level, "High")

    def test_empty_text_is_safe(self):
        label, confidence = classify_issue("", "")
        self.assertEqual(label, "Other")
        self.assertEqual(confidence, 0.0)

if __name__ == "__main__":
    unittest.main()