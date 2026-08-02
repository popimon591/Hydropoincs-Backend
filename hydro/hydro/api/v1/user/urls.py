from django.urls import path
from hydro.api.v1.user import views
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("register/send-otp", views.RegisterProfile.as_view(), name="register_send_otp"),
    path("register/verify-otp", views.VerifyOtp.as_view(), name="register_verify_otp"),
    path("login/send-otp", views.LoginOtp.as_view(), name="login_send_otp"),
    path("login/verify-otp", views.LoginOtpVerify.as_view(), name="login_verify_otp"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # Backward-compatible aliases
    path("register/otp/", views.RegisterProfile.as_view(), name="register_otp_legacy"),
    path("register/otp/verify/", views.VerifyOtp.as_view(), name="register_verify_otp_legacy"),
    path("login/otp/", views.LoginOtp.as_view(), name="login_otp_legacy"),
    path("login/otp/verify/", views.LoginOtpVerify.as_view(), name="login_verify_otp_legacy"),
]