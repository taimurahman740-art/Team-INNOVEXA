# INNOVEXA — Smart Campus Facility and Issue Management System

A capstone prototype for reporting campus maintenance issues, suggesting a category, routing reports to a department, and tracking staff progress.

## Current workflow
1. A visitor submits an issue title, description, location, and optional image.
2. A small custom Multinomial Naive Bayes text classifier suggests a category.
3. A keyword-based rule estimates priority; a category map suggests a department. A separate transparent keyword checklist assigns a 0–10 safety triage score, level and reasons.
4. Staff enter the configured shared staff key and update status.
5. Reports are stored in PostgreSQL and displayed on the dashboard.

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

The holdout examples are hand-written and very small. Their scores are only a code-check demonstration, not evidence of real campus performance. Collect representative, consented, labelled campus reports and use a genuinely separate test set before making accuracy claims.

## Deployment
See [DEPLOYMENT_SETUP.md](DEPLOYMENT_SETUP.md) for Render configuration and the staff key setup.

## Limitations and responsible use
- The classifier is a small demonstration model; confidence is not calibrated.
- Priority and safety triage are keyword rules, not AI risk prediction or validated safety assessments. The score can miss hazards and must never be used to decide that a situation is safe.
- Department assignment is a fixed mapping, not machine learning.
- Images are stored but are not analyzed by computer vision.
- A basic status history is recorded, but it identifies changes only as system or shared staff-key activity; it is not an individual audit trail. No student/staff accounts, institutional SSO, individual roles, or notifications are implemented.
- Reports and uploaded images are publicly visible in this prototype. Do not submit personal, confidential, or sensitive information.
- For immediate danger, contact campus security or emergency services directly.