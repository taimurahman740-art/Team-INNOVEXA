"""API regression tests using an isolated in-memory SQLite database."""
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.routes import router


class IssueApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.staff_env = patch.dict(os.environ, {"STAFF_API_KEY": "test-staff-key"})
        self.staff_env.start()

    def tearDown(self):
        self.staff_env.stop()
        self.client.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def create_payload(self, **overrides):
        payload = {
            "title": "Broken classroom light",
            "description": "The ceiling light does not turn on.",
            "location": "Engineering Building Room 201",
            "category": "Other",
        }
        payload.update(overrides)
        return payload

    def test_public_issue_submission_and_initial_history(self):
        response = self.client.post("/issues", json=self.create_payload())
        self.assertEqual(response.status_code, 201)
        issue = response.json()
        self.assertEqual(issue["status"], "Submitted")
        self.assertEqual(issue["risk_level"], "Low")

        history = self.client.get(
            f"/issues/{issue['id']}/history",
            headers={"X-Staff-Key": "test-staff-key"},
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 1)
        self.assertIsNone(history.json()[0]["old_status"])
        self.assertEqual(history.json()[0]["new_status"], "Submitted")

    def test_invalid_image_data_is_rejected(self):
        response = self.client.post(
            "/issues", json=self.create_payload(image_data="not-an-image")
        )
        self.assertEqual(response.status_code, 422)

    def test_image_mime_type_must_match_file_signature(self):
        # PNG signature encoded as a data URL is accepted.
        valid_png = "data:image/png;base64,iVBORw0KGgo="
        accepted = self.client.post(
            "/issues", json=self.create_payload(image_data=valid_png)
        )
        self.assertEqual(accepted.status_code, 201)

        # A valid PNG cannot be relabelled as JPEG.
        mismatched = self.client.post(
            "/issues",
            json=self.create_payload(image_data="data:image/jpeg;base64,iVBORw0KGgo="),
        )
        self.assertEqual(mismatched.status_code, 422)

    def test_malformed_base64_image_is_rejected(self):
        response = self.client.post(
            "/issues",
            json=self.create_payload(image_data="data:image/png;base64,%%%not-base64%%%")
        )
        self.assertEqual(response.status_code, 422)

    def test_staff_endpoints_reject_missing_or_wrong_key(self):
        missing = self.client.patch("/issues/1/status", json={"status": "Resolved"})
        wrong = self.client.get("/issues/resolved", headers={"X-Staff-Key": "wrong"})
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)

    def test_staff_status_update_is_recorded_in_history(self):
        created = self.client.post("/issues", json=self.create_payload())
        issue_id = created.json()["id"]
        headers = {"X-Staff-Key": "test-staff-key"}

        updated = self.client.patch(
            f"/issues/{issue_id}/status",
            json={"status": "In Progress"},
            headers=headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "In Progress")

        history = self.client.get(f"/issues/{issue_id}/history", headers=headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            [event["new_status"] for event in history.json()],
            ["Submitted", "In Progress"],
        )
        self.assertEqual(history.json()[1]["old_status"], "Submitted")

    def test_public_listing_is_readable_without_staff_key(self):
        self.client.post("/issues", json=self.create_payload())
        response = self.client.get("/issues")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        public_issue = response.json()[0]
        self.assertNotIn("description", public_issue)
        self.assertNotIn("location", public_issue)
        self.assertNotIn("image_data", public_issue)

    def test_staff_listing_requires_key_and_returns_full_details(self):
        self.client.post("/issues", json=self.create_payload())
        denied = self.client.get("/issues/staff")
        self.assertEqual(denied.status_code, 401)
        allowed = self.client.get("/issues/staff", headers={"X-Staff-Key": "test-staff-key"})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()[0]["location"], "Engineering Building Room 201")
        self.assertIn("description", allowed.json()[0])

    def test_resolved_reports_endpoint_requires_staff_key(self):
        missing = self.client.get("/issues/resolved")
        self.assertEqual(missing.status_code, 401)

        created = self.client.post("/issues", json=self.create_payload())
        issue_id = created.json()["id"]
        headers = {"X-Staff-Key": "test-staff-key"}
        self.client.patch(
            f"/issues/{issue_id}/status",
            json={"status": "Resolved"},
            headers=headers,
        )
        response = self.client.get("/issues/resolved", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [issue_id])

    def test_invalid_status_value_is_rejected(self):
        created = self.client.post("/issues", json=self.create_payload())
        response = self.client.patch(
            f"/issues/{created.json()['id']}/status",
            json={"status": "Deleted"},
            headers={"X-Staff-Key": "test-staff-key"},
        )
        self.assertEqual(response.status_code, 422)

    def test_status_update_for_unknown_issue_returns_404(self):
        response = self.client.patch(
            "/issues/999/status",
            json={"status": "Resolved"},
            headers={"X-Staff-Key": "test-staff-key"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
