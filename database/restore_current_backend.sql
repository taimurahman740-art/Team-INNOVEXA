-- INNOVEXA current-backend recovery schema
-- Matches backend/app/models.py on the main branch.
-- The FastAPI startup also runs Base.metadata.create_all(), which creates
-- these tables automatically when DATABASE_URL points to a fresh database.
-- This script is provided for manual recovery/inspection if needed.
-- It creates STRUCTURE only; it does not restore old report records.

BEGIN;

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'Other',
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    status VARCHAR(30) NOT NULL DEFAULT 'Submitted',
    location VARCHAR(180) NOT NULL,
    department VARCHAR(80),
    image_data TEXT,
    classification_confidence FLOAT,
    risk_score INTEGER NOT NULL DEFAULT 0,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Low',
    risk_reasons JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS issue_status_history (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    changed_by VARCHAR(80) NOT NULL DEFAULT 'staff-key'
);

CREATE INDEX IF NOT EXISTS ix_issues_id ON issues (id);
CREATE INDEX IF NOT EXISTS ix_issue_status_history_id ON issue_status_history (id);
CREATE INDEX IF NOT EXISTS ix_issue_status_history_issue_id ON issue_status_history (issue_id);

COMMIT;
