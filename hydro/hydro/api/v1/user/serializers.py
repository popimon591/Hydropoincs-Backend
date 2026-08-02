import logging
import secrets
from datetime import timedelta

import phonenumbers
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from phonenumbers import PhoneNumberType
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import CustomUser, PhoneOTP

logger = logging.getLogger(__name__)


def normalize_phone_number(raw_phone_number):
    if raw_phone_number is None:
        raise serializers.ValidationError("Phone number is required.")

    phone_number = "".join(str(raw_phone_number).split())
    if not phone_number:
        raise serializers.ValidationError("Phone number is required.")

    region = getattr(settings, "DEFAULT_PHONE_REGION", None)

    try:
        parsed = phonenumbers.parse(phone_number, region)
    except phonenumbers.NumberParseException:
        raise serializers.ValidationError("Enter a valid phone number.")

    if not phonenumbers.is_valid_number(parsed):
        raise serializers.ValidationError("Enter a valid phone number.")

    number_type = phonenumbers.number_type(parsed)
    if number_type not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE):
        raise serializers.ValidationError("Enter a valid mobile phone number.")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    phone_country = phonenumbers.region_code_for_number(parsed) or ""
    return e164, phone_country


def create_auth_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class OTPService:
    @staticmethod
    def _expiry_seconds():
        return int(getattr(settings, "OTP_EXPIRY_SECONDS", 300))

    @staticmethod
    def _cooldown_seconds():
        return int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60))

    @staticmethod
    def _max_attempts():
        return int(getattr(settings, "OTP_MAX_VERIFY_ATTEMPTS", 5))

    @staticmethod
    def _generate_otp():
        return f"{secrets.randbelow(900000) + 100000:06d}"

    @staticmethod
    def _send_sms(phone_number, otp):
        if settings.DEBUG:
            logger.info("Mock OTP sender for %s. OTP: %s", phone_number, otp)
            return
        logger.info("Mock OTP sender invoked for %s", phone_number)

    @classmethod
    @transaction.atomic
    def send_otp(cls, *, phone_number, purpose, full_name=""):
        now = timezone.now()
        otp_record = (
            PhoneOTP.objects.select_for_update()
            .filter(phone=phone_number, purpose=purpose)
            .first()
        )

        if otp_record and otp_record.resend_available_at > now:
            retry_after = int((otp_record.resend_available_at - now).total_seconds())
            raise serializers.ValidationError(
                {"phone_number": [f"Please wait {retry_after} seconds before requesting a new OTP."]}
            )

        otp_value = cls._generate_otp()
        print(f"Generated OTP for {phone_number}: {otp_value}")  # For debugging purposes
        expiry = now + timedelta(seconds=cls._expiry_seconds())
        resend_available_at = now + timedelta(seconds=cls._cooldown_seconds())

        defaults = {
            "otp_hash": make_password(otp_value),
            "full_name": full_name.strip(),
            "failed_attempts": 0,
            "expires_at": expiry,
            "resend_available_at": resend_available_at,
            "verified_at": None,
            "used_at": None,
        }
        PhoneOTP.objects.update_or_create(
            phone=phone_number,
            purpose=purpose,
            defaults=defaults,
        )
        cls._send_sms(phone_number, otp_value)

    @classmethod
    @transaction.atomic
    def verify_otp(cls, *, phone_number, purpose, otp):
        otp_record = (
            PhoneOTP.objects.select_for_update()
            .filter(phone=phone_number, purpose=purpose)
            .first()
        )
        if not otp_record:
            raise serializers.ValidationError({"otp": ["Invalid OTP."]})

        if otp_record.used_at is not None:
            raise serializers.ValidationError({"otp": ["This OTP has already been used."]})

        now = timezone.now()
        if now > otp_record.expires_at:
            raise serializers.ValidationError({"otp": ["OTP has expired."]})

        if otp_record.failed_attempts >= cls._max_attempts():
            raise serializers.ValidationError(
                {"otp": ["Too many incorrect attempts. Please request a new OTP."]}
            )

        if not check_password(otp, otp_record.otp_hash):
            otp_record.failed_attempts += 1
            otp_record.save(update_fields=["failed_attempts", "updated_at"])
            remaining = max(cls._max_attempts() - otp_record.failed_attempts, 0)
            raise serializers.ValidationError(
                {"otp": [f"Invalid OTP. {remaining} attempt(s) remaining."]}
            )

        otp_record.verified_at = now
        otp_record.save(update_fields=["verified_at", "updated_at"])
        return otp_record


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
        if CustomUser.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return normalized

    def create(self, validated_data):
        OTPService.send_otp(
            phone_number=validated_data["phone_number"],
            purpose=PhoneOTP.Purpose.REGISTRATION,
            full_name=validated_data["full_name"],
        )
        return {}


class RegistrationVerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_phone_number(self, value):
        normalized, phone_country = normalize_phone_number(value)
        if CustomUser.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        self.context["phone_country"] = phone_country
        return normalized

    def validate_otp(self, value):
        otp = value.strip()
        if not otp.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return otp

    @transaction.atomic
    def create(self, validated_data):
        otp_record = OTPService.verify_otp(
            phone_number=validated_data["phone_number"],
            purpose=PhoneOTP.Purpose.REGISTRATION,
            otp=validated_data["otp"],
        )

        full_name = otp_record.full_name.strip()
        if not full_name:
            raise serializers.ValidationError({"full_name": ["Full name is required."]})

        try:
            user = CustomUser.objects.create_user(
                phone=validated_data["phone_number"],
                full_name=full_name,
                phone_country=self.context.get("phone_country", ""),
            )
        except IntegrityError:
            raise serializers.ValidationError({"phone_number": ["This phone number is already registered."]})

        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=["used_at", "updated_at"])

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
        if not CustomUser.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        return normalized

    def create(self, validated_data):
        OTPService.send_otp(
            phone_number=validated_data["phone_number"],
            purpose=PhoneOTP.Purpose.LOGIN,
        )
        return {}


class LoginVerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_phone_number(self, value):
        normalized, _ = normalize_phone_number(value)
        user = CustomUser.objects.filter(phone=normalized).first()
        if not user:
            raise serializers.ValidationError("No account found with this phone number.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        self.context["user"] = user
        return normalized

    def validate_otp(self, value):
        otp = value.strip()
        if not otp.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return otp

    @transaction.atomic
    def create(self, validated_data):
        otp_record = OTPService.verify_otp(
            phone_number=validated_data["phone_number"],
            purpose=PhoneOTP.Purpose.LOGIN,
            otp=validated_data["otp"],
        )

        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=["used_at", "updated_at"])

        user = self.context["user"]
        return {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone,
            },
            "token": create_auth_tokens(user),
        }
