"""Readiness endpoint tests; the database engine is mocked, never production data."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app import main


class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()

    def test_health_confirms_database_connection(self):
        with patch.object(main.engine, "connect") as connect:
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})
        connect.assert_called_once_with()

    def test_health_returns_503_when_database_is_unavailable(self):
        with patch.object(main.engine, "connect", side_effect=SQLAlchemyError("database offline")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Database unavailable")


if __name__ == "__main__":
    unittest.main()
