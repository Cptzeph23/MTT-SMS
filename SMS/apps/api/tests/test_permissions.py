from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.accounts.models import Role
from apps.api.permissions import PasswordChangeCompleted, RoleAllowed
from smsApp.testing import make_school, make_user


class PasswordChangeCompletedTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.permission = PasswordChangeCompleted()

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_anonymous_is_deferred_to_authentication(self):
        self.assertTrue(
            self.permission.has_permission(self.request_for(AnonymousUser()), SimpleNamespace())
        )

    def test_user_with_pending_change_is_blocked(self):
        user = make_user(self.school, Role.TEACHER, "t1", must_change_password=True)
        self.assertFalse(self.permission.has_permission(self.request_for(user), SimpleNamespace()))

    def test_pending_user_may_reach_flagged_view(self):
        user = make_user(self.school, Role.TEACHER, "t1", must_change_password=True)
        view = SimpleNamespace(allow_password_change_pending=True)
        self.assertTrue(self.permission.has_permission(self.request_for(user), view))

    def test_completed_user_is_allowed(self):
        user = make_user(self.school, Role.TEACHER, "t1", must_change_password=False)
        self.assertTrue(self.permission.has_permission(self.request_for(user), SimpleNamespace()))


class RoleAllowedTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.permission = RoleAllowed()
        self.view = SimpleNamespace(allowed_roles=(Role.PRINCIPAL.value, Role.DEPUTY_PRINCIPAL.value))

    def test_allowed_role_passes(self):
        user = make_user(self.school, Role.PRINCIPAL, "p1")
        self.assertTrue(self.permission.has_permission(SimpleNamespace(user=user), self.view))

    def test_other_role_is_blocked(self):
        user = make_user(self.school, Role.FINANCE_ADMIN, "f1")
        self.assertFalse(self.permission.has_permission(SimpleNamespace(user=user), self.view))

    def test_anonymous_is_blocked(self):
        self.assertFalse(
            self.permission.has_permission(SimpleNamespace(user=AnonymousUser()), self.view)
        )

    def test_view_without_restriction_is_open(self):
        user = make_user(self.school, Role.PARENT, "par1")
        self.assertTrue(self.permission.has_permission(SimpleNamespace(user=user), SimpleNamespace()))
