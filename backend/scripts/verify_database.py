"""Non-destructive check of the production database (Neon PostgreSQL).

Run from backend/ with the same DATABASE_URL the Render API uses:

    DATABASE_URL='postgresql://...' python scripts/verify_database.py

What it does:
  * Prints the database host (never the user name or password) and whether it is Neon.
  * Reads row counts and status counts from the INNOVEXA tables.
  * Checks that the connection is not read-only and that the app's user may
    INSERT and UPDATE the real tables.
  * Proves writes work by writing to a TEMPORARY table that PostgreSQL drops
    automatically. No INNOVEXA table is written to, altered or dropped.
"""
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

TABLES = ("issues", "staff_users", "issue_status_history")


def main() -> int:
    raw = os.getenv("DATABASE_URL")
    if not raw:
        print("DATABASE_URL is not set.")
        return 2
    url = make_url(raw)
    if not url.drivername.startswith("postgresql"):
        print(f"Refusing to run: expected PostgreSQL, got {url.drivername}.")
        return 2
    host = url.host or "(unknown host)"
    print(f"Host: {host}")
    print(f"Neon host: {'yes' if host.endswith('.neon.tech') else 'NO - check DATABASE_URL'}")
    print(f"Pooled endpoint: {'yes' if '-pooler' in host else 'no'}")
    print(f"sslmode: {url.query.get('sslmode', 'not set (Neon requires SSL)')}")

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        print("Server:", conn.execute(text("SELECT version()")).scalar().split(",")[0])
        print("Database:", conn.execute(text("SELECT current_database()")).scalar())
        print("Read-only connection:", conn.execute(text("SHOW transaction_read_only")).scalar())

        existing = set(conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )).scalars())
        for table in TABLES:
            if table not in existing:
                print(f"MISSING TABLE: {table}")
                continue
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            can_insert = conn.execute(text(f"SELECT has_table_privilege(current_user, '{table}', 'INSERT')")).scalar()
            can_update = conn.execute(text(f"SELECT has_table_privilege(current_user, '{table}', 'UPDATE')")).scalar()
            print(f"{table}: {count} rows, insert={can_insert}, update={can_update}")

        if "issues" in existing:
            for status, n in conn.execute(text("SELECT status, count(*) FROM issues GROUP BY status ORDER BY status")):
                print(f"  issues with status {status}: {n}")
            print("  highest issue id:", conn.execute(text("SELECT max(id) FROM issues")).scalar())
            columns = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'issues' ORDER BY ordinal_position"
            )).scalars().all()
            print("  issues columns:", ", ".join(columns))

        # Write test on a temporary table only. It disappears when the connection closes.
        conn.execute(text("CREATE TEMPORARY TABLE innovexa_write_check (id int, note text)"))
        conn.execute(text("INSERT INTO innovexa_write_check VALUES (1, 'ok')"))
        written = conn.execute(text("SELECT note FROM innovexa_write_check WHERE id = 1")).scalar()
        conn.rollback()
        print("Write test (temporary table):", "passed" if written == "ok" else "FAILED")
    engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
