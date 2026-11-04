"""Evaluate the prototype Naive Bayes classifier on a separate labelled holdout set.

Run from the backend directory: python -m app.evaluate_classifier
This is a small demonstration set, not a representative campus benchmark.
"""
from collections import defaultdict
from .services import classify_issue

HOLDOUT = [
    ("Electrical", "The wall outlet is sparking and has an exposed wire."),
    ("Electrical", "The classroom lamp and ceiling light do not turn on."),
    ("Plumbing", "Water is leaking from the bathroom faucet."),
    ("Plumbing", "The toilet drain is blocked and overflowing."),
    ("Cleaning", "The classroom floor is dirty and needs cleaning."),
    ("Cleaning", "The rubbish bin is full of garbage."),
    ("Safety", "There is broken glass on the stairs."),
    ("Safety", "Smoke is coming from a room and people may be in danger."),
    ("Facility", "The classroom air conditioner is broken."),
    ("Facility", "The elevator lift is not working."),
    ("Other", "I found a student identification card."),
    ("Other", "The campus Wi-Fi connection is unavailable."),
]

def main():
    labels = sorted({label for label, _ in HOLDOUT})
    matrix = {actual: {pred: 0 for pred in labels} for actual in labels}
    for actual, text in HOLDOUT:
        predicted, confidence = classify_issue("Campus report", text)
        if predicted not in matrix[actual]:
            matrix[actual][predicted] = 0
        matrix[actual][predicted] += 1
        print(f"actual={actual:10} predicted={predicted:10} confidence={confidence:.3f}")
    print("\nPer-class metrics (one-vs-rest):")
    f1_values = []
    for label in labels:
        tp = matrix[label].get(label, 0)
        fp = sum(matrix[actual].get(label, 0) for actual in labels if actual != label)
        fn = sum(count for pred, count in matrix[label].items() if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        print(f"{label:10} precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}")
    total = len(HOLDOUT)
    correct = sum(matrix[label].get(label, 0) for label in labels)
    print(f"\nAccuracy: {correct}/{total} = {correct / total:.3f}")
    print(f"Macro F1: {sum(f1_values) / len(f1_values):.3f}")
    print("\nConfusion matrix (rows=actual, columns=predicted):")
    print("actual\\pred".ljust(13) + " ".join(label[:8].rjust(9) for label in labels))
    for actual in labels:
        print(actual.ljust(13) + " ".join(str(matrix[actual].get(pred, 0)).rjust(9) for pred in labels))
    print("\nWARNING: this tiny hand-written holdout set is illustrative only; do not report it as real-world campus accuracy.")

if __name__ == "__main__":
    main()