"""Core module tests."""
from unittest.mock import patch
from django.db import OperationalError
from django.test import SimpleTestCase
from rest_framework.test import APIClient


class HealthCheckTests(SimpleTestCase):
    """Verify health endpoint structure without requiring live DB."""

    def test_health_returns_503_when_db_unavailable(self):
        client = APIClient()
        with patch("apps.core.views.connections") as mock_connections:
            mock_connections.__getitem__.return_value.ensure_connection.side_effect = OperationalError(
                "db down"
            )
            response = client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "degraded")
        self.assertEqual(response.data["database"], "unavailable")

