from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("login/<slug:school_code>/", views.LoginView.as_view(), name="login-school"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("change-password/", views.ForceChangePasswordView.as_view(), name="change-password"),
    path("forgot-password/", views.ForgotPasswordRequestView.as_view(), name="forgot-password"),
    path(
        "forgot-password/<slug:school_code>/",
        views.ForgotPasswordRequestView.as_view(),
        name="forgot-password-school",
    ),
    path(
        "reset-password/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="reset-password-confirm",
    ),
]
