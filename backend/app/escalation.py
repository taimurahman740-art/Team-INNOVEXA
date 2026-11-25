"""Automatic escalation and response-time management (feature 2).

Each priority has two configurable targets (table response_targets):
  * start_within_minutes:   a report must leave "Submitted" within this time
  * resolve_within_minutes: a report must be Resolved/Closed within this time

A report past either target is *overdue*. For priorities with auto_escalate on
(High by default), an overdue report also gets an escalation record, which
administrators see as an alert until someone acknowledges it. Escalation never
changes a report's status.

Render's free tier has no background scheduler, so the check runs when staff
load their task lists (at most once a minute) and when an administrator presses
"Check now". An external cron can call POST /issues/escalations/check as well.
"""
from datetime import datetime, timedelta, timezone

OPEN_STATUSES = ("Submitted", "In Progress")
PRIORITIES = ("High", "Medium", "Low")
DEFAULT_TARGETS = {
    "High": {"start_within_minutes": 4 * 60, "resolve_within_minutes": 24 * 60, "auto_escalate": True},
    "Medium": {"start_within_minutes": 24 * 60, "resolve_within_minutes": 72 * 60, "auto_escalate": False},
    "Low": {"start_within_minutes": 72 * 60, "resolve_within_minutes": 7 * 24 * 60, "auto_escalate": False},
}
CHECK_INTERVAL = timedelta(seconds=60)
_last_check: datetime | None = None


def utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def human_minutes(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        days = minutes // (24 * 60)
        return f"{days} day" + ("s" if days != 1 else "")
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


def breaches(issue: dict, target: dict, now: datetime) -> list[dict]:
    """Missed targets for one report: [{kind, due_at, overdue_minutes, target_minutes}]."""
    if issue["status"] not in OPEN_STATUSES:
        return []
    created = utc(issue["created_at"])
    found = []
    start_due = created + timedelta(minutes=target["start_within_minutes"])
    if issue["status"] == "Submitted" and now > start_due:
        found.append({"kind": "start", "due_at": start_due, "target_minutes": target["start_within_minutes"],
                      "overdue_minutes": int((now - start_due).total_seconds() // 60)})
    resolve_due = created + timedelta(minutes=target["resolve_within_minutes"])
    if now > resolve_due:
        found.append({"kind": "resolve", "due_at": resolve_due, "target_minutes": target["resolve_within_minutes"],
                      "overdue_minutes": int((now - resolve_due).total_seconds() // 60)})
    return found


def plan_escalations(issues: list[dict], targets: dict, already: set, now: datetime) -> list[dict]:
    """New escalation records to create. One per (report, kind); never repeated."""
    new = []
    for issue in issues:
        target = targets.get(issue["priority"])
        if not target or not target["auto_escalate"]:
            continue
        for b in breaches(issue, target, now):
            if (issue["id"], b["kind"]) in already:
                continue
            action = "not started" if b["kind"] == "start" else "not resolved"
            new.append({
                "issue_id": issue["id"], "kind": b["kind"], "priority": issue["priority"], "target_minutes": b["target_minutes"],
                "reason": f"{issue['priority']} priority report {action} within {human_minutes(b['target_minutes'])}.",
            })
    return new


# --- database helpers -----------------------------------------------------------------

def ensure_default_targets(db) -> None:
    """Insert the default targets for any priority that has none. Never overwrites."""
    from .models import ResponseTarget
    existing = {t.priority for t in db.query(ResponseTarget).all()}
    for priority, values in DEFAULT_TARGETS.items():
        if priority not in existing:
            db.add(ResponseTarget(priority=priority, updated_by="system default", **values))
    db.commit()


def load_targets(db) -> dict:
    from .models import ResponseTarget
    rows = db.query(ResponseTarget).all()
    targets = {p: dict(v) for p, v in DEFAULT_TARGETS.items()}
    for r in rows:
        targets[r.priority] = {"start_within_minutes": r.start_within_minutes, "resolve_within_minutes": r.resolve_within_minutes, "auto_escalate": r.auto_escalate}
    return targets


def run_check(db, force: bool = False, now: datetime | None = None) -> int:
    """Create escalations for overdue reports. Throttled unless force=True. Returns how many were created."""
    global _last_check
    from .models import Escalation, Issue
    now = now or datetime.now(timezone.utc)
    if not force and _last_check and now - _last_check < CHECK_INTERVAL:
        return 0
    _last_check = now
    open_issues = db.query(Issue).filter(Issue.status.in_(OPEN_STATUSES)).all()
    rows = [{"id": i.id, "priority": i.priority, "status": i.status, "created_at": i.created_at} for i in open_issues]
    already = {(e.issue_id, e.kind) for e in db.query(Escalation.issue_id, Escalation.kind).all()}
    planned = plan_escalations(rows, load_targets(db), already, now)
    for item in planned:
        db.add(Escalation(created_at=now, **item))
    if planned:
        db.commit()
    return len(planned)
