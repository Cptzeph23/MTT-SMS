"""Web views for authentication and password management."""
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.audit import actions
from apps.audit.services import record
from apps.schools.models import School
from smsApp.utils import get_client_ip

from . import throttle
from .forms import (
    ForceChangePasswordForm,
    ForgotPasswordForm,
    LoginForm,
    SetNewPasswordForm,
)
from .models import User
from .services import change_password
from .tokens import make_reset_link, token_is_valid, user_from_uidb64

GENERIC_RESET_MESSAGE = (
    "If those details match an account with an email on file, we have sent "
    "password reset instructions to that address."
)


@method_decorator([csrf_protect, never_cache], name="dispatch")
class LoginView(View):
    """Handles both the school-branded login and the platform login.

    A URL with a school code (`/login/<school-code>/`) locks the school and
    shows its branding. The bare `/login/` URL is for Super Admin, and also
    accepts a school code typed into the form, as a fallback entry point.
    """

    template_name = "accounts/login.html"

    def get(self, request, school_code=None):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        school = self._get_school_or_404(school_code)
        form = LoginForm(initial={"school_code": school_code or ""})
        return render(request, self.template_name, self._context(school, school_code, form))

    def post(self, request, school_code=None):
        school = self._get_school_or_404(school_code)
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(school, school_code, form))

        effective_code = school_code or form.cleaned_data["school_code"]
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        ip_address = get_client_ip(request)

        if throttle.is_locked(ip_address, effective_code, username):
            form.add_error(
                None,
                "Too many failed attempts. Please try again later or reset your password.",
            )
            return render(request, self.template_name, self._context(school, school_code, form))

        user = authenticate(
            request, username=username, password=password, school_code=effective_code or None
        )
        if user is None:
            attempts = throttle.register_failure(ip_address, effective_code, username)
            if attempts >= throttle.max_attempts():
                record(
                    action=actions.LOGIN_LOCKED,
                    module=actions.MODULE_AUTH,
                    object_type="User",
                    object_repr=username,
                    request=request,
                )
            form.add_error(None, "Invalid credentials. Please try again.")
            return render(request, self.template_name, self._context(school, school_code, form))

        throttle.clear(ip_address, effective_code, username)
        auth_login(request, user)
        if user.must_change_password:
            return redirect("accounts:change-password")
        return redirect("core:dashboard")

    @staticmethod
    def _get_school_or_404(school_code):
        if not school_code:
            return None
        return get_object_or_404(School, code__iexact=school_code, is_active=True)

    @staticmethod
    def _context(school, school_code, form):
        return {
            "form": form,
            "school": school,
            "school_locked": school_code is not None,
        }


@method_decorator([csrf_protect, never_cache], name="dispatch")
class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        return redirect("accounts:login")

    def get(self, request):
        return self.post(request)


@method_decorator([csrf_protect, never_cache], name="dispatch")
class ForceChangePasswordView(View):
    """Shown automatically until the temporary password is replaced.

    PasswordChangeEnforcementMiddleware redirects every other page here for
    a user with must_change_password set, so this requirement cannot be
    skipped.
    """

    template_name = "accounts/change_password.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.must_change_password:
            return redirect("core:dashboard")
        return render(request, self.template_name, {"form": ForceChangePasswordForm(user=request.user)})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        form = ForceChangePasswordForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                change_password(
                    user=request.user,
                    new_password=form.cleaned_data["new_password"],
                    request=request,
                )
            except DjangoValidationError as exc:
                for error in exc.messages:
                    form.add_error(None, error)
            else:
                messages.success(request, "Your password has been updated.")
                return redirect("core:dashboard")
        return render(request, self.template_name, {"form": form})


@method_decorator([csrf_protect, never_cache], name="dispatch")
class ForgotPasswordRequestView(View):
    template_name = "accounts/forgot_password.html"

    def get(self, request, school_code=None):
        school = self._get_school(school_code)
        return render(
            request,
            self.template_name,
            {"form": ForgotPasswordForm(), "school": school, "school_locked": school_code is not None},
        )

    def post(self, request, school_code=None):
        school = self._get_school(school_code)
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            queryset = User.objects.filter(school=school) if school else User.objects.filter(
                school__isnull=True
            )
            user = queryset.filter(username__iexact=username, is_active=True).first()
            if user is not None and user.email:
                reset_link = make_reset_link(request, user)
                send_mail(
                    subject="Password reset instructions",
                    message=(
                        f"Hello {user.display_name},\n\n"
                        f"Use the link below to set a new password. It expires once used "
                        f"or once your password changes.\n\n{reset_link}\n\n"
                        "If you did not request this, you can ignore this message."
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                )
                record(
                    action=actions.PASSWORD_RESET_REQUESTED,
                    module=actions.MODULE_ACCOUNTS,
                    school=school,
                    obj=user,
                    request=request,
                )
            messages.success(request, GENERIC_RESET_MESSAGE)
            return redirect(request.path)
        return render(
            request,
            self.template_name,
            {"form": form, "school": school, "school_locked": school_code is not None},
        )

    @staticmethod
    def _get_school(school_code):
        if not school_code:
            return None
        return get_object_or_404(School, code__iexact=school_code, is_active=True)


@method_decorator([csrf_protect, never_cache], name="dispatch")
class PasswordResetConfirmView(View):
    template_name = "accounts/reset_password_confirm.html"

    def get(self, request, uidb64, token):
        user = user_from_uidb64(uidb64)
        valid = token_is_valid(user, token)
        form = SetNewPasswordForm(user=user) if valid else None
        return render(request, self.template_name, {"validlink": valid, "form": form})

    def post(self, request, uidb64, token):
        user = user_from_uidb64(uidb64)
        valid = token_is_valid(user, token)
        if not valid:
            return render(request, self.template_name, {"validlink": False, "form": None})

        form = SetNewPasswordForm(request.POST, user=user)
        if form.is_valid():
            try:
                change_password(
                    user=user, new_password=form.cleaned_data["new_password"], request=request
                )
            except DjangoValidationError as exc:
                for error in exc.messages:
                    form.add_error(None, error)
            else:
                record(
                    action=actions.PASSWORD_RESET_COMPLETED,
                    module=actions.MODULE_ACCOUNTS,
                    school=user.school,
                    obj=user,
                    request=request,
                )
                messages.success(request, "Your password has been reset. You may now log in.")
                return redirect("accounts:login")
        return render(request, self.template_name, {"validlink": True, "form": form})
