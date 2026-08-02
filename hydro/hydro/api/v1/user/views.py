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

    def post(self, request):
        serializer = RegistrationSendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="OTP sent successfully.",
            status_code=status.HTTP_200_OK,
        )


class VerifyOtp(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        serializer = LoginSendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            serializer.save()
        except ValidationError as exc:
            return validation_error_response(exc.detail)

        return success_response(
            message="OTP sent successfully.",
            status_code=status.HTTP_200_OK,
        )


class LoginOtpVerify(APIView):
    permission_classes = [AllowAny]

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