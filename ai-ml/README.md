# AI/ML
Issue classification, duplicate-ticket detection, hazard assessment, severity scoring, and ML priority prediction.

All models live in `backend/app/`. Every AI result is a suggestion that staff review.

| Feature | Status | Code |
|---|---|---|
| Text classification (Naive Bayes) | In use | `services.py` |
| Multimodal image + text classification, photo-only reports | In use | `image_recognition.py`, `services.choose_category` |
| Hazard detection and severity (zero-shot CLIP) | In use, confirmed by staff | `image_recognition.py` |
| Priority prediction (Random Forest) | In use as a baseline | `priority_model.py` |
| Duplicate-ticket detection | In use, flags for staff review | `duplicates.py` |

## Priority prediction (feature 5)

**Model:** scikit-learn `RandomForestClassifier` with 200 trees, maximum depth 5, minimum leaf size 2, balanced class weights and `random_state=42`. It is trained when the API starts.

**Training data:** the 44 labelled rows in `backend/data/tongmyong_sample_issues.csv`: 14 paraphrased public Tongmyong board posts and 30 synthetic rows. Labels: 25 Medium, 11 High, 8 Low. Every High example is synthetic.

**Features**
- Category (one-hot, 8 categories).
- Safety risk score from 0 to 10, from keyword triage plus any photo hazard.
- Affected-area traffic from 0 to 2, derived from location words. Entrances, corridors, cafeterias, stairs and the library are high; classrooms, labs and restrooms are medium; dorm rooms and offices are low.
- Service-disruption cue in the text, such as "not working" or "no water".
- *Not used yet:* historical resolution time. The sample rows have no resolution history. It can be added from Neon status history once enough reports are resolved.

**Safety floor:** a report with a risk score of 5 or more is always High. A priority chosen by the reporter is kept unless the safety floor applies. The stored `ai_analysis.priority` records the model prediction, the keyword-rule priority, the final priority and the factors used.

**Evaluation** (`python -m app.evaluate_priority`): stratified 4-fold cross-validation repeated 10 times. The model and the keyword rules are scored on exactly the same held-out folds, and both include the safety floor.

| Method | Accuracy | Macro F1 | High reports missed (of 110 held out) |
|---|---|---|---|
| Random Forest + safety floor | 0.670 | 0.633 | 40 |
| Keyword rules + safety floor | 0.636 | 0.603 | 60 |

The model's most common error is predicting Low for a Medium report.

**Limitation:** these figures come from a tiny, mostly synthetic dataset written by the team. They show that the pipeline works and that the model is at least as good as the rules on this data. They are **not** real-world accuracy. Before claiming performance, collect human-labelled Neon reports, keep a held-out test set, retrain, and re-run the evaluation.

**Fallback:** if scikit-learn is missing or training fails, the API uses the keyword rules and records `method: "rules"`.

## Duplicate-ticket detection (feature 7)

**When:** every new report is compared with open reports (Submitted or In Progress) in the same department or the same building, using the 50 most recent. The check never blocks, rejects, merges or closes a report. Matches are stored in `ai_analysis.duplicates`, and staff confirm or dismiss them with `PATCH /issues/{id}/duplicate-review`.

**Text similarity:** TF-IDF vectors of title + description (unigrams and bigrams, English stop words removed, sublinear term frequency), compared with cosine similarity. The vocabulary is fitted on the sample dataset plus the reports being compared.

**Image similarity:** a 320-value feature vector per photo, compared with cosine similarity. It joins a mean-centred 16×16 greyscale layout with a 4×4×4 RGB colour histogram. It recognises the same scene photographed again. It is **not** a learned embedding, so two different photos of the same *kind* of problem will not match.

**Decision:** a report is flagged when its text similarity is at least 0.25, or its photo similarity is at least 0.60, or the combined score (0.6 × text + 0.4 × photo) is at least 0.35 in the same building. At most three matches are kept. The thresholds can be changed with `DUPLICATE_TEXT_THRESHOLD`, `DUPLICATE_IMAGE_THRESHOLD` and `DUPLICATE_COMBINED_THRESHOLD`.

**Calibration** (`tests/test_duplicates.py`, hand-made, small):

| Pair type | Score |
|---|---|
| 4 reworded duplicates (text) | 0.27–0.52 |
| 4 different problems, same department (text) | 0.00–0.04 |
| Same scene photographed again: shifted, brighter, cropped | 0.71 |
| Different scene | 0.17 |

**Limitation:** these checks are hand-made examples, not real campus data. Check the thresholds on real reports and photos, and count false flags from the staff reviews (`review.decision`), before claiming performance.
