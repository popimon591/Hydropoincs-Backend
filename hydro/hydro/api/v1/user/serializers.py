import logging
from time import perf_counter

import phonenumbers
from django.conf import settings
from django.db import IntegrityError, transaction
from phonenumbers import PhoneNumberType
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from hydro.api.v1.user.firebase_auth import verify_firebase_phone_token
from user.models import CustomUser

logger = logging.getLogger(__name__)


def normalize_phone_number(raw_phone_number):
    if raw_phone_number is None:
        raise serializers.ValidationError("Phone number is required.")

    phone_number = "".join(str(raw_phone_number).split())
    if not phone_number:
        raise serializers.ValidationError("Phone number is required.")

    region = getattr(settings, "DEFAULT_PHONE_REGION", None)

    started_at = perf_counter()
    try:
        parsed = phonenumbers.parse(phone_number, region)
    except phonenumbers.NumberParseException:
        logger.info(
            "auth_timing operation=phone_normalization duration_ms=%.2f valid=false",
            (perf_counter() - started_at) * 1000,
        )
        raise serializers.ValidationError("Enter a valid phone number.")

    if not phonenumbers.is_valid_number(parsed):
        logger.info(
            "auth_timing operation=phone_normalization duration_ms=%.2f valid=false",
            (perf_counter() - started_at) * 1000,
        )
        raise serializers.ValidationError("Enter a valid phone number.")

    number_type = phonenumbers.number_type(parsed)
    if number_type not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE):
        raise serializers.ValidationError("Enter a valid mobile phone number.")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    phone_country = phonenumbers.region_code_for_number(parsed) or ""
    logger.info(
        "auth_timing operation=phone_normalization duration_ms=%.2f valid=true",
        (perf_counter() - started_at) * 1000,
    )
    return e164, phone_country


def create_auth_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class RegistrationSendOTPSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100, trim_whitespace=True)
    phone_number = serializers.CharField(max_length=30)

    def validate_full_name(self, value):
        full_name = value.strip()
        if not full_name:
            raise serializers.ValidationError("Full name is required.")
        return full_name

    def validate_phone_number(self, value):
        normalized, _ = normalize_phone_number(value)
        started_at = perf_counter()
        exists = CustomUser.objects.filter(phone=normalized).exists()
        logger.info(
            "auth_timing operation=registration_preflight_lookup duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )
        if exists:
            raise serializers.ValidationError(
                "This phone number is already registered."
            )
        return normalized

    def create(self, validated_data):
        return {
            "phone_number": validated_data["phone_number"],
            "provider": "firebase",
        }


class RegistrationVerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)
    full_name = serializers.CharField(max_length=100, trim_whitespace=True)
    firebase_id_token = serializers.CharField(max_length=8192, write_only=True)

    def validate_phone_number(self, value):
        normalized, phone_country = normalize_phone_number(value)
        self.context["phone_country"] = phone_country
        return normalized

    def validate_full_name(self, value):
        full_name = value.strip()
        if not full_name:
            raise serializers.ValidationError("Full name is required.")
        return full_name

    def validate(self, attrs):
        verify_firebase_phone_token(
            attrs["firebase_id_token"],
            expected_phone=attrs["phone_number"],
        )
        started_at = perf_counter()
        already_registered = CustomUser.objects.filter(
            phone=attrs["phone_number"]
        ).exists()
        logger.info(
            "auth_timing operation=registration_verification_lookup duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )
        if already_registered:
            raise serializers.ValidationError(
                {"phone_number": ["This phone number is already registered."]}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        started_at = perf_counter()
        try:
            user = CustomUser.objects.create_user(
                phone=validated_data["phone_number"],
                full_name=validated_data["full_name"],
                phone_country=self.context.get("phone_country", ""),
            )
        except IntegrityError:
            raise serializers.ValidationError({"phone_number": ["This phone number is already registered."]})
        finally:
            logger.info(
                "auth_timing operation=registration_account_creation duration_ms=%.2f",
                (perf_counter() - started_at) * 1000,
            )

        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone,
            },
            "token": create_auth_tokens(user),
        }


class LoginSendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)

    def validate_phone_number(self, value):
        normalized, _ = normalize_phone_number(value)
        started_at = perf_counter()
        user = CustomUser.objects.filter(phone=normalized).only("is_active").first()
        logger.info(
            "auth_timing operation=login_preflight_lookup duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )
        if not user:
            raise serializers.ValidationError(
                "No account found with this phone number."
            )
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        return normalized

    def create(self, validated_data):
        return {
            "phone_number": validated_data["phone_number"],
            "provider": "firebase",
        }


class LoginVerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)
    firebase_id_token = serializers.CharField(max_length=8192, write_only=True)

    def validate_phone_number(self, value):
        normalized, _ = normalize_phone_number(value)
        return normalized

    def validate(self, attrs):
        verify_firebase_phone_token(
            attrs["firebase_id_token"],
            expected_phone=attrs["phone_number"],
        )
        started_at = perf_counter()
        user = (
            CustomUser.objects.filter(phone=attrs["phone_number"])
            .only("is_active", "id", "full_name", "phone")
            .first()
        )
        logger.info(
            "auth_timing operation=login_verification_user_lookup duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )
        if not user:
            raise serializers.ValidationError(
                {"phone_number": ["No account found with this phone number."]}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"phone_number": ["This account is inactive."]}
            )
        self.context["user"] = user
        return attrs

    def create(self, validated_data):
        user = self.context["user"]
        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone,
            },
            "token": create_auth_tokens(user),
        }
