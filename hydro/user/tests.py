from unittest.mock import patch

from django.test import SimpleTestCase
from firebase_admin import auth
from rest_framework.exceptions import ValidationError

from hydro.api.v1.user.firebase_auth import verify_firebase_phone_token
from hydro.api.v1.user.serializers import (
    LoginSendOTPSerializer,
    LoginVerifyOTPSerializer,
    RegistrationSendOTPSerializer,
    RegistrationVerifyOTPSerializer,
)


class FirebasePhoneTokenTests(SimpleTestCase):
    @patch("hydro.api.v1.user.firebase_auth._get_firebase_app")
    @patch("hydro.api.v1.user.firebase_auth.auth.verify_id_token")
    def test_verifies_phone_claim_and_checks_revocation(self, verify_token, get_app):
        app = object()
        get_app.return_value = app
        verify_token.return_value = {"phone_number": "+14155552671", "uid": "firebase-user"}

        claims = verify_firebase_phone_token(
            "signed-firebase-token",
            expected_phone="+14155552671",
        )

        self.assertEqual(claims["uid"], "firebase-user")
        verify_token.assert_called_once_with(
            "signed-firebase-token",
            app=app,
            check_revoked=True,
        )

    @patch("hydro.api.v1.user.firebase_auth._get_firebase_app")
    @patch("hydro.api.v1.user.firebase_auth.auth.verify_id_token")
    def test_rejects_a_token_for_a_different_phone(self, verify_token, _get_app):
        verify_token.return_value = {"phone_number": "+14155550000"}

        with self.assertRaises(ValidationError):
            verify_firebase_phone_token(
                "signed-firebase-token",
                expected_phone="+14155552671",
            )

    @patch("hydro.api.v1.user.firebase_auth._get_firebase_app")
    @patch("hydro.api.v1.user.firebase_auth.auth.verify_id_token")
    def test_rejects_invalid_firebase_token(self, verify_token, _get_app):
        verify_token.side_effect = auth.InvalidIdTokenError("invalid token")

        with self.assertRaises(ValidationError):
            verify_firebase_phone_token(
                "invalid-token",
                expected_phone="+14155552671",
            )


class PhoneOTPFlowTests(SimpleTestCase):
    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_invalid_phone_is_rejected_before_database_lookup(self, filter_users):
        login = LoginSendOTPSerializer(data={"phone_number": "not-a-phone"})
        registration = RegistrationSendOTPSerializer(
            data={
                "full_name": "Ada Lovelace",
                "phone_number": "not-a-phone",
            }
        )

        self.assertFalse(login.is_valid())
        self.assertFalse(registration.is_valid())
        filter_users.assert_not_called()

    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_send_otp_preflight_checks_database_eligibility(self, filter_users):
        user = type("User", (), {"is_active": True})()
        filter_users.return_value.only.return_value.first.return_value = user
        filter_users.return_value.exists.return_value = False
        login = LoginSendOTPSerializer(
            data={"phone_number": "+14155552671"}
        )
        registration = RegistrationSendOTPSerializer(
            data={
                "full_name": "Ada Lovelace",
                "phone_number": "+14155552671",
            }
        )

        self.assertTrue(login.is_valid(), login.errors)
        self.assertTrue(registration.is_valid(), registration.errors)
        self.assertEqual(filter_users.call_count, 2)

    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_login_preflight_rejects_missing_or_inactive_users(self, filter_users):
        filter_users.return_value.only.return_value.first.return_value = None
        missing_user = LoginSendOTPSerializer(
            data={"phone_number": "+14155552671"}
        )

        self.assertFalse(missing_user.is_valid())
        self.assertEqual(
            missing_user.errors["phone_number"][0],
            "No account found with this phone number.",
        )

        filter_users.return_value.only.return_value.first.return_value = type(
            "User", (), {"is_active": False}
        )()
        inactive_user = LoginSendOTPSerializer(
            data={"phone_number": "+14155552671"}
        )

        self.assertFalse(inactive_user.is_valid())
        self.assertEqual(
            inactive_user.errors["phone_number"][0],
            "This account is inactive.",
        )

    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_registration_preflight_rejects_existing_user(self, filter_users):
        filter_users.return_value.exists.return_value = True
        registration = RegistrationSendOTPSerializer(
            data={
                "full_name": "Ada Lovelace",
                "phone_number": "+14155552671",
            }
        )

        self.assertFalse(registration.is_valid())
        self.assertEqual(
            registration.errors["phone_number"][0],
            "This phone number is already registered.",
        )

    @patch("hydro.api.v1.user.serializers.verify_firebase_phone_token")
    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_login_checks_database_only_after_firebase_verification(
        self, filter_users, verify_token
    ):
        events = []
        user = type(
            "User",
            (),
            {
                "is_active": True,
                "id": 1,
                "full_name": "Ada Lovelace",
                "phone": "+14155552671",
            },
        )()
        filter_users.return_value.only.return_value.first.return_value = user
        filter_users.side_effect = lambda **kwargs: (
            events.append("database"),
            filter_users.return_value,
        )[1]
        verify_token.side_effect = lambda *args, **kwargs: events.append("firebase")

        serializer = LoginVerifyOTPSerializer(
            data={
                "phone_number": "+14155552671",
                "firebase_id_token": "verified-token",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(events, ["firebase", "database"])
        self.assertIs(serializer.context["user"], user)

    @patch("hydro.api.v1.user.serializers.verify_firebase_phone_token")
    @patch("hydro.api.v1.user.serializers.CustomUser.objects.filter")
    def test_registration_checks_duplicate_only_after_firebase_verification(
        self, filter_users, verify_token
    ):
        events = []
        filter_users.return_value.exists.return_value = True
        filter_users.side_effect = lambda **kwargs: (
            events.append("database"),
            filter_users.return_value,
        )[1]
        verify_token.side_effect = lambda *args, **kwargs: events.append("firebase")

        serializer = RegistrationVerifyOTPSerializer(
            data={
                "full_name": "Ada Lovelace",
                "phone_number": "+14155552671",
                "firebase_id_token": "verified-token",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(events, ["firebase", "database"])
        self.assertIn("phone_number", serializer.errors)
