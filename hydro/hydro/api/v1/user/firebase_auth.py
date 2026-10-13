import logging
from threading import Lock
from time import perf_counter

import firebase_admin
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import auth, credentials, exceptions
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)
_FIREBASE_APP_NAME = "hydro-auth"
_FIREBASE_APP_LOCK = Lock()


class FirebaseServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Firebase authentication is temporarily unavailable."
    default_code = "service_unavailable"


def _get_firebase_app():
    project_id = settings.FIREBASE_PROJECT_ID
    if not project_id:
        raise ImproperlyConfigured("FIREBASE_PROJECT_ID environment variable is not set")

    with _FIREBASE_APP_LOCK:
        try:
            return firebase_admin.get_app(_FIREBASE_APP_NAME)
        except ValueError:
            credential_path = settings.FIREBASE_CREDENTIALS
            credential = (
                credentials.Certificate(credential_path)
                if credential_path
                else credentials.ApplicationDefault()
            )
            return firebase_admin.initialize_app(
                credential,
                options={"projectId": project_id},
                name=_FIREBASE_APP_NAME,
            )


def verify_firebase_phone_token(id_token, *, expected_phone):
    started_at = perf_counter()
    try:
        try:
            claims = auth.verify_id_token(
                id_token,
                app=_get_firebase_app(),
                check_revoked=True,
            )
        except (
            auth.InvalidIdTokenError,
            auth.UserDisabledError,
            auth.UserNotFoundError,
        ) as exc:
            logger.info("Firebase rejected an invalid or expired phone-auth token")
            raise serializers.ValidationError(
                {"firebase_id_token": ["Invalid or expired Firebase authentication token."]}
            ) from exc
        except exceptions.FirebaseError as exc:
            logger.exception("Firebase phone-auth token verification failed")
            raise FirebaseServiceUnavailable() from exc

        if claims.get("phone_number") != expected_phone:
            raise serializers.ValidationError(
                {"firebase_id_token": ["The verified phone number does not match."]}
            )
        return claims
    finally:
        logger.info(
            "auth_timing operation=firebase_id_token_verification duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )
