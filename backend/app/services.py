"""Lightweight supervised text classifier for Tongmyong campus issue triage.

Training combines a small, hand-labelled starter set with anonymised,
English paraphrases of public Tongmyong University dormitory repair posts.
The public-board examples are a small seed dataset, not a representative
campus-wide sample. Predictions must be reviewed by campus staff.
"""
import csv
import re
from collections import Counter, defaultdict
from math import log
from pathlib import Path

STARTER_TRAINING_EXAMPLES = [
    ("Electrical", "broken classroom light lamp bulb not turning on"),
    ("Electrical", "power socket outlet is damaged"),
    ("Electrical", "exposed wire sparks electric shock circuit breaker"),
    ("Electrical", "electricity power outage in computer lab"),
    ("Electrical", "projector cable and electrical connection problem"),
    ("Plumbing", "water leaking from pipe ceiling faucet sink"),
    ("Plumbing", "toilet is blocked drain is clogged"),
    ("Plumbing", "bathroom tap has no water"),
    ("Plumbing", "overflowing water pipe burst"),
    ("Cleaning", "trash bin garbage waste is full"),
    ("Cleaning", "dirty classroom floor needs cleaning"),
    ("Cleaning", "food spill on cafeteria floor"),
    ("Cleaning", "bathroom is dirty and smells bad"),
    ("Safety", "broken glass sharp object on floor"),
    ("Safety", "smoke fire burning smell emergency hazard"),
    ("Safety", "loose handrail dangerous stairs"),
    ("Safety", "exposed dangerous object may injure students"),
    ("Facility", "air conditioner is not working classroom hot"),
    ("Facility", "broken desk chair door window ceiling"),
    ("Facility", "damaged classroom furniture and projector"),
    ("Facility", "elevator lift is not working"),
    ("Facility", "roof is damaged and water dripping"),
    ("Other", "lost property student card found item"),
    ("Other", "question about campus service or administration"),
    ("Other", "internet wifi connection is unavailable"),
]

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "tongmyong_sample_issues.csv"

def load_tongmyong_training_examples() -> list[tuple[str, str]]:
    """Load public Tongmyong dormitory examples; ignore synthetic evaluation rows."""
    examples = []
    with DATASET_PATH.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("source_type") in {"public_page_paraphrase", "public_board_paraphrase"}:
                label = row.get("category", "").strip()
                text = " ".join((row.get("title", ""), row.get("description", ""))).strip()
                if label and text:
                    examples.append((label, text))
    return examples

# The live classifier now actually trains on the Tongmyong-labelled public-board
# examples as well as the starter examples. Synthetic evaluation rows are excluded.
TRAINING_EXAMPLES = STARTER_TRAINING_EXAMPLES + load_tongmyong_training_examples()

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

class NaiveBayesIssueClassifier:
    """Multinomial Naive Bayes text classifier trained from labelled examples."""
    def __init__(self, training_examples=None):
        self.training_examples = training_examples if training_examples is not None else TRAINING_EXAMPLES
        self.class_docs = Counter()
        self.word_counts = defaultdict(Counter)
        self.vocabulary = set()
        for label, sample in self.training_examples:
            words = _tokens(sample)
            self.class_docs[label] += 1
            self.word_counts[label].update(words)
            self.vocabulary.update(words)
        self.total_docs = sum(self.class_docs.values())
        self.total_words = {c: sum(counts.values()) for c, counts in self.word_counts.items()}

    def predict(self, text: str) -> tuple[str, float]:
        words = _tokens(text)
        if not words or not self.total_docs:
            return "Other", 0.0
        scores = {}
        vocab_size = max(len(self.vocabulary), 1)
        for label, docs in self.class_docs.items():
            score = log(docs / self.total_docs)
            denom = self.total_words[label] + vocab_size
            for word in words:
                score += log((self.word_counts[label][word] + 1) / denom)
            scores[label] = score
        peak = max(scores.values())
        exp_scores = {k: __import__("math").exp(v - peak) for k, v in scores.items()}
        total = sum(exp_scores.values())
        label = max(scores, key=scores.get)
        return label, exp_scores[label] / total

_classifier = NaiveBayesIssueClassifier()

def classify_issue(title: str, description: str) -> tuple[str, float]:
    return _classifier.predict(f"{title} {description}")

def suggest_category(title: str, description: str) -> str:
    category, confidence = classify_issue(title, description)
    return category if confidence >= 0.30 else "Other"

