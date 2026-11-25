"""Core utility endpoints including health check."""
from django.db import OperationalError, connections
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Report API and PostgreSQL connectivity status."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        db_status = "connected"
        try:
            conn = connections["default"]
            conn.ensure_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except OperationalError:
            db_ok = False
            db_status = "unavailable"

        payload = {
            "status": "ok" if db_ok else "degraded",
            "service": "mca-career-compass-api",
            "database": db_status,
            "timestamp": timezone.now().isoformat(),
        }
        http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)

