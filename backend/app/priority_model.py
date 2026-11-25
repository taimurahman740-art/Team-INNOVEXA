"""Machine-learning priority prediction (feature 5): Random Forest baseline.

Training data: the 44 labelled rows in data/tongmyong_sample_issues.csv
(14 paraphrased public Tongmyong board posts, 30 synthetic rows written by the
team). This is a small, mostly synthetic set, so the model is a documented
baseline, not a validated predictor. See app/evaluate_priority.py.

Features used:
  * category (one-hot)
  * safety risk score 0-10 (keyword triage, plus any photo hazard)
  * affected-area traffic 0-2, derived from location words (rule-based)
  * service-disruption cue in the text (e.g. "not working", "no water")
Not used yet: historical resolution time. The sample rows have no resolution
history; it can be added once Neon holds enough resolved reports.

Safety floor: a report with risk score >= 5 is always High, whatever the model says.
"""
import csv
import re
from pathlib import Path

from .services import assess_safety_risk

CATEGORIES = ["Facility", "Electrical", "Plumbing", "HVAC", "IT", "Cleaning", "Safety", "Other"]
PRIORITIES = ["Low", "Medium", "High"]
DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "tongmyong_sample_issues.csv"

HIGH_TRAFFIC = re.compile(r"\b(entrance|exit|lobby|hallway|corridor|stair|stairwell|cafeteria|canteen|elevator|lift|bus stop|main building|library|lecture hall|auditorium|gym)\b")
MEDIUM_TRAFFIC = re.compile(r"\b(classroom|lecture|laboratory|lab|study|lounge|common area|restroom|washroom|bathroom|toilet|kitchen|student center)\b")
DISRUPTION = re.compile(r"\b(not working|not turning on|does not turn on|doesn't work|broken|blocked|clogged|outage|no water|no power|no internet|unavailable|cannot|can't|leak(?:ing)?|overflow(?:ing)?|offline)\b")
FEATURE_NAMES = [f"category={c}" for c in CATEGORIES] + ["risk_score", "area_traffic", "service_disrupted"]


def area_traffic(location: str) -> int:
    """0 = low (rooms, offices), 1 = medium (classrooms, labs, restrooms), 2 = high (entrances, corridors, cafeterias)."""
    text = (location or "").lower()
    if HIGH_TRAFFIC.search(text):
        return 2
    if MEDIUM_TRAFFIC.search(text):
        return 1
    return 0


def features(category: str, title: str, description: str, location: str, risk_score: int) -> list[float]:
    text = f"{title} {description}".lower()
    return [1.0 if category == c else 0.0 for c in CATEGORIES] + [
        float(risk_score), float(area_traffic(location)), 1.0 if DISRUPTION.search(text) else 0.0,
    ]


def load_training_rows() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = [r for r in csv.DictReader(file) if r.get("priority") in PRIORITIES and r.get("category") in CATEGORIES]
    for r in rows:
        r["risk_score"] = assess_safety_risk(r["title"], r["description"])[0]
    return rows


def training_matrix(rows: list[dict]):
    X = [features(r["category"], r["title"], r["description"], r["location"], r["risk_score"]) for r in rows]
    y = [r["priority"] for r in rows]
    return X, y


def new_model():
    from sklearn.ensemble import RandomForestClassifier
    # Shallow trees and balanced class weights: the dataset is tiny and Medium dominates.
    return RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=2, class_weight="balanced", random_state=42)


class PriorityModel:
    def __init__(self):
        self.model = None
        self.error = None
        try:
            X, y = training_matrix(load_training_rows())
            self.model = new_model().fit(X, y)
            self.training_rows = len(y)
        except Exception as exc:  # scikit-learn missing or data unreadable: fall back to rules
            self.error = f"{type(exc).__name__}: {exc}"
            self.training_rows = 0

    @property
    def available(self) -> bool:
        return self.model is not None

    def predict(self, category: str, title: str, description: str, location: str, risk_score: int) -> dict:
        x = features(category, title, description, location, risk_score)
        probs = {str(k): float(v) for k, v in zip(self.model.classes_, self.model.predict_proba([x])[0])}
        predicted = max(probs, key=probs.get)
        factors = [f"Category: {category}", f"Safety risk score: {risk_score} of 10",
                   f"Area traffic: {['low', 'medium', 'high'][int(x[-2])]}"]
        if x[-1]:
            factors.append("Text describes a service that is not working")
        return {
            "method": "random_forest",
            "predicted": predicted,
            "probabilities": {k: round(float(v), 3) for k, v in probs.items()},
            "factors": factors,
            "training_rows": self.training_rows,
        }


_model = None


def get_model() -> PriorityModel:
    global _model
    if _model is None:
        _model = PriorityModel()
    return _model


def predict_priority(category: str, title: str, description: str, location: str, risk_score: int, rule_priority: str) -> dict:
    """Model prediction plus the safety floor. Falls back to the rule priority if the model is unavailable."""
    model = get_model()
    if model.available:
        result = model.predict(category, title, description, location, risk_score)
    else:
        result = {"method": "rules", "predicted": rule_priority, "factors": ["Model unavailable; keyword rules used"], "error": model.error}
    result["rule_priority"] = rule_priority
    result["safety_floor_applied"] = risk_score >= 5 and result["predicted"] != "High"
    result["final"] = "High" if risk_score >= 5 else result["predicted"]
    return result
