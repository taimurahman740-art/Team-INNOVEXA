"""Hosted zero-shot image analysis for campus facility reports.

Method: CLIP (openai/clip-vit-large-patch14 by default) via Hugging Face hosted
inference, used *zero-shot*. The model has not been trained or fine-tuned on
campus photos. It compares the photo against short text prompts and returns a
similarity score per prompt. Two passes are made:

1. Category pass: one prompt per maintenance category (routing).
2. Hazard pass: one prompt per predefined visible hazard, plus a "no hazard" prompt.

Every result is a suggestion for human review. When the model is unsure the
response says so (needs_more_info) instead of inventing a report.
"""
import os

from huggingface_hub import InferenceClient

CANDIDATE_LABELS = {
    "Facility": "a photo of damaged campus facilities such as broken furniture, doors, windows, ceilings, walls or elevators",
    "Electrical": "a photo of electrical problems such as damaged sockets, exposed wires, broken lights or electrical panels",
    "Plumbing": "a photo of plumbing problems such as leaking pipes, water dripping, broken taps, clogged sinks or toilets",
    "HVAC": "a photo of an air conditioner, heater, radiator, ventilation fan or air vent",
    "IT": "a photo of computers, monitors, printers, projectors, network cables or wifi routers",
    "Cleaning": "a photo of campus cleanliness problems such as overflowing trash, litter, dirty floors or spills",
    "Safety": "a photo of a safety hazard such as broken glass, blocked emergency exits, damaged handrails or dangerous obstacles",
    "Other": "a photo of something unrelated to campus maintenance, such as a person, a pet, food or a landscape",
}

# key -> (prompt, human label, risk points added to the safety score, default category)
HAZARDS = {
    "exposed_wiring": ("a photo of exposed or bare electrical wires hanging out of a wall, ceiling or socket", "Exposed electrical wiring", 5, "Electrical"),
    "water_pooling": ("a photo of a puddle of standing water pooling on an indoor floor", "Water pooling on the floor", 2, "Plumbing"),
    "structural_crack": ("a photo of a large crack running through a concrete wall, ceiling or floor", "Structural crack", 3, "Facility"),
    "broken_glass": ("a photo of a broken or shattered glass window, door or glass pieces on the floor", "Broken glass", 2, "Safety"),
}
NO_HAZARD_PROMPT = "a photo of an ordinary campus scene with no visible hazard"

SUGGESTED_TITLES = {
    "Facility": "Damaged campus facility",
    "Electrical": "Electrical problem",
    "Plumbing": "Plumbing problem",
    "HVAC": "Heating or air-conditioning problem",
    "IT": "IT equipment or network problem",
    "Cleaning": "Cleaning needed",
    "Safety": "Possible safety hazard",
    "Other": "Campus issue",
}


def _threshold(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


# Below these, the photo is treated as unclear and the student is asked to describe it.
CATEGORY_MIN_SCORE = _threshold("IMAGE_CATEGORY_MIN_SCORE", 0.35)
CATEGORY_MIN_MARGIN = _threshold("IMAGE_CATEGORY_MIN_MARGIN", 0.10)
HAZARD_MIN_SCORE = _threshold("IMAGE_HAZARD_MIN_SCORE", 0.45)


def _pairs(predictions) -> list[tuple[str, float]]:
    """Accept huggingface_hub output objects or plain dicts; sort by score."""
    pairs = []
    for item in predictions or []:
        label = item["label"] if isinstance(item, dict) else item.label
        score = item["score"] if isinstance(item, dict) else item.score
        pairs.append((label, float(score)))
    return sorted(pairs, key=lambda pair: pair[1], reverse=True)


def interpret_predictions(category_predictions, hazard_predictions, model: str) -> dict:
    """Turn raw zero-shot scores into a reviewable, honest suggestion."""
    prompt_to_category = {prompt: category for category, prompt in CANDIDATE_LABELS.items()}
    category_scores = {}
    for prompt, score in _pairs(category_predictions):
        category = prompt_to_category.get(prompt)
        if category is None:
            raise RuntimeError("The image model returned an unknown category")
        category_scores[category] = round(score, 4)
    if not category_scores:
        raise RuntimeError("The image model returned no predictions")
    ranked = sorted(category_scores.items(), key=lambda pair: pair[1], reverse=True)
    best_category, best_score = ranked[0]
    margin = best_score - (ranked[1][1] if len(ranked) > 1 else 0.0)

    hazard = None
    if hazard_predictions:
        prompt_to_hazard = {prompt: key for key, (prompt, *_rest) in HAZARDS.items()}
        top_prompt, top_score = _pairs(hazard_predictions)[0]
        key = prompt_to_hazard.get(top_prompt)
        if key and top_score >= HAZARD_MIN_SCORE:
            _, label, points, _ = HAZARDS[key]
            hazard = {"key": key, "label": label, "score": round(top_score, 4), "risk_points": points}

    category = best_category
    uncertain = best_score < CATEGORY_MIN_SCORE or margin < CATEGORY_MIN_MARGIN or best_category == "Other"
    if uncertain and hazard:
        # A confident hazard is meaningful on its own; route by the hazard.
        category = HAZARDS[hazard["key"]][3]
        uncertain = False

    result = {
        "category": category,
        "score": category_scores.get(category, best_score),
        "model": model,
        "method": "zero-shot CLIP (not trained on campus photos)",
        "category_scores": category_scores,
        "top_categories": [{"category": c, "score": s} for c, s in ranked[:3]],
        "hazard": hazard,
        "needs_more_info": uncertain,
        "requires_human_review": True,
        "suggested_title": None,
        "suggested_description": None,
        "message": None,
    }
    if uncertain:
        result["message"] = "The photo is not clear enough to identify the problem. Please add a short title and description."
        return result

    if hazard:
        title = f"Possible {hazard['label'].lower()}"
        seen = f"{hazard['label'].lower()} ({round(hazard['score'] * 100)}% match)"
    else:
        title = SUGGESTED_TITLES[category]
        seen = f"a {category} issue ({round(result['score'] * 100)}% match)"
    result["suggested_title"] = title
    result["suggested_description"] = (
        f"Photo report. The image appears to show {seen}. "
        "This text was suggested automatically from the photo and should be checked by the reporter and staff."
    )
    result["message"] = "Suggested from the photo. Please review before submitting."
    return result


def classify_campus_image(image_bytes: bytes, token: str, model: str) -> dict:
    """Run the category and hazard passes and return an interpreted suggestion."""
    client = InferenceClient(provider="auto", api_key=token, timeout=30)
    category_predictions = client.zero_shot_image_classification(
        image_bytes,
        candidate_labels=list(CANDIDATE_LABELS.values()),
        hypothesis_template="This is {0}.",
        model=model,
    )
    try:
        hazard_predictions = client.zero_shot_image_classification(
            image_bytes,
            candidate_labels=[prompt for prompt, *_ in HAZARDS.values()] + [NO_HAZARD_PROMPT],
            hypothesis_template="This is {0}.",
            model=model,
        )
    except Exception:
        hazard_predictions = None  # hazard detection is optional; category still useful
    return interpret_predictions(category_predictions, hazard_predictions, model)
