
import sqlite3
from pathlib import Path

# Project root: Team-INNOVEXA/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATABASE_DIR / "reports.db"


def get_connection():
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create the reports table if it does not already exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter TEXT NOT NULL,
                facility TEXT NOT NULL,
                location TEXT NOT NULL,
                priority TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created TEXT NOT NULL,
                image_path TEXT
            )
            """
        )


def save_report(report):
    """Save one report and return its database ID."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports (
                reporter, facility, location, priority,
                description, status, created, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report["Reporter"],
                report["Facility"],
                report["Location"],
                report["Priority"],
                report["Description"],
                report.get("Status", "Pending"),
                report["Created"],
                report.get("Image"),
            ),
        )
        return cursor.lastrowid


def get_reports():
    """Load all reports, newest first."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM reports ORDER BY id DESC"
        ).fetchall()

    reports = []
    for row in rows:
        reports.append({
            "ID": row["id"],
            "Reporter": row["reporter"],
            "Facility": row["facility"],
            "Location": row["location"],
            "Priority": row["priority"],
            "Description": row["description"],
            "Status": row["status"],
            "Created": row["created"],
            "Image": row["image_path"],
        })

    return reports


def update_report_status(report_id, status):
    """Update a report's status."""
    with get_connection() as connection:
        connection.execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (status, report_id),
        )
initialize_database()