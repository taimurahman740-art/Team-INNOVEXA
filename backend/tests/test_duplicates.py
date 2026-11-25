"""Duplicate detection (feature 7): behaviour and the calibration pairs behind the thresholds."""
import base64
import io
import unittest

from PIL import Image, ImageDraw, ImageEnhance

from app.duplicates import IMAGE_THRESHOLD, TEXT_THRESHOLD, find_possible_duplicates, image_similarity, image_vector, text_similarities

DUPLICATE_PAIRS = [
    ("Water leaking from ceiling Water is dripping from the ceiling in the library third floor", "Ceiling leak Water drips from the ceiling near the library stairs on floor 3"),
    ("Air conditioner not cooling The AC in room 412 runs but does not cool", "Room 412 air conditioner broken Aircon blows warm air, not cooling"),
    ("Projector does not turn on Room 105 projector has no power", "Room 105 projector broken The projector won't turn on"),
    ("Blocked sink drain The sink in the student center restroom is clogged", "Clogged sink Student center washroom sink is blocked and water won't drain"),
]
DIFFERENT_PAIRS = [
    ("Water leaking from ceiling Water is dripping from the ceiling in the library", "Blocked sink drain The sink in the student center restroom is clogged"),
    ("Air conditioner not cooling The AC in room 412 runs but does not cool", "Heater too hot Radiator in room 305 cannot be turned down"),
    ("Projector does not turn on Room 105 projector has no power", "Wi-Fi unavailable Wireless network down in the library"),
    ("Broken classroom light The ceiling light does not turn on", "Exposed wire near socket Wire is exposed near the hallway outlet"),
]


def photo(variant=0, shift=0, bright=1.0, crop=0) -> str:
    img = Image.new("RGB", (640, 480), (120 + variant * 20, 130, 140))
    d = ImageDraw.Draw(img)
    d.rectangle([80 + shift, 90, 560 + shift, 380], fill=(200, 205, 210))
    d.line([(200 + shift, 120), (260, 330), (310, 200), (390, 350)], fill=(40, 40, 45), width=12)
    if variant:
        d.ellipse([100, 100, 400, 400], fill=(30, 90, 160))
    if crop:
        img = img.crop((crop, crop, 640 - crop, 480 - crop))
    img = ImageEnhance.Brightness(img).enhance(bright)
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def report(i, title, description, department="Plumbing Maintenance", building="Library", status="Submitted", image_data=None):
    return {"id": i, "title": title, "description": description, "department": department, "building": building, "status": status, "image_data": image_data}


class TextSimilarityTests(unittest.TestCase):
    def test_reworded_duplicates_pass_threshold(self):
        for a, b in DUPLICATE_PAIRS:
            self.assertGreaterEqual(text_similarities(a, [b])[0], TEXT_THRESHOLD, a)

    def test_different_problems_stay_below_threshold(self):
        for a, b in DIFFERENT_PAIRS:
            self.assertLess(text_similarities(a, [b])[0], TEXT_THRESHOLD, a)


class ImageSimilarityTests(unittest.TestCase):
    def test_same_scene_reshot_is_similar(self):
        self.assertGreaterEqual(image_similarity(image_vector(photo()), image_vector(photo(shift=15, bright=1.1, crop=20))), IMAGE_THRESHOLD)

    def test_different_scene_is_not(self):
        self.assertLess(image_similarity(image_vector(photo()), image_vector(photo(variant=3))), IMAGE_THRESHOLD)

    def test_bad_image_is_ignored(self):
        self.assertIsNone(image_vector("data:image/png;base64,not-an-image"))
        self.assertIsNone(image_vector(None))


class FindDuplicatesTests(unittest.TestCase):
    def test_flags_similar_open_report(self):
        new = report(None, "Ceiling leak", "Water drips from the ceiling near the library stairs on floor 3")
        matches = find_possible_duplicates(new, [report(5, "Water leaking from ceiling", "Water is dripping from the ceiling in the library third floor")])
        self.assertEqual(matches[0]["issue_id"], 5)
        self.assertIn("Similar description", matches[0]["reasons"])

    def test_ignores_resolved_and_other_departments_and_buildings(self):
        new = report(None, "Ceiling leak", "Water drips from the ceiling in the library")
        candidates = [
            report(6, "Water leaking from ceiling", "Water is dripping from the ceiling in the library", status="Resolved"),
            report(7, "Water leaking from ceiling", "Water is dripping from the ceiling", department="IT Infrastructure", building="Dormitory A"),
        ]
        self.assertEqual(find_possible_duplicates(new, candidates), [])

    def test_unrelated_report_is_not_flagged(self):
        new = report(None, "Blocked sink", "The restroom sink is clogged")
        self.assertEqual(find_possible_duplicates(new, [report(8, "Low water pressure", "Shower pressure is weak in dormitory A")]), [])

    def test_same_photo_flags_even_with_short_text(self):
        img = photo()
        new = report(None, "Photo report", "Photo report.", image_data=photo(shift=10, crop=15))
        matches = find_possible_duplicates(new, [report(9, "Exposed wire", "Wire hanging from the ceiling", image_data=img)])
        self.assertEqual(matches[0]["issue_id"], 9)
        self.assertIn("Very similar photo", matches[0]["reasons"])


if __name__ == "__main__":
    unittest.main()
