import unittest
from app.analytics import response_time_stats

ISSUES = [
    {"id": 1, "created_at": "2026-11-01T00:00:00Z", "department": "Plumbing Maintenance", "priority": "High"},
    {"id": 2, "created_at": "2026-11-01T00:00:00Z", "department": "Plumbing Maintenance", "priority": "Low"},
    {"id": 3, "created_at": "2026-11-01T00:00:00Z", "department": "IT Infrastructure", "priority": "Medium"},
]
HISTORY = [
    {"issue_id": 1, "new_status": "Submitted", "changed_at": "2026-11-01T00:00:00Z"},
    {"issue_id": 1, "new_status": "In Progress", "changed_at": "2026-11-01T01:00:00Z"},
    {"issue_id": 1, "new_status": "Resolved", "changed_at": "2026-11-01T04:00:00Z"},
    {"issue_id": 2, "new_status": "Closed", "changed_at": "2026-11-02T00:00:00Z"},
    {"issue_id": 3, "new_status": "Submitted", "changed_at": "2026-11-01T00:00:00Z"},
]

class ResponseTimeTests(unittest.TestCase):
    def test_uses_only_real_events(self):
        r = response_time_stats(ISSUES, HISTORY)
        self.assertEqual(r["response"], {"count": 1, "average_seconds": 3600, "median_seconds": 3600})
        self.assertEqual(r["resolution"]["count"], 2)  # issue 3 has no resolution and is not estimated
        self.assertEqual(r["resolution"]["average_seconds"], (4 * 3600 + 24 * 3600) // 2)

    def test_grouped_by_department(self):
        deps = {d["department"]: d for d in response_time_stats(ISSUES, HISTORY)["resolution_by_department"]}
        self.assertEqual(deps["Plumbing Maintenance"]["count"], 2)
        self.assertNotIn("IT Infrastructure", deps)

    def test_empty(self):
        self.assertEqual(response_time_stats([], [])["resolution"]["average_seconds"], None)
