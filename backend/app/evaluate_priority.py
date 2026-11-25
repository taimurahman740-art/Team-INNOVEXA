"""Evaluate the Random Forest priority model against the existing keyword rules.

Run from backend/: python -m app.evaluate_priority

Method: stratified 4-fold cross-validation, repeated 10 times with different
shuffles, on the 44 labelled sample rows. Both the model and the rule baseline
are scored on exactly the same held-out folds.

LIMITATION: 30 of the 44 rows are synthetic and written by the team, and every
High example is synthetic. These numbers show the pipeline works; they are NOT
a measure of real-world accuracy. Re-run this on human-labelled Neon reports
before claiming performance.
"""
from collections import Counter

from .priority_model import PRIORITIES, load_training_rows, new_model, training_matrix
from .services import suggest_priority


def rule_priority(row) -> str:
    # The production rule path: keyword priority, with the risk >= 5 safety floor.
    return "High" if row["risk_score"] >= 5 else suggest_priority(row["title"], row["description"])


def macro_f1(y_true, y_pred) -> float:
    scores = []
    for label in PRIORITIES:
        tp = sum(t == p == label for t, p in zip(y_true, y_pred))
        fp = sum(p == label and t != label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def evaluate(repeats: int = 10, folds: int = 4) -> dict:
    from sklearn.model_selection import StratifiedKFold
    rows = load_training_rows()
    X, y = training_matrix(rows)
    results = {"model": {"acc": [], "f1": []}, "rules": {"acc": [], "f1": []}}
    confusion = Counter()
    high_missed = {"model": 0, "rules": 0}
    for seed in range(repeats):
        for train, test in StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed).split(X, y):
            model = new_model().fit([X[i] for i in train], [y[i] for i in train])
            truth = [y[i] for i in test]
            for name, pred in (("model", list(model.predict([X[i] for i in test]))), ("rules", [rule_priority(rows[i]) for i in test])):
                # Production applies the safety floor to the model too.
                if name == "model":
                    pred = ["High" if rows[i]["risk_score"] >= 5 else p for i, p in zip(test, pred)]
                    confusion.update(zip(truth, pred))
                results[name]["acc"].append(sum(t == p for t, p in zip(truth, pred)) / len(truth))
                results[name]["f1"].append(macro_f1(truth, pred))
                high_missed[name] += sum(t == "High" and p != "High" for t, p in zip(truth, pred))
    summary = {name: {k: sum(v) / len(v) for k, v in m.items()} for name, m in results.items()}
    return {"rows": len(y), "labels": Counter(y), "summary": summary, "confusion": confusion, "high_missed": high_missed, "repeats": repeats, "folds": folds}


def main():
    r = evaluate()
    print(f"Rows: {r['rows']}  labels: {dict(r['labels'])}")
    print(f"Stratified {r['folds']}-fold CV x {r['repeats']} repeats (same folds for both methods)\n")
    for name, label in (("model", "Random Forest + safety floor"), ("rules", "Keyword rules + safety floor")):
        s = r["summary"][name]
        print(f"{label:30} accuracy={s['acc']:.3f}  macro F1={s['f1']:.3f}  High reports missed={r['high_missed'][name]}")
    print("\nRandom Forest confusion matrix, summed over all folds (rows = expected):")
    print("          " + "".join(f"{p:>8}" for p in PRIORITIES))
    for t in PRIORITIES:
        print(f"{t:>8}  " + "".join(f"{r['confusion'][(t, p)]:>8}" for p in PRIORITIES))
    print("\nLIMITATION: 30 of 44 rows are synthetic and every High example is synthetic.")
    print("This shows the pipeline works. It is not validated real-world accuracy.")


if __name__ == "__main__":
    main()
