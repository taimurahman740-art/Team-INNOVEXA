# INNOVEXA database recovery

This repository contains the backend code and the database structure needed to recreate a fresh database. It does not contain a backup of live report records.

## Current backend behavior

The FastAPI application imports the SQLAlchemy models and runs:

`Base.metadata.create_all(bind=engine)`

during application startup (see `backend/app/main.py`). With a valid `DATABASE_URL` pointing to an empty PostgreSQL database, SQLAlchemy creates the current model tables automatically:

- `issues`
- `issue_status_history`

The backend also applies additive columns to an existing `issues` table at startup.

## Recovery after creating a new Render PostgreSQL database

1. Create a new PostgreSQL database in Render.
2. In the Render dashboard, open the `innovexa-api` web service and set its `DATABASE_URL` environment variable to the new database's **internal** connection URL (keep credentials private).
3. Save the environment variable change and allow the backend to redeploy/restart.
4. Check `https://innovexa-api-lfjx.onrender.com/health` (or the current service URL). A successful response should report `{"status":"ok","database":"connected"}`.
5. Open the API docs at `/docs` and submit a test issue. Confirm it appears in the public issue list.
6. Configure the staff key in the backend environment if staff operations are to be tested.

## Manual SQL reference

`restore_current_backend.sql` documents the current table structure. Normally it is not necessary to run it manually because application startup creates the tables. Use it as a reference if manual database setup is required.

## Important limitations

- This procedure recreates the schema, not the old database contents.
- Existing reports, images stored in report rows, and status history are not recovered without a separate data backup.
- The current backend models do not define student user-account tables or registration endpoints. Do not expect user accounts to be recreated from this schema.
- Keep the old Render database until you are ready to replace it. Do not delete it before the new database has been created and tested.
