## Tongmyong University dormitory repair dataset

The project dataset is [backend/data/tongmyong_sample_issues.csv](backend/data/tongmyong_sample_issues.csv). It is explicitly labelled for Tongmyong University and contains:
- 14 English paraphrases of publicly visible Tongmyong University dormitory repair-board posts (5 earlier examples and 9 additional posts reviewed on the official board).
- 30 fictional synthetic examples reserved for demonstration/evaluation only.

Official public source: https://www.tu.ac.kr/dormitory/sub06_04.do

The public posts are paraphrased, not copied verbatim. Personal names and room numbers are omitted. The category labels are manually assigned for this prototype and are not university-approved labels. The live Naive Bayes classifier now loads the 14 public-board paraphrases from this CSV together with 25 starter training examples. Synthetic rows are excluded from model training and are used only by the evaluation script. The public sample is small and should not be described as a representative dataset of all Tongmyong University dormitory issues.

# INNOVEXA — Smart Campus Facility and Issue Management System

A capstone prototype for reporting campus maintenance issues, suggesting a category, routing reports to a department, and tracking staff progress.

## Current workflow
1. A visitor submits an issue title, description, location, and optional image.
2. When a photo is attached and Hugging Face inference is configured, a pretrained CLIP zero-shot image classifier suggests a category. A custom Multinomial Naive Bayes text classifier also analyzes the title and description.
3. A keyword-based rule estimates priority; a category map suggests a department. A separate transparent keyword checklist assigns a 0–10 safety triage score, level and reasons.
4. Staff enter the configured shared staff key and update status.
5. Reports are stored in PostgreSQL and displayed on the dashboard. Staff can switch between open, resolved and all reports, and inspect status history.

## Technology
- Frontend: React + Vite
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Text classification: custom Python Multinomial Naive Bayes implementation
- Image classification: hosted zero-shot CLIP model through Hugging Face Inference Providers (requires a server-side token)

## Configure AI image recognition

Create a Hugging Face fine-grained access token with **Make calls to Inference Providers** permission. Set it as `HF_TOKEN` in the backend environment (never in frontend code or GitHub). The default model is `openai/clip-vit-large-patch14`; optionally override it with `HF_IMAGE_MODEL`. If the token is missing or the provider is unavailable, users can still submit reports and select a category manually.

The returned score is a relative model match score, not a calibrated probability or measured campus accuracy. The model suggests one of the six existing categories; it does not determine safety risk or diagnose the exact defect.

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

The evaluator reads the 30 synthetic rows and reports per-class precision, recall, F1, agreement and a confusion matrix. These are demonstration measurements on hand-written synthetic examples, not validated real-world accuracy. They must not be presented as accuracy on real Tongmyong University reports. A larger, consented and human-labelled campus dataset with an untouched test split is still needed for a defensible real-world performance claim.

## Dataset
See [backend/data/tongmyong_sample_issues.csv](backend/data/tongmyong_sample_issues.csv). The file distinguishes public-board paraphrases from synthetic examples through its `source_type` field.

## Deployment
See [DEPLOYMENT_SETUP.md](DEPLOYMENT_SETUP.md) for Render configuration and the staff key setup.

## Limitations and responsible use
- The classifier is a small demonstration model; confidence is not calibrated.
- The public-board training examples are paraphrased and manually labelled; they are not a large or representative campus dataset.
- Priority and safety triage are keyword rules, not AI risk prediction or validated safety assessments. The score can miss hazards and must never be used to decide that a situation is safe.
- Department assignment is a fixed mapping, not machine learning.
- Image recognition is a zero-shot category suggestion, not a model trained on campus-specific photos. Its match score is not calibrated accuracy; students can override the suggestion and staff must review reports. It requires the `HF_TOKEN` Render secret.
- A basic status history is recorded, but it identifies changes only as system or shared staff-key activity; it is not an individual audit trail. No student/staff accounts, institutional SSO, individual roles, or notifications are implemented.
- The public overview exposes only limited report metadata. Full descriptions, exact locations, images, risk details and status history require the shared staff key. The shared key is still a prototype credential, not individual accounts.
- For immediate danger, contact campus security or emergency services directly.
