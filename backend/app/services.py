"""Lightweight supervised text classifier for campus issue triage.

The model is trained on a small, hand-labelled starter dataset. It is a
capstone prototype: predictions must be reviewed by campus staff.
"""
import re
from collections import Counter, defaultdict
from math import log

TRAINING_EXAMPLES = [
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

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

class NaiveBayesIssueClassifier:
    """Multinomial Naive Bayes text classifier trained from labelled examples."""
    def __init__(self):
        self.class_docs = Counter()
        self.word_counts = defaultdict(Counter)
        self.vocabulary = set()
        for label, sample in TRAINING_EXAMPLES:
            words = _tokens(sample)
            self.class_docs[label] += 1
            self.word_counts[label].update(words)
            self.vocabulary.update(words)
        self.total_docs = sum(self.class_docs.values())
        self.total_words = {c: sum(counts.values()) for c, counts in self.word_counts.items()}

    def predict(self, text: str) -> tuple[str, float]:
        words = _tokens(text)
        if not words:
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
    if any(word in text for word in ("fire", "smoke", "sparking", "exposed wire", "electric shock", "gas leak", "broken glass", "injury", "dangerous", "emergency")):
        return "High"
    if any(word in text for word in ("leak", "broken", "not working", "blocked", "overflow", "damaged", "clogged", "outage")):
        return "Medium"
    return "Low"

def suggest_department(category: str) -> str:
    return {
        "Electrical": "Electrical Maintenance", "Plumbing": "Plumbing Maintenance",
        "Cleaning": "Cleaning Services", "Safety": "Campus Safety",
        "Facility": "Facilities Maintenance", "Other": "Campus Administration",
    }.get(category, "Campus Administration")
