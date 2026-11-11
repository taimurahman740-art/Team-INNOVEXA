"""Hosted zero-shot image classification for campus facility reports."""
from huggingface_hub import InferenceClient

CANDIDATE_LABELS = {
    "Facility": "a photo of damaged campus facilities, broken furniture, doors, windows, ceilings, air conditioners or elevators",
    "Electrical": "a photo of electrical problems such as damaged sockets, exposed wires, broken lights or electrical equipment",
    "Plumbing": "a photo of plumbing problems such as leaking pipes, water dripping, broken taps, clogged sinks or toilets",
    "Cleaning": "a photo of campus cleanliness problems such as overflowing trash, litter, dirty floors or spills",
    "Safety": "a photo of a safety hazard such as broken glass, blocked emergency exits, damaged handrails or dangerous obstacles",
    "Other": "a photo of something unrelated to campus maintenance or a campus issue that does not fit the other categories",
}

def classify_campus_image(image_bytes: bytes, token: str, model: str) -> dict:
    """Return the best category and model similarity score for one image."""
    client = InferenceClient(provider="auto", api_key=token, timeout=30)
    predictions = client.zero_shot_image_classification(
        image_bytes,
        candidate_labels=list(CANDIDATE_LABELS.values()),
        hypothesis_template="This is {0}.",
        model=model,
    )
    if not predictions:
        raise RuntimeError("The image model returned no predictions")
    label_to_category = {description: category for category, description in CANDIDATE_LABELS.items()}
    best = predictions[0]
    category = label_to_category.get(best.label)
    if category is None:
        raise RuntimeError("The image model returned an unknown category")
    return {"category": category, "score": round(float(best.score), 4), "model": model}
