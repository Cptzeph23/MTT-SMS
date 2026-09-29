"""Web view tests: login, forced password change, forgot/reset password."""
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role
from apps.accounts.tokens import make_reset_link
from apps.audit import actions
from apps.audit.models import AuditLog
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user

STRONG_PASSWORD = "Vq7#mLp29-Xz"


class LoginViewTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.teacher = make_user(self.school, Role.TEACHER, "tea1", must_change_password=False)
        self.admin = make_super_admin("root")

    def test_school_branded_login_page_renders(self):
        response = self.client.get(reverse("accounts:login-school", args=["alpha"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha")

    def test_unknown_school_login_page_is_404(self):
        response = self.client.get(reverse("accounts:login-school", args=["nowhere"]))
        self.assertEqual(response.status_code, 404)

    def test_successful_school_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login-school", args=["alpha"]),
            {"username": "tea1", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)

    def test_login_is_case_insensitive_on_username(self):
        response = self.client.post(
            reverse("accounts:login-school", args=["alpha"]),
            {"username": "TEA1", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)

    def test_wrong_password_shows_error_and_is_audited(self):
        response = self.client.post(
            reverse("accounts:login-school", args=["alpha"]),
            {"username": "tea1", "password": "wrong-one"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")
        self.assertTrue(AuditLog.objects.filter(action=actions.LOGIN_FAILED).exists())

    def test_generic_login_accepts_a_typed_school_code(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"school_code": "alpha", "username": "tea1", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)

    def test_super_admin_uses_generic_login_with_no_school_code(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "root", "password": DEFAULT_PASSWORD}
        )
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)

    def test_first_login_redirects_to_change_password(self):
        make_user(self.school, Role.TEACHER, "newteacher", must_change_password=True)
        response = self.client.post(
            reverse("accounts:login-school", args=["alpha"]),
            {"username": "newteacher", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse("accounts:change-password"))

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
    def test_account_locks_after_repeated_failures(self):
        url = reverse("accounts:login-school", args=["alpha"])
        for _ in range(3):
            self.client.post(url, {"username": "tea1", "password": "wrong"})
        response = self.client.post(url, {"username": "tea1", "password": DEFAULT_PASSWORD})
        self.assertContains(response, "Too many failed attempts")

    def test_already_authenticated_user_is_redirected_away_from_login(self):
        self.client.login(username="tea1", password=DEFAULT_PASSWORD, school_code="alpha")
        response = self.client.get(reverse("accounts:login-school", args=["alpha"]))
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)


class ForcedPasswordChangeTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.user = make_user(self.school, Role.TEACHER, "tea1", must_change_password=True)
        self.client.login(username="tea1", password=DEFAULT_PASSWORD, school_code="alpha")

    def test_cannot_bypass_by_visiting_the_dashboard_directly(self):
        response = self.client.get(reverse("core:dashboard-teacher"))
        self.assertRedirects(response, reverse("accounts:change-password"))

    def test_can_reach_logout_while_change_is_pending(self):
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_successful_change_clears_the_flag_and_reaches_dashboard(self):
        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "current_password": DEFAULT_PASSWORD,
                "new_password": STRONG_PASSWORD,
                "confirm_password": STRONG_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

    def test_wrong_current_password_is_rejected(self):
        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "current_password": "not-the-temp-password",
                "new_password": STRONG_PASSWORD,
                "confirm_password": STRONG_PASSWORD,
            },
        )
        self.assertContains(response, "current password is incorrect")

    def test_mismatched_confirmation_is_rejected(self):
        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "current_password": DEFAULT_PASSWORD,
                "new_password": STRONG_PASSWORD,
                "confirm_password": STRONG_PASSWORD + "x",
            },
        )
        self.assertContains(response, "do not match")

    def test_weak_new_password_is_rejected(self):
        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "current_password": DEFAULT_PASSWORD,
                "new_password": "password1",
                "confirm_password": "password1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)


class ForgotAndResetPasswordTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.user = make_user(
            self.school, Role.TEACHER, "tea1", email="tea1@example.com", must_change_password=False
        )
        self.no_email_user = make_user(self.school, Role.TEACHER, "tea2", must_change_password=False)

    def test_forgot_password_sends_email_for_known_user_with_email(self):
        response = self.client.post(
            reverse("accounts:forgot-password-school", args=["alpha"]), {"username": "tea1"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("tea1@example.com", mail.outbox[0].to)

    def test_forgot_password_gives_generic_response_for_unknown_user(self):
        response = self.client.post(
            reverse("accounts:forgot-password-school", args=["alpha"]), {"username": "ghost"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_password_gives_generic_response_for_user_without_email(self):
        response = self.client.post(
            reverse("accounts:forgot-password-school", args=["alpha"]), {"username": "tea2"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_sets_a_new_password(self):
        factory_request = self.client.get(reverse("accounts:login")).wsgi_request
        link = make_reset_link(factory_request, self.user)
        path = link.split("http://testserver", 1)[-1]
        get_response = self.client.get(path)
        self.assertTrue(get_response.context["validlink"])

        response = self.client.post(
            path, {"new_password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD}
        )
        self.assertRedirects(response, reverse("accounts:login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))
        self.assertFalse(self.user.must_change_password)

    def test_reset_link_cannot_be_reused(self):
        factory_request = self.client.get(reverse("accounts:login")).wsgi_request
        link = make_reset_link(factory_request, self.user)
        path = link.split("http://testserver", 1)[-1]
        self.client.post(path, {"new_password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD})

        second = self.client.get(path)
        self.assertFalse(second.context["validlink"])

    def test_invalid_token_is_rejected(self):
        response = self.client.get(
            reverse("accounts:reset-password-confirm", args=["bad-uid", "bad-token"])
        )
        self.assertFalse(response.context["validlink"])
