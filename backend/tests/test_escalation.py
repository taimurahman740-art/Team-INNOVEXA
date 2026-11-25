"""Overdue detection and automatic escalation rules (feature 2)."""
import unittest
from datetime import datetime, timedelta, timezone

from app.escalation import DEFAULT_TARGETS, breaches, human_minutes, plan_escalations

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def issue(i, priority="High", status="Submitted", hours_ago=0):
    return {"id": i, "priority": priority, "status": status, "created_at": NOW - timedelta(hours=hours_ago)}


class BreachTests(unittest.TestCase):
    def test_within_target_is_not_overdue(self):
        self.assertEqual(breaches(issue(1, hours_ago=3), DEFAULT_TARGETS["High"], NOW), [])

    def test_not_started_in_time(self):
        b = breaches(issue(1, hours_ago=5), DEFAULT_TARGETS["High"], NOW)
        self.assertEqual([x["kind"] for x in b], ["start"])
        self.assertEqual(b[0]["overdue_minutes"], 60)

    def test_started_but_not_resolved_in_time(self):
        b = breaches(issue(1, status="In Progress", hours_ago=30), DEFAULT_TARGETS["High"], NOW)
        self.assertEqual([x["kind"] for x in b], ["resolve"])

    def test_resolved_reports_are_never_overdue(self):
        self.assertEqual(breaches(issue(1, status="Resolved", hours_ago=500), DEFAULT_TARGETS["High"], NOW), [])

    def test_naive_sqlite_timestamps_are_treated_as_utc(self):
        naive = {**issue(1, hours_ago=5), "created_at": (NOW - timedelta(hours=5)).replace(tzinfo=None)}
        self.assertEqual(len(breaches(naive, DEFAULT_TARGETS["High"], NOW)), 1)


class PlanTests(unittest.TestCase):
    def test_only_auto_escalate_priorities_are_escalated(self):
        planned = plan_escalations([issue(1, "High", hours_ago=5), issue(2, "Medium", hours_ago=100)], DEFAULT_TARGETS, set(), NOW)
        self.assertEqual([(p["issue_id"], p["kind"]) for p in planned], [(1, "start")])
        self.assertIn("not started within 4 h", planned[0]["reason"])

    def test_never_escalates_the_same_breach_twice(self):
        self.assertEqual(plan_escalations([issue(1, hours_ago=5)], DEFAULT_TARGETS, {(1, "start")}, NOW), [])

    def test_both_breaches_escalate_separately(self):
        planned = plan_escalations([issue(1, hours_ago=30)], DEFAULT_TARGETS, set(), NOW)
        self.assertEqual(sorted(p["kind"] for p in planned), ["resolve", "start"])

    def test_custom_targets_are_respected(self):
        targets = {**DEFAULT_TARGETS, "Medium": {"start_within_minutes": 60, "resolve_within_minutes": 120, "auto_escalate": True}}
        self.assertEqual(len(plan_escalations([issue(1, "Medium", hours_ago=2)], targets, set(), NOW)), 1)

    def test_human_minutes(self):
        self.assertEqual((human_minutes(240), human_minutes(1440), human_minutes(10080), human_minutes(90)), ("4 h", "1 day", "7 days", "90 min"))


if __name__ == "__main__":
    unittest.main()
