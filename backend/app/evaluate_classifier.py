"""Evaluate the current category classifier against labelled synthetic sample rows.

Run from backend/: python -m app.evaluate_classifier
This reports agreement on a hand-labelled synthetic demonstration set, NOT real-world
model accuracy. The synthetic examples were authored for this project and are not
independent campus observations.
"""
import csv
from collections import defaultdict
from pathlib import Path
from .services import classify_issue

DATASET = Path(__file__).resolve().parents[1] / "data" / "tongmyong_sample_issues.csv"


def predict_category(title: str, description: str) -> str:
    label, confidence = classify_issue(title, description)
    return label if confidence >= 0.30 else "Other"


def main():
    with DATASET.open(encoding="utf-8-sig", newline="") as file:
        rows = [row for row in csv.DictReader(file) if row.get("source_type") == "synthetic"]
    if not rows:
        raise SystemExit("No synthetic rows found in the sample CSV.")

    labels = sorted({row["category"] for row in rows} | {"Other"})
    matrix = defaultdict(lambda: defaultdict(int))
    correct = 0
    for row in rows:
        actual = row["category"]
        predicted = predict_category(row["title"], row["description"])
        matrix[actual][predicted] += 1
        correct += actual == predicted
        print(f'{row["id"]}: expected={actual:10} predicted={predicted:10} {"MATCH" if actual == predicted else "MISMATCH"}')

    print("\nPer-class metrics (one-vs-rest):")
    f1_scores = []
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[actual][label] for actual in labels if actual != label)
        fn = sum(matrix[label][pred] for pred in labels if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        if any(row["category"] == label for row in rows):
            f1_scores.append(f1)
        print(f"{label:10} precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}")

    total = len(rows)
    print(f"\nSynthetic-set agreement: {correct}/{total} = {correct / total:.3f}")
    print(f"Macro F1: {sum(f1_scores) / len(f1_scores):.3f}" if f1_scores else "Macro F1: n/a")
    print("\nConfusion matrix (rows=expected, columns=predicted):")
    print("expected\\pred".ljust(13) + " ".join(label[:8].rjust(9) for label in labels))
    for actual in labels:
        print(actual.ljust(13) + " ".join(str(matrix[actual][pred]).rjust(9) for pred in labels))
    print("\nLIMITATION: these hand-written synthetic examples are not a representative or independent campus test set.")
    print("Do not report this result as validated model accuracy. Obtain anonymised, human-labelled real reports and reserve an untouched test set.")


if __name__ == "__main__":
    main()
