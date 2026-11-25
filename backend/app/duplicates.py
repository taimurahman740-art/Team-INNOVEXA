"""Duplicate-ticket detection (feature 7): text + image similarity with cosine scores.

A new report is compared with *open* reports (Submitted or In Progress) in the
same department or the same building. Matches are stored as "possible
duplicates" for staff review. A report is never rejected or merged automatically.

Text: TF-IDF vectors (unigrams + bigrams, English stop words removed) of
title + description, compared with cosine similarity. The vocabulary is fitted
on the sample dataset plus the reports being compared, so rare words stay
informative even when only a few reports are open.

Image: a compact feature vector per photo (16x16 greyscale layout, mean-centred,
plus a 4x4x4 RGB colour histogram), compared with cosine similarity. This finds
the same scene photographed again; it is a hand-crafted image feature, not a
learned embedding, so it will not match two different photos of "the same kind"
of problem.

Thresholds can be changed with environment variables (see below). Defaults were
set on a small hand-made check (tests/test_duplicates.py): 4 reworded duplicate
pairs scored 0.27-0.52 on text, 4 different problems in the same department
scored 0.00-0.04; a re-shot photo of the same scene scored 0.71, a different
scene 0.17. Re-check them on real campus reports and photos.
"""
import base64
import binascii
import csv
import io
import os
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "tongmyong_sample_issues.csv"
OPEN_STATUSES = ("Submitted", "In Progress")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


TEXT_THRESHOLD = _env_float("DUPLICATE_TEXT_THRESHOLD", 0.25)
IMAGE_THRESHOLD = _env_float("DUPLICATE_IMAGE_THRESHOLD", 0.60)
COMBINED_THRESHOLD = _env_float("DUPLICATE_COMBINED_THRESHOLD", 0.35)
MAX_MATCHES = 3


def _corpus_texts() -> list[str]:
    try:
        with DATASET_PATH.open(encoding="utf-8-sig", newline="") as file:
            return [f"{r['title']} {r['description']}" for r in csv.DictReader(file)]
    except OSError:
        return []


_BACKGROUND = None


def text_similarities(new_text: str, other_texts: list[str]) -> list[float]:
    """Cosine similarity between new_text and each of other_texts (0..1)."""
    if not other_texts or not new_text.strip():
        return [0.0] * len(other_texts)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    global _BACKGROUND
    if _BACKGROUND is None:
        _BACKGROUND = _corpus_texts()
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    vectorizer.fit(_BACKGROUND + other_texts + [new_text])
    matrix = vectorizer.transform([new_text] + other_texts)
    return [round(float(s), 4) for s in cosine_similarity(matrix[0], matrix[1:])[0]]


def image_vector(image_data: str | None):
    """Feature vector for a data-URL image, or None if there is no usable image."""
    if not image_data or "," not in image_data:
        return None
    try:
        import numpy as np
        from PIL import Image
        raw = base64.b64decode(image_data.split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as img:
            rgb = img.convert("RGB")
            grey = np.asarray(rgb.convert("L").resize((16, 16)), dtype=float).ravel()
            small = np.asarray(rgb.resize((32, 32)), dtype=int).reshape(-1, 3) // 64
        grey = grey - grey.mean()
        grey = grey / (np.linalg.norm(grey) or 1.0)
        hist = np.bincount(small[:, 0] * 16 + small[:, 1] * 4 + small[:, 2], minlength=64).astype(float)
        hist = hist / (np.linalg.norm(hist) or 1.0)
        return np.concatenate([grey, hist]) / np.sqrt(2)
    except (binascii.Error, ValueError, OSError, ImportError):
        return None


def image_similarity(a, b) -> float | None:
    if a is None or b is None:
        return None
    import numpy as np
    return round(float(max(0.0, min(1.0, np.dot(a, b)))), 4)


def find_possible_duplicates(new: dict, candidates: list[dict]) -> list[dict]:
    """new / candidates: {id, title, description, department, building, image_data, status}.

    Returns up to MAX_MATCHES matches, best first:
    {issue_id, title, text_score, image_score, score, reasons}.
    """
    pool = [c for c in candidates
            if c.get("id") != new.get("id") and c.get("status") in OPEN_STATUSES
            and ((new.get("department") and c.get("department") == new.get("department"))
                 or (new.get("building") and c.get("building") and c["building"].lower() == new["building"].lower()))]
    if not pool:
        return []
    text_scores = text_similarities(f"{new.get('title', '')} {new.get('description', '')}",
                                    [f"{c.get('title', '')} {c.get('description', '')}" for c in pool])
    new_vec = image_vector(new.get("image_data"))
    matches = []
    for candidate, text_score in zip(pool, text_scores):
        image_score = image_similarity(new_vec, image_vector(candidate.get("image_data"))) if new_vec is not None else None
        score = 0.6 * text_score + 0.4 * image_score if image_score is not None else text_score
        same_building = bool(new.get("building") and candidate.get("building") and candidate["building"].lower() == new["building"].lower())
        reasons = []
        if text_score >= TEXT_THRESHOLD:
            reasons.append("Similar description")
        if image_score is not None and image_score >= IMAGE_THRESHOLD:
            reasons.append("Very similar photo")
        if not reasons and score >= COMBINED_THRESHOLD and same_building:
            reasons.append("Similar description and photo in the same building")
        if reasons:
            if same_building:
                reasons.append("Same building")
            matches.append({"issue_id": candidate["id"], "title": candidate.get("title"), "status": candidate.get("status"),
                            "text_score": text_score, "image_score": image_score, "score": round(score, 4), "reasons": reasons})
    return sorted(matches, key=lambda m: m["score"], reverse=True)[:MAX_MATCHES]
