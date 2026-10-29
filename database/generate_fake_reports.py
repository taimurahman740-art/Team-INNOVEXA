"""
generate_fake_reports.py  -  fills the Campus-maintenance database with
realistic fake reports so the team can test the app and analytics.

Usage:
    pip install psycopg2-binary
    python generate_fake_reports.py            # adds 400 reports
    python generate_fake_reports.py 600        # adds 600 reports
    python generate_fake_reports.py --reset    # deletes old fake data first

Edit DB below if your password/port is different.
Run AFTER schema.sql and seed.sql.
"""
import random
import sys
from datetime import datetime, timedelta

import psycopg2

DB = dict(host="localhost", port=5432, dbname="Campus-maintenance",
          user="postgres", password="your_password_here")

random.seed(42)  # same data every run (remove for random data)

# category -> (department name, hazard or None, severity range, sample descriptions)
ISSUES = {
    "Electrical": ("Electrical", None, (3, 6), [
        "The ceiling light in the classroom is not working.",
        "Power outlet near the window has no electricity.",
        "Lights keep flickering during class.",
        "Projector power socket is dead."]),
    "Electrical-Hazard": ("Electrical", "Exposed Wiring", (7, 10), [
        "There are exposed wires hanging from the wall near the door.",
        "Wires are visible behind a broken outlet cover, sparks seen.",
        "Burning smell and loose cables near the switch board."]),
    "HVAC": ("HVAC", None, (2, 5), [
        "The air conditioner is not cooling at all.",
        "AC is making a loud noise and blowing warm air.",
        "Room is too hot, the AC remote does not respond."]),
    "HVAC-Hazard": ("HVAC", "Water Leakage", (6, 9), [
        "Water is leaking from the AC onto the floor.",
        "AC is dripping water onto the desks and chairs."]),
    "Plumbing": ("Plumbing", None, (3, 6), [
        "The sink tap is broken and keeps running.",
        "Toilet is blocked and not flushing.",
        "Water fountain has no water pressure."]),
    "Plumbing-Hazard": ("Plumbing", "Water Pooling", (6, 9), [
        "Water is pooling on the corridor floor, it is slippery.",
        "Pipe is leaking and the floor is flooded."]),
    "IT": ("IT", None, (1, 4), [
        "WiFi is not working in this room.",
        "The projector does not turn on.",
        "Computer in the lab will not boot.",
        "Network cable port is dead at the front desk."]),
    "Other": ("Other", None, (1, 4), [
        "The classroom door does not lock properly.",
        "Several chairs are broken.",
        "Whiteboard is cracked and unusable."]),
    "Other-Hazard": ("Other", "Broken Glass", (7, 9), [
        "The window glass is broken and sharp pieces are on the floor.",
        "Cracked glass panel in the door might fall."]),
}
# how common each issue is (weights)
WEIGHTS = {"Electrical": 18, "Electrical-Hazard": 5, "HVAC": 16, "HVAC-Hazard": 5,
           "Plumbing": 10, "Plumbing-Hazard": 3, "IT": 14, "Other": 8, "Other-Hazard": 2}

# Hotspots: (building, floor, room, issue) -> extra reports, makes recurring problems
HOTSPOTS = [("Engineering Building", 3, "301", "HVAC-Hazard", 6),
            ("Building B", 2, "204", "Electrical", 5),
            ("Building A", 3, "301", "HVAC", 4),
            ("Library", 1, "Reading Hall", "Plumbing-Hazard", 4)]

def priority_from(severity, hazard):
    """Simple rule-based priority (same idea your backend can use)."""
    if severity >= 8:
        return "critical"
    if severity >= 6 or hazard:
        return "high"
    if severity >= 3:
        return "medium"
    return "low"

