import logging
from functools import wraps
from time import perf_counter

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from hydro.api.v1.user.serializers import (
    LoginSendOTPSerializer,
    LoginVerifyOTPSerializer,
    RegistrationSendOTPSerializer,
    RegistrationVerifyOTPSerializer,
)

logger = logging.getLogger(__name__)


def timed_auth_endpoint(endpoint_name):
    def decorate(view_method):
        @wraps(view_method)
        def timed_view(self, request, *args, **kwargs):
            started_at = perf_counter()
            try:
                return view_method(self, request, *args, **kwargs)
            finally:
                logger.info(
                    "auth_timing endpoint=%s duration_ms=%.2f",
                    endpoint_name,
                    (perf_counter() - started_at) * 1000,
                )

        return timed_view

    return decorate


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data or {},
        },
        status=status_code,
    )


def validation_error_response(errors, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "errors": errors,
        },
        status=status_code,
    )


class RegisterProfile(APIView):
    permission_classes = [AllowAny]

    @timed_auth_endpoint("register_send_otp")
    def post(self, request):
        serializer = RegistrationSendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            payload = serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="Phone number is ready for Firebase verification.",
            data=payload,
            status_code=status.HTTP_200_OK,
        )


class VerifyOtp(APIView):
    permission_classes = [AllowAny]

    @timed_auth_endpoint("register_verify_otp")
    def post(self, request):
        serializer = RegistrationVerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            payload = serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="Registration successful.",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )


class LoginOtp(APIView):
    permission_classes = [AllowAny]

    @timed_auth_endpoint("login_send_otp")
    def post(self, request):
        serializer = LoginSendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            payload = serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="Phone number is ready for Firebase verification.",
            data=payload,
            status_code=status.HTTP_200_OK,
        )


class LoginOtpVerify(APIView):
    permission_classes = [AllowAny]

    @timed_auth_endpoint("login_verify_otp")
    def post(self, request):
        serializer = LoginVerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            payload = serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="Login successful.",
            data=payload,
            status_code=status.HTTP_200_OK,
        )