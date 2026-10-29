-- INNOVEXA API compatibility schema.
-- The current FastAPI prototype uses these tables. The normalized academic
-- schema remains available in schema.sql; these tables are not synchronized
-- with reports/maintenance_tasks and are a documented transitional layer.
CREATE TABLE IF NOT EXISTS app_users (
 id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
 email VARCHAR(180) NOT NULL UNIQUE, password_hash VARCHAR(300) NOT NULL,
 role VARCHAR(20) NOT NULL DEFAULT 'student' CHECK (role IN ('student','staff','admin')),
 department VARCHAR(80), active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS issues (
 id SERIAL PRIMARY KEY, title VARCHAR(120) NOT NULL, description TEXT NOT NULL,
 category VARCHAR(40) NOT NULL DEFAULT 'Other', priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
 status VARCHAR(30) NOT NULL DEFAULT 'Submitted', location VARCHAR(180) NOT NULL,
 department VARCHAR(80), image_url VARCHAR(300),
 created_by INTEGER REFERENCES app_users(id), assigned_to INTEGER REFERENCES app_users(id),
 resolution_note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS issue_updates (
 id SERIAL PRIMARY KEY, issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
 user_id INTEGER REFERENCES app_users(id), status VARCHAR(40) NOT NULL, note TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS issue_feedback (
 id SERIAL PRIMARY KEY, issue_id INTEGER NOT NULL UNIQUE REFERENCES issues(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES app_users(id), rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
 comment TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_issues_created_by ON issues(created_by);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issue_updates_issue ON issue_updates(issue_id);
