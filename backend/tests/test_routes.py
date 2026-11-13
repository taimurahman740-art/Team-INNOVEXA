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

    def test_image_classification_requires_provider_token(self):
        with patch.dict(os.environ, {"HF_TOKEN": ""}):
            response = self.client.post(
                "/issues/image-classification",
                json={"image_data": "data:image/png;base64,iVBORw0KGgo="},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("HF_TOKEN", response.json()["detail"])

    def test_image_classification_returns_model_category(self):
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            with patch(
                "app.routes.classify_campus_image",
                return_value={"category": "Plumbing", "score": 0.87, "model": "test-model"},
            ):
                response = self.client.post(
                    "/issues/image-classification",
                    json={"image_data": "data:image/png;base64,iVBORw0KGgo="},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["category"], "Plumbing")
        self.assertEqual(response.json()["score"], 0.87)

    def test_image_classification_rejects_invalid_image_before_provider_call(self):
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            with patch("app.routes.classify_campus_image") as classify:
                response = self.client.post(
                    "/issues/image-classification",
                    json={"image_data": "data:image/png;base64,not-a-real-png"},
                )
        self.assertEqual(response.status_code, 422)
        classify.assert_not_called()

    def test_image_classification_uses_configured_model(self):
        image_data = "data:image/png;base64,iVBORw0KGgo="
        with patch.dict(os.environ, {"HF_TOKEN": "test-token", "HF_IMAGE_MODEL": "custom/test-model"}):
            with patch(
                "app.routes.classify_campus_image",
                return_value={"category": "Electrical", "score": 0.91, "model": "custom/test-model"},
            ) as classify:
                response = self.client.post(
                    "/issues/image-classification",
                    json={"image_data": image_data},
                )
        self.assertEqual(response.status_code, 200)
        classify.assert_called_once_with(bytes.fromhex("89504e470d0a1a0a"), "test-token", "custom/test-model")

    def test_image_provider_failure_returns_safe_fallback_message(self):
        secret = "hf-test-secret-must-not-leak"
        with patch.dict(os.environ, {"HF_TOKEN": secret}):
            with patch(
                "app.routes.classify_campus_image",
                side_effect=RuntimeError(f"provider failed with token {secret}"),
            ):
                response = self.client.post(
                    "/issues/image-classification",
                    json={"image_data": "data:image/png;base64,iVBORw0KGgo="},
                )
        self.assertEqual(response.status_code, 502)
        self.assertIn("choose a category manually", response.json()["detail"])
        self.assertNotIn(secret, response.text)

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

    def test_high_risk_report_cannot_be_downgraded_by_submitted_priority(self):
        response = self.client.post(
            "/issues",
            json=self.create_payload(
                title="Water near electrical outlet",
                description="Water is dripping beside a live power outlet.",
                priority="Low",
            ),
        )
        self.assertEqual(response.status_code, 201)
        issue = response.json()
        self.assertEqual(issue["risk_level"], "High")
        self.assertGreaterEqual(issue["risk_score"], 5)
        self.assertEqual(issue["priority"], "High")

    def test_routine_report_can_keep_submitted_priority(self):
        response = self.client.post(
            "/issues",
            json=self.create_payload(
                title="Broken classroom chair",
                description="One chair leg is damaged and needs repair.",
                priority="Low",
            ),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["risk_level"], "Low")
        self.assertEqual(response.json()["priority"], "Low")


if __name__ == "__main__":
    unittest.main()
