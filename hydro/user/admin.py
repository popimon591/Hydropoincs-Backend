from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from user.models import CustomUser, PhoneOTP


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ("id",)
    list_display = ("id", "full_name", "phone", "phone_country", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("full_name", "phone")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("full_name", "phone_country", "first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "phone_country", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "failed_attempts", "expires_at", "used_at", "updated_at")
    list_filter = ("purpose",)
    search_fields = ("phone",)
    readonly_fields = ("otp_hash", "created_at", "updated_at", "verified_at", "used_at")