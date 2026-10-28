# INNOVEXA — Start Here

This repository contains a React/Vite interface, a FastAPI API, PostgreSQL schema/seed files, and project documentation. The current API implements a basic issue workflow; it does **not** yet implement login/authentication, photo uploads, real staff accounts, notifications, or a trained machine-learning model. Category/priority suggestions are keyword rules and must be described as a prototype, not validated AI.

## Easiest start (Docker Desktop)

1. Install and open Docker Desktop.
2. Open a terminal in the repository root (the folder containing this file).
3. Run: `docker compose -f Campus-maintenance/docker-compose.yml up --build`
4. Open the frontend at `http://localhost:5173`.
5. API documentation and health check: `http://localhost:8000/docs` and `http://localhost:8000/health`.
6. Stop with Ctrl+C, then run `docker compose -f Campus-maintenance/docker-compose.yml down` to stop containers while preserving database data.

The PostgreSQL schema is initialized only when its data volume is first created. To discard the database and reinitialize it, run `docker compose -f Campus-maintenance/docker-compose.yml down -v` (this deletes local database data).

## Run without Docker

### Backend
From the repository root, install `backend/requirements.txt`, then start with `uvicorn app.main:app --app-dir backend --reload`. Without `DATABASE_URL`, the API uses a local SQLite database file.

### Frontend
From `frontend/`, run `npm install` and `npm run dev`. The browser API base defaults to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` before starting if your API runs elsewhere.

## Current limitations to address next

- The API's prototype `issues` table is separate from the richer relational schema in `database/schema.sql`; integration/migration is still needed.
- No authentication or role-based access control is implemented. Do not expose this prototype to the public internet or use it for real student personal data.
- The database seed file contains placeholder password hashes; there is no login flow using them.
- The frontend displays sample demo records if the backend is unavailable; demo records are not saved.
- The keyword classifier is a baseline only. A trained model needs a labeled dataset, evaluation, and human review for safety-critical reports.

## Useful checks

- `GET /health` should return `{"status":"ok"}`.
- `GET /issues` should return a JSON list.
- Submit a report from the UI and refresh; the saved record should remain visible.
