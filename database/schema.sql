-- =====================================================================
-- INNOVEXA - Campus Maintenance System : PostgreSQL schema (v1)
-- Run:  psql -U postgres -d "Campus-maintenance" -f schema.sql
-- =====================================================================

BEGIN;

-- ---------- 1. USERS & ROLES ----------------------------------------
CREATE TABLE departments (
    department_id  SERIAL PRIMARY KEY,
    name           VARCHAR(60)  NOT NULL UNIQUE,
    description    TEXT
);

CREATE TABLE users (
    user_id        SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    student_id     VARCHAR(20)  UNIQUE,              -- NULL for staff/admin
    email          VARCHAR(150) NOT NULL UNIQUE,
    role           VARCHAR(10)  NOT NULL
                   CHECK (role IN ('student', 'staff', 'admin')),
    department_id  INTEGER REFERENCES departments(department_id),  -- staff only
    password_hash  VARCHAR(255) NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT staff_needs_department
        CHECK (role <> 'staff' OR department_id IS NOT NULL)
);

-- ---------- 2. LOCATIONS --------------------------------------------
CREATE TABLE buildings (
    building_id    SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE locations (
    location_id    SERIAL PRIMARY KEY,
    building_id    INTEGER NOT NULL REFERENCES buildings(building_id),
    floor          SMALLINT NOT NULL,
    room           VARCHAR(20) NOT NULL,
    UNIQUE (building_id, floor, room)
);

-- ---------- 3. REPORTS ----------------------------------------------
CREATE TABLE reports (
    report_id      SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    location_id    INTEGER NOT NULL REFERENCES locations(location_id),
    description    TEXT    NOT NULL,
    image_url      VARCHAR(255),                      -- optional photo
    category       VARCHAR(40),                       -- filled by AI (final category)
    status         VARCHAR(15) NOT NULL DEFAULT 'submitted'
                   CHECK (status IN ('submitted','accepted','in_progress',
                                     'resolved','escalated','rejected')),
    duplicate_of   INTEGER REFERENCES reports(report_id),  -- set if flagged duplicate
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------- 4. AI ANALYSIS (one row per report) ---------------------
CREATE TABLE ai_analysis (
    analysis_id      SERIAL PRIMARY KEY,
    report_id        INTEGER NOT NULL UNIQUE REFERENCES reports(report_id) ON DELETE CASCADE,
    category         VARCHAR(40),
    confidence       NUMERIC(5,2) CHECK (confidence BETWEEN 0 AND 100),   -- %
    hazard           VARCHAR(60),                     -- e.g. 'Water Leakage'
    severity_score   NUMERIC(3,1) CHECK (severity_score BETWEEN 0 AND 10),
    duplicate_score  NUMERIC(4,3) CHECK (duplicate_score BETWEEN 0 AND 1),
    priority         VARCHAR(10)
                     CHECK (priority IN ('low','medium','high','critical')),
    priority_source  VARCHAR(10) NOT NULL DEFAULT 'rules'
                     CHECK (priority_source IN ('rules','ml')),
    department_id    INTEGER REFERENCES departments(department_id),
    analyzed_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------- 5. MAINTENANCE TASKS ------------------------------------
CREATE TABLE maintenance_tasks (
    task_id        SERIAL PRIMARY KEY,
    report_id      INTEGER NOT NULL UNIQUE REFERENCES reports(report_id) ON DELETE CASCADE,
    department_id  INTEGER NOT NULL REFERENCES departments(department_id),
    staff_id       INTEGER REFERENCES users(user_id),   -- NULL until accepted
    priority       VARCHAR(10) NOT NULL
                   CHECK (priority IN ('low','medium','high','critical')),
    status         VARCHAR(15) NOT NULL DEFAULT 'assigned'
                   CHECK (status IN ('assigned','accepted','in_progress',
                                     'resolved','escalated')),
    assigned_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at     TIMESTAMP,
    completed_at   TIMESTAMP,
    response_due   TIMESTAMP,                           -- escalation deadline
    CHECK (completed_at IS NULL OR completed_at >= assigned_at)
);

-- ---------- 6. ESCALATIONS ------------------------------------------
CREATE TABLE escalations (
    escalation_id  SERIAL PRIMARY KEY,
    task_id        INTEGER NOT NULL REFERENCES maintenance_tasks(task_id) ON DELETE CASCADE,
    level          SMALLINT NOT NULL CHECK (level IN (1, 2)),   -- 1 reminder, 2 admin
    reason         TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------- 7. HISTORY, NOTIFICATIONS, FEEDBACK ---------------------
CREATE TABLE status_history (
    history_id     SERIAL PRIMARY KEY,
    report_id      INTEGER NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    status         VARCHAR(15) NOT NULL,
    changed_by     INTEGER REFERENCES users(user_id),   -- NULL = system/AI
    timestamp      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    report_id      INTEGER REFERENCES reports(report_id) ON DELETE CASCADE,
    message        TEXT NOT NULL,
    is_read        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE feedback (
    feedback_id    SERIAL PRIMARY KEY,
    report_id      INTEGER NOT NULL UNIQUE REFERENCES reports(report_id) ON DELETE CASCADE,
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    rating         SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment        TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------- 8. INDEXES ----------------------------------------------
CREATE INDEX idx_reports_user      ON reports(user_id);
CREATE INDEX idx_reports_location  ON reports(location_id);
CREATE INDEX idx_reports_status    ON reports(status);
CREATE INDEX idx_reports_category  ON reports(category);
CREATE INDEX idx_reports_created   ON reports(created_at);
CREATE INDEX idx_tasks_department  ON maintenance_tasks(department_id, status);
CREATE INDEX idx_tasks_staff       ON maintenance_tasks(staff_id);
CREATE INDEX idx_tasks_due         ON maintenance_tasks(response_due) WHERE status IN ('assigned','escalated');
CREATE INDEX idx_history_report    ON status_history(report_id);
CREATE INDEX idx_notif_user_unread ON notifications(user_id) WHERE is_read = FALSE;

-- ---------- 9. ANALYTICS VIEWS (for the admin dashboard) ------------
CREATE VIEW v_dashboard_counts AS
SELECT
    COUNT(*) FILTER (WHERE r.status NOT IN ('resolved','rejected'))            AS active_issues,
    COUNT(*) FILTER (WHERE a.priority = 'critical'
                       AND r.status NOT IN ('resolved','rejected'))            AS critical_issues,
    COUNT(*) FILTER (WHERE r.status = 'resolved')                             AS resolved_issues,
    COUNT(*) FILTER (WHERE r.status = 'escalated')                            AS escalated_issues
FROM reports r
LEFT JOIN ai_analysis a ON a.report_id = r.report_id;

CREATE VIEW v_issues_by_category AS
SELECT COALESCE(category, 'Other') AS category, COUNT(*) AS total
FROM reports
GROUP BY COALESCE(category, 'Other')
ORDER BY total DESC;

CREATE VIEW v_department_workload AS
SELECT d.name AS department,
       COUNT(t.task_id) FILTER (WHERE t.status <> 'resolved') AS active_tasks
FROM departments d
LEFT JOIN maintenance_tasks t ON t.department_id = d.department_id
GROUP BY d.name
ORDER BY active_tasks DESC;

CREATE VIEW v_resolution_times AS
SELECT d.name AS department,
       ROUND(AVG(EXTRACT(EPOCH FROM (t.started_at   - t.assigned_at)) / 3600)::numeric, 1) AS avg_hours_to_start,
       ROUND(AVG(EXTRACT(EPOCH FROM (t.completed_at - t.assigned_at)) / 3600)::numeric, 1) AS avg_hours_to_resolve
FROM maintenance_tasks t
JOIN departments d ON d.department_id = t.department_id
WHERE t.completed_at IS NOT NULL
GROUP BY d.name;

-- Recurring problem = same location + category reported 3+ times in 90 days
CREATE VIEW v_recurring_problems AS
SELECT b.name AS building, l.floor, l.room, r.category,
       COUNT(*) AS times_reported,
       MAX(r.created_at) AS last_reported
FROM reports r
JOIN locations l ON l.location_id = r.location_id
JOIN buildings b ON b.building_id = l.building_id
WHERE r.created_at >= NOW() - INTERVAL '90 days'
  AND r.category IS NOT NULL
GROUP BY b.name, l.floor, l.room, r.category
HAVING COUNT(*) >= 3
ORDER BY times_reported DESC;

COMMIT;
