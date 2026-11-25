"""Response- and resolution-time statistics computed from real status history.

Pure functions over plain values so they can be unit-tested without a database.
"""
from collections import defaultdict
from datetime import datetime, timezone
from statistics import median


def _ts(value) -> float:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def _summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "average_seconds": None, "median_seconds": None}
    return {"count": len(values), "average_seconds": round(sum(values) / len(values)), "median_seconds": round(median(values))}


def response_time_stats(issues: list[dict], history: list[dict]) -> dict:
    """issues: {id, created_at, department, priority}; history: {issue_id, new_status, changed_at}.

    Response time = created -> first "In Progress". Resolution time = created -> first
    "Resolved" or "Closed". Issues without that event are left out, never estimated.
    """
    events = defaultdict(dict)
    for row in sorted(history, key=lambda r: _ts(r["changed_at"])):
        status = "Resolved" if row["new_status"] == "Closed" else row["new_status"]
        events[row["issue_id"]].setdefault(status, _ts(row["changed_at"]))

    response, resolution = [], []
    by_department, by_priority = defaultdict(list), defaultdict(list)
    for issue in issues:
        created = _ts(issue["created_at"])
        seen = events.get(issue["id"], {})
        if "In Progress" in seen:
            response.append(max(0.0, seen["In Progress"] - created))
        if "Resolved" in seen:
            seconds = max(0.0, seen["Resolved"] - created)
            resolution.append(seconds)
            by_department[issue.get("department") or "Unassigned"].append(seconds)
            by_priority[issue.get("priority") or "Medium"].append(seconds)

    return {
        "response": _summary(response),
        "resolution": _summary(resolution),
        "resolution_by_department": [{"department": d, **_summary(v)} for d, v in sorted(by_department.items())],
        "resolution_by_priority": [{"priority": p, **_summary(v)} for p, v in sorted(by_priority.items())],
    }
