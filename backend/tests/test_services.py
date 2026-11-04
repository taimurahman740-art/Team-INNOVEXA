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

    def test_empty_text_is_safe(self):
        label, confidence = classify_issue("", "")
        self.assertEqual(label, "Other")
        self.assertEqual(confidence, 0.0)

if __name__ == "__main__":
    unittest.main()