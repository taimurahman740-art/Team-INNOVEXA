## Sample Tongmyong-style issue dataset

The starter CSV is at [backend/data/tongmyong_sample_issues.csv](backend/data/tongmyong_sample_issues.csv). It contains five paraphrased examples inspired by issue types visible on the public Tongmyong University dormitory repair board, plus 30 fictional synthetic examples.

Public source: https://tu.ac.kr/dormitory/sub06_04.do

The public-board examples are paraphrases, not verified exports or verbatim records. Synthetic rows are fictional and must not be presented as real university incidents. All category, department, priority and risk labels are illustrative, not university-approved. This CSV is for demonstration only and is not currently used to train the live classifier. Do not use it to claim model accuracy or real-world safety performance.

# INNOVEXA — Smart Campus Facility and Issue Management System

A capstone prototype for reporting campus maintenance issues, suggesting a category, routing reports to a department, and tracking staff progress.

## Current workflow
1. A visitor submits an issue title, description, location, and optional image.
2. A small custom Multinomial Naive Bayes text classifier suggests a category.
3. A keyword-based rule estimates priority; a category map suggests a department. A separate transparent keyword checklist assigns a 0–10 safety triage score, level and reasons.
4. Staff enter the configured shared staff key and update status.
5. Reports are stored in PostgreSQL and displayed on the dashboard. Staff can switch between open, resolved and all reports, and inspect status history.

## Technology
- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Classification: custom Python Multinomial Naive Bayes implementation

## Run locally
### Backend
From the backend directory, create and activate a virtual environment, install dependencies, set DATABASE_URL and STAFF_API_KEY, then run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
From the frontend directory, install packages and start Vite:

```bash
npm install
npm run dev
```

Configure the frontend API base URL using the environment variable expected by frontend/src/api.js.

## Evaluate and test the classifier
From the backend directory:

```bash
python -m app.evaluate_classifier
python -m unittest discover -s tests
```

The evaluator reads the synthetic rows in `data/tongmyong_sample_issues.csv` and reports per-class precision, recall, F1, agreement and a confusion matrix. These are measurements on hand-written synthetic examples, not validated model accuracy or evidence of real campus performance. Collect representative, consented, human-labelled campus reports and reserve an untouched test set before making accuracy claims.

## Sample dataset
See [backend/data/tongmyong_sample_issues.csv](backend/data/tongmyong_sample_issues.csv). It includes paraphrased public-board issue types and clearly labelled fictional examples. The CSV is for evaluation/demo only and is not automatically loaded into the live model.

## Deployment
See [DEPLOYMENT_SETUP.md](DEPLOYMENT_SETUP.md) for Render configuration and the staff key setup.

## Limitations and responsible use
- The classifier is a small demonstration model; confidence is not calibrated.
- Priority and safety triage are keyword rules, not AI risk prediction or validated safety assessments. The score can miss hazards and must never be used to decide that a situation is safe.
- Department assignment is a fixed mapping, not machine learning.
- Images are stored but are not analyzed by computer vision.
- A basic status history is recorded, but it identifies changes only as system or shared staff-key activity; it is not an individual audit trail. No student/staff accounts, institutional SSO, individual roles, or notifications are implemented.
- The public overview exposes only limited report metadata. Full descriptions, exact locations, images, risk details and status history require the shared staff key. The shared key is still a prototype credential, not individual accounts.
- For immediate danger, contact campus security or emergency services directly.