def main():
    n = 400
    reset = "--reset" in sys.argv
    for a in sys.argv[1:]:
        if a.isdigit():
            n = int(a)

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    if reset:
        cur.execute("""TRUNCATE feedback, notifications, status_history, escalations,
                       maintenance_tasks, ai_analysis, reports RESTART IDENTITY CASCADE""")
        print("Old report data deleted.")

    # add more rooms (4 floors x 5 rooms per building) so recurring problems stand out
    cur.execute("SELECT building_id FROM buildings")
    for (bid,) in cur.fetchall():
        for floor in range(1, 5):
            for k in range(1, 6):
                cur.execute("""INSERT INTO locations (building_id, floor, room) VALUES (%s,%s,%s)
                               ON CONFLICT (building_id, floor, room) DO NOTHING""",
                            (bid, floor, f"{floor}0{k}"))

    cur.execute("SELECT department_id, name FROM departments")
    dept = {name: did for did, name in cur.fetchall()}
    cur.execute("SELECT user_id FROM users WHERE role='student'")
    students = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT user_id, department_id FROM users WHERE role='staff'")
    staff = {d: u for u, d in cur.fetchall()}
    cur.execute("""SELECT l.location_id, b.name, l.floor, l.room
                   FROM locations l JOIN buildings b USING (building_id)""")
    locs = cur.fetchall()
    cur.execute("SELECT user_id FROM users WHERE role='admin' LIMIT 1")
    admin = cur.fetchone()[0]

    # build the list of reports to create: random + hotspot extras
    plan = []
    keys, w = list(WEIGHTS), list(WEIGHTS.values())
    for _ in range(n):
        plan.append((random.choice(locs), random.choices(keys, w)[0]))
    for b, f, r, issue, count in HOTSPOTS:
        loc = next((l for l in locs if (l[1], l[2], l[3]) == (b, f, r)), None)
        if loc:
            plan += [(loc, issue)] * count

    now = datetime.now()
    created = 0
    for loc, issue in plan:
        dname, hazard, (smin, smax), texts = ISSUES[issue]
        category = issue.split("-")[0]
        severity = round(random.uniform(smin, smax), 1)
        priority = priority_from(severity, hazard)
        # recent reports more likely; spread over the last 120 days
        created_at = now - timedelta(days=random.randint(0, 120),
                                     hours=random.randint(0, 23),
                                     minutes=random.randint(0, 59))
        age_days = (now - created_at).days
        # status depends on age: old reports are mostly resolved
        if age_days > 14:
            status = random.choices(["resolved", "in_progress", "escalated"], [90, 5, 5])[0]
        elif age_days > 3:
            status = random.choices(["resolved", "in_progress", "accepted", "escalated"], [50, 25, 15, 10])[0]
        else:
            status = random.choices(["submitted", "accepted", "in_progress", "resolved"], [25, 30, 30, 15])[0]

        student = random.choice(students)
        cur.execute("""INSERT INTO reports (user_id, location_id, description, image_url, category,
                       status, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       RETURNING report_id""",
                    (student, loc[0], random.choice(texts),
                     f"uploads/fake_{random.randint(1000, 9999)}.jpg" if random.random() < 0.7 else None,
                     category, status, created_at, created_at))
        rid = cur.fetchone()[0]

        cur.execute("""INSERT INTO ai_analysis (report_id, category, confidence, hazard, severity_score,
                       duplicate_score, priority, priority_source, department_id, analyzed_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'rules',%s,%s)""",
                    (rid, category, round(random.uniform(78, 99), 2), hazard, severity,
                     round(random.uniform(0, 0.4), 3), priority, dept[dname],
                     created_at + timedelta(seconds=5)))

        cur.execute("""INSERT INTO status_history (report_id, status, changed_by, timestamp)
                       VALUES (%s,'submitted',%s,%s)""", (rid, student, created_at))

        # maintenance task
        task_status = "assigned" if status == "submitted" else status
        assigned = created_at + timedelta(seconds=10)
        due_hours = {"critical": 1, "high": 4, "medium": 24, "low": 72}[priority]
        started = completed = None
        staff_id = None
        if task_status != "assigned":
            staff_id = staff.get(dept[dname])
            started = assigned + timedelta(hours=random.randint(0, due_hours * 2) + 1)
        if task_status == "resolved":
            completed = started + timedelta(hours=random.randint(1, 72))
        cur.execute("""INSERT INTO maintenance_tasks (report_id, department_id, staff_id, priority, status,
                       assigned_at, started_at, completed_at, response_due)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING task_id""",
                    (rid, dept[dname], staff_id, priority, task_status, assigned, started, completed,
                     assigned + timedelta(hours=due_hours)))
        tid = cur.fetchone()[0]

        # status history steps
        steps = {"accepted": ["accepted"], "in_progress": ["accepted", "in_progress"],
                 "resolved": ["accepted", "in_progress", "resolved"],
                 "escalated": ["escalated"]}.get(status, [])
        t = assigned
        for s in steps:
            t = t + timedelta(hours=random.randint(1, 20))
            cur.execute("INSERT INTO status_history (report_id, status, changed_by, timestamp) VALUES (%s,%s,%s,%s)",
                        (rid, s, staff_id if s != "escalated" else None, t))

        if status == "escalated":
            cur.execute("INSERT INTO escalations (task_id, level, reason, created_at) VALUES (%s,1,%s,%s)",
                        (tid, "No response within target time", assigned + timedelta(hours=due_hours)))
            if random.random() < 0.6:
                cur.execute("INSERT INTO escalations (task_id, level, reason, created_at) VALUES (%s,2,%s,%s)",
                            (tid, "Administrator notified", assigned + timedelta(hours=due_hours * 2)))

        cur.execute("INSERT INTO notifications (user_id, report_id, message, is_read, created_at) VALUES (%s,%s,%s,%s,%s)",
                    (student, rid, f"Your report is now: {status.replace('_', ' ')}.",
                     random.random() < 0.7, t))

        if status == "resolved" and random.random() < 0.5:
            cur.execute("""INSERT INTO feedback (report_id, user_id, rating, comment, created_at)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (rid, student, random.choices([1, 2, 3, 4, 5], [3, 5, 15, 35, 42])[0],
                         random.choice(["Fixed quickly.", "Good work.", "Took a long time.", None]),
                         completed))
        created += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Done. {created} fake reports created.")

if __name__ == "__main__":
    main()
