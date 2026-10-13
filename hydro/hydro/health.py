"""Lightweight health check endpoint for load balancers / container orchestrators (ALB, ECS)."""

import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    """Return 200 if the app is up and can reach the database, else 503.

    Do not leak internal error details in the response body (avoid information
    disclosure); log the exception server-side instead.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Health check database connectivity failure")
        return JsonResponse({"status": "error"}, status=503)

    return JsonResponse({"status": "ok"})