def suggest_priority(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    # Safety triage overrides routine maintenance priority when an immediate
    # hazard is detected (for example, water leaking near a light fixture).
    risk_score, _, _ = assess_safety_risk(title, description)
    if risk_score >= 5:
        return "High"
    if any(word in text for word in ("fire", "smoke", "sparking", "exposed wire", "electric shock", "gas leak", "broken glass", "injury", "dangerous", "emergency")):
        return "High"
    if any(word in text for word in ("leak", "broken", "not working", "blocked", "overflow", "damaged", "clogged", "outage")):
        return "Medium"
    return "Low"

def _is_negated_hazard(text: str, match_start: int) -> bool:
    """Avoid triggering a hazard rule when its matched phrase is explicitly negated."""
    preceding_text = text[max(0, match_start - 32):match_start]
    direct_negation = re.search(
        r"\b(?:no|not|never|without|free of|isn't|aren't|wasn't|weren't)\s+(?:any\s+)?$",
        preceding_text,
    )
    coordinated_negation = re.search(
        r"\bno\s+(?:fire|smoke|gas|water)(?:\s*,\s*(?:fire|smoke|gas|water))*\s+or\s+$|\bno\s+(?:fire|smoke|gas|water)\s+or\s+$",
        preceding_text,
    )
    return direct_negation is not None or coordinated_negation is not None


def assess_safety_risk(title: str, description: str) -> tuple[int, str, list[str]]:
    """Keyword triage aid only; not a validated safety prediction model."""
    text = f"{title} {description}".lower()
    rules = [
        (r"\b(fire(?! (?:exit|extinguisher|alarm)\b)|flames|smoke|explosion|gas leak|gas is leaking|smell of gas|gas smell|rotten egg smell)\b",
         5, "Possible fire, smoke, gas or explosion"),
        (r"\b(?:"
         r"fire alarm (?:is )?(?:not working|broken|disabled|offline|out of service)|"
         r"smoke detector (?:is )?(?:not working|broken|disabled|offline|out of service)|"
         r"(?:fire )?extinguishers? (?:is |are )?(?:missing|empty|unavailable|not present|not available|out of service|not working|broken)|"
         r"(?:missing|empty|unavailable|not present|not available|out of service|not working|broken) (?:fire )?extinguishers?|"
         r"(?:sprinkler|sprinklers|sprinkler system|sprinkler systems) (?:is |are )?(?:not working|broken|disabled|offline|out of service)|"
         r"(?:emergency lighting|emergency lights) (?:is |are |has |have )?(?:not working|broken|out|offline|failed)"
         r")\b",
         5, "Fire protection or emergency equipment unavailable"),
        (r"\b(electric shock|electrocut(?:ed|ion)|sparking|sparks|exposed wire|live wire|bare wire|burning outlet)\b",
         5, "Possible electrical danger"),
        (r"\b(?:water|leak(?:ing)?|dripping|drip)\b.{0,100}\b(?:light|lamp|bulb|electrical fixture|wiring|outlet|socket|switch|electrical equipment)\b|\b(?:light|lamp|bulb|electrical fixture|wiring|outlet|socket|switch|electrical equipment)\b.{0,100}\b(?:water|leak(?:ing)?|dripping|drip)\b",
         5, "Water near an electrical fixture or equipment"),
        (r"\b(structural failure|building (?:is )?cracking|large crack in (?:the )?(?:wall|ceiling)|ceiling (?:is )?falling|ceiling collapse|wall collapse|about to collapse)\b",
         5, "Possible structural danger"),
        (r"\b(injured|injury|bleeding|unconscious|trapped|someone fell|person fell|electric shock victim)\b",
         5, "Possible injury or immediate danger"),
        (r"\b(broken glass|shattered glass|sharp object|slippery floor|flooding|water leak|water is flooding|water near (?:an? )?(?:electrical|power) (?:socket|outlet|equipment)|water (?:is )?leaking near (?:a |an )?(?:electrical|power) (?:socket|outlet|equipment))\b",
         2, "Potential physical hazard"),
        (r"\b(?:blocked|obstructed) (?:fire |emergency )?exits?\b|"
         r"\b(?:fire |emergency )?exits? (?:are |is )?(?:blocked|obstructed)\b|"
         r"\b(?:exit|evacuation) routes? (?:are |is )?(?:blocked|obstructed)\b|"
         r"\b(?:fire )?escapes? (?:are |is )?(?:blocked|obstructed)\b|"
         r"\b(?:emergency )?egress (?:is |are )?(?:blocked|obstructed)\b",
         5, "Blocked emergency exit or evacuation route"),
        (r"\b(loose handrail|loose railing|broken handrail|missing handrail)\b",
         2, "Potential fall hazard"),
    ]
    score = 0
    reasons = []
    for pattern, points, reason in rules:
        matches = re.finditer(pattern, text)
        if any(not _is_negated_hazard(text, match.start()) for match in matches):
            score += points
            reasons.append(reason)
    score = min(score, 10)
    level = "High" if score >= 5 else "Moderate" if score >= 2 else "Low"
    return score, level, reasons


def suggest_department(category: str) -> str:
    return {
        "Electrical": "Electrical Maintenance", "Plumbing": "Plumbing Maintenance",
        "Cleaning": "Cleaning Services", "Safety": "Campus Safety",
        "Facility": "Facilities Maintenance", "Other": "Campus Administration",
    }.get(category, "Campus Administration")
