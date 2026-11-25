"""Tests for HVAC/IT routing, photo interpretation and image + text fusion.

These test the decision logic with fixed model scores. They do not measure how
accurate CLIP is on real campus photos.
"""
import unittest

from app.image_recognition import CANDIDATE_LABELS, HAZARDS, NO_HAZARD_PROMPT, interpret_predictions
from app.services import choose_category, classify_issue, merge_image_hazard_risk, routing_reason, suggest_department


def category_preds(scores: dict) -> list[dict]:
    rest = (1.0 - sum(scores.values())) / max(len(CANDIDATE_LABELS) - len(scores), 1)
    return [{"label": prompt, "score": scores.get(cat, rest)} for cat, prompt in CANDIDATE_LABELS.items()]


def hazard_preds(key: str | None, score: float) -> list[dict]:
    prompts = {k: v[0] for k, v in HAZARDS.items()}
    others = [p for k, p in prompts.items() if k != key] + ([NO_HAZARD_PROMPT] if key else [])
    rest = (1.0 - score) / len(others)
    top = prompts[key] if key else NO_HAZARD_PROMPT
    return [{"label": top, "score": score}] + [{"label": p, "score": rest} for p in others]


class RoutingTests(unittest.TestCase):
    def test_new_departments(self):
        self.assertEqual(suggest_department("HVAC"), "HVAC Maintenance")
        self.assertEqual(suggest_department("IT"), "IT Infrastructure")

    def test_text_classifier_learns_hvac_and_it(self):
        self.assertEqual(classify_issue("Air conditioner broken", "The air conditioning is not cooling the room")[0], "HVAC")
        self.assertEqual(classify_issue("No wifi", "The wireless network in the lab is down")[0], "IT")

    def test_routing_reason_mentions_department(self):
        self.assertIn("IT Infrastructure", routing_reason("IT", "image+text"))


class InterpretTests(unittest.TestCase):
    def test_confident_photo_gives_suggestion(self):
        r = interpret_predictions(category_preds({"Plumbing": 0.8}), hazard_preds(None, 0.7), "m")
        self.assertEqual(r["category"], "Plumbing")
        self.assertFalse(r["needs_more_info"])
        self.assertIsNone(r["hazard"])
        self.assertTrue(r["suggested_title"])
        self.assertTrue(r["requires_human_review"])
        self.assertEqual(r["match_strength"], "strong")

    def test_unclear_photo_asks_for_more_information(self):
        r = interpret_predictions(category_preds({"Plumbing": 0.30, "Facility": 0.25}), hazard_preds(None, 0.6), "m")
        self.assertTrue(r["needs_more_info"])
        self.assertIsNone(r["suggested_title"])
        self.assertIsNone(r["suggested_description"])
        self.assertEqual(r["match_strength"], "uncertain")

    def test_close_scores_ask_for_more_information(self):
        r = interpret_predictions(category_preds({"Plumbing": 0.42, "Facility": 0.38}), None, "m")
        self.assertTrue(r["needs_more_info"])

    def test_confident_hazard_is_reported_with_risk_points(self):
        r = interpret_predictions(category_preds({"Electrical": 0.7}), hazard_preds("exposed_wiring", 0.8), "m")
        self.assertEqual(r["hazard"]["key"], "exposed_wiring")
        self.assertEqual(r["hazard"]["risk_points"], 5)
        self.assertIn("exposed electrical wiring", r["suggested_title"].lower())
        self.assertEqual(r["recommended_department"], "Electrical Maintenance")
        self.assertEqual(r["estimated_priority"], "High")
        self.assertEqual(r["suggested_severity"], "High")
        self.assertNotIn("%", r["suggested_description"])

    def test_weak_hazard_is_ignored(self):
        r = interpret_predictions(category_preds({"Facility": 0.7}), hazard_preds("structural_crack", 0.3), "m")
        self.assertIsNone(r["hazard"])

    def test_hazard_rescues_uncertain_category(self):
        r = interpret_predictions(category_preds({"Facility": 0.3, "Safety": 0.28}), hazard_preds("broken_glass", 0.75), "m")
        self.assertFalse(r["needs_more_info"])
        self.assertEqual(r["category"], "Safety")

    def test_unknown_label_raises(self):
        with self.assertRaises(RuntimeError):
            interpret_predictions([{"label": "nonsense", "score": 1.0}], None, "m")


class FusionTests(unittest.TestCase):
    def analysis(self, scores, **extra):
        best = max(scores, key=scores.get)
        return {"category": best, "score": scores[best], "category_scores": scores, "needs_more_info": False, **extra}

    def test_text_only(self):
        category, _, source, _ = choose_category("Leaking pipe", "Water leaking from the pipe under the sink", True, None)
        self.assertEqual((category, source), ("Plumbing", "text"))

    def test_image_only(self):
        category, _, source, _ = choose_category("", "", False, self.analysis({"HVAC": 0.8, "Facility": 0.2}))
        self.assertEqual((category, source), ("HVAC", "image"))

    def test_image_and_text_are_combined(self):
        category, _, source, details = choose_category("Room problem", "Something is wrong in the classroom", True, self.analysis({"IT": 0.9, "Other": 0.1}))
        self.assertEqual(source, "image+text")
        self.assertEqual(category, "IT")
        self.assertIn("text_category", details)
        self.assertIn("image_category", details)

    def test_fire_text_overrides_photo(self):
        category, _, source, _ = choose_category("Fire", "Flames and smoke in the electrical room", True, self.analysis({"Electrical": 0.95}))
        self.assertEqual((category, source), ("Safety", "safety_override"))

    def test_uncertain_photo_is_not_used(self):
        a = self.analysis({"IT": 0.9}, needs_more_info=True)
        _, _, source, _ = choose_category("Leaking pipe", "Water leaking from the pipe", True, a)
        self.assertEqual(source, "text")

    def test_no_signal_goes_to_administration(self):
        self.assertEqual(choose_category("", "", False, None)[0], "Other")


class HazardRiskTests(unittest.TestCase):
    def test_photo_hazard_raises_risk(self):
        hazard = {"key": "exposed_wiring", "label": "Exposed electrical wiring", "score": 0.8, "risk_points": 5}
        score, level, reasons = merge_image_hazard_risk(0, [], {"hazard": hazard})
        self.assertEqual((score, level), (5, "High"))
        self.assertIn("staff must confirm", reasons[0])

    def test_no_photo_keeps_keyword_risk(self):
        self.assertEqual(merge_image_hazard_risk(5, ["x"], None), (5, "High", ["x"]))

    def test_risk_is_capped(self):
        hazard = {"key": "exposed_wiring", "label": "Exposed electrical wiring", "score": 0.9, "risk_points": 5}
        self.assertEqual(merge_image_hazard_risk(9, [], {"hazard": hazard})[0], 10)


if __name__ == "__main__":
    unittest.main()
