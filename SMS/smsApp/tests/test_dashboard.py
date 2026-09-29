"""Dashboard routing and role isolation tests."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user

ROLE_DASHBOARD_URL = {
    Role.SUPER_ADMIN: "core:dashboard-super-admin",
    Role.PRINCIPAL: "core:dashboard-principal",
    Role.DEPUTY_PRINCIPAL: "core:dashboard-deputy-principal",
    Role.FINANCE_ADMIN: "core:dashboard-finance",
    Role.TEACHER: "core:dashboard-teacher",
    Role.PARENT: "core:dashboard-parent",
}


class DashboardRoutingTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")

    def _login(self, role, username):
        make_user(self.school, role, username, must_change_password=False)
        self.client.login(username=username, password=DEFAULT_PASSWORD, school_code="alpha")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_each_role_is_routed_to_its_own_dashboard(self):
        for role, url_name in ROLE_DASHBOARD_URL.items():
            with self.subTest(role=role):
                self.client.logout()
                if role == Role.SUPER_ADMIN:
                    make_super_admin("root_" + role)
                    self.client.login(username="root_" + role, password=DEFAULT_PASSWORD)
                else:
                    self._login(role, f"user_{role}")
                response = self.client.get(reverse("core:dashboard"))
                self.assertRedirects(response, reverse(url_name))

    def test_teacher_cannot_open_principal_dashboard_by_editing_the_url(self):
        self._login(Role.TEACHER, "tea1")
        response = self.client.get(reverse("core:dashboard-principal"))
        self.assertEqual(response.status_code, 403)

    def test_deputy_cannot_open_finance_dashboard_by_editing_the_url(self):
        self._login(Role.DEPUTY_PRINCIPAL, "dep1")
        response = self.client.get(reverse("core:dashboard-finance"))
        self.assertEqual(response.status_code, 403)

    def test_parent_cannot_open_super_admin_dashboard(self):
        self._login(Role.PARENT, "par1")
        response = self.client.get(reverse("core:dashboard-super-admin"))
        self.assertEqual(response.status_code, 403)

    def test_own_dashboard_renders_successfully(self):
        self._login(Role.TEACHER, "tea1")
        response = self.client.get(reverse("core:dashboard-teacher"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher Dashboard")


class ErrorPageTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")

    def test_404_page_renders(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_403_page_renders_for_wrong_role(self):
        make_user(self.school, Role.TEACHER, "tea1", must_change_password=False)
        self.client.login(username="tea1", password=DEFAULT_PASSWORD, school_code="alpha")
        response = self.client.get(reverse("core:dashboard-principal"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access denied", status_code=403)
