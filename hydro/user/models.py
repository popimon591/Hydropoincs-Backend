from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, full_name, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required.")
        if not full_name:
            raise ValueError("Full name is required.")

        user = self.model(phone=phone, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone, full_name, password, **extra_fields)


class CustomUser(AbstractUser):

    username = None
    email = None

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=17, unique=True)
    phone_country = models.CharField(max_length=5, blank=True, default="")

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]
    objects = CustomUserManager()

    def __str__(self):
        return self.full_name


class PhoneOTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        LOGIN = "login", "Login"

    phone = models.CharField(max_length=17,db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    otp_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=100, blank=True, default="")
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    resend_available_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["phone", "purpose"],
                name="unique_phone_purpose_otp",
            )
        ]

    def __str__(self):
        return f"{self.phone} ({self.purpose})"