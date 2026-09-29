from django.contrib.auth import authenticate
from django.test import TestCase

from apps.accounts.backends import SchoolScopedBackend
from apps.accounts.models import Role
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user


class SchoolScopedBackendTests(TestCase):
    def setUp(self):
        self.school_a = make_school("alpha")
        self.school_b = make_school("beta")
        self.teacher = make_user(self.school_a, Role.TEACHER, "Tea01")
        self.admin = make_super_admin("root")

    def login(self, username, password=DEFAULT_PASSWORD, school_code=None):
        credentials = {"username": username, "password": password}
        if school_code is not None:
            credentials["school_code"] = school_code
        return authenticate(**credentials)

    def test_valid_school_login(self):
        self.assertEqual(self.login("Tea01", school_code="alpha"), self.teacher)

    def test_username_and_school_code_are_case_insensitive(self):
        self.assertEqual(self.login("tea01", school_code="ALPHA"), self.teacher)

    def test_wrong_password_fails(self):
        self.assertIsNone(self.login("Tea01", "wrong-password-1", "alpha"))

    def test_wrong_school_fails(self):
        self.assertIsNone(self.login("Tea01", school_code="beta"))

    def test_unknown_school_fails(self):
        self.assertIsNone(self.login("Tea01", school_code="nope"))

    def test_school_user_cannot_use_platform_login(self):
        self.assertIsNone(self.login("Tea01"))

    def test_super_admin_uses_platform_login(self):
        self.assertEqual(self.login("root"), self.admin)

    def test_super_admin_cannot_use_school_login(self):
        self.assertIsNone(self.login("root", school_code="alpha"))

    def test_inactive_user_cannot_login(self):
        make_user(self.school_a, Role.TEACHER, "gone", is_active=False)
        self.assertIsNone(self.login("gone", school_code="alpha"))

    def test_inactive_school_blocks_login(self):
        self.school_a.is_active = False
        self.school_a.save()
        self.assertIsNone(self.login("Tea01", school_code="alpha"))

    def test_same_username_resolves_to_the_right_school(self):
        other = make_user(self.school_b, Role.TEACHER, "Tea01")
        self.assertEqual(self.login("Tea01", school_code="beta"), other)
        self.assertEqual(self.login("Tea01", school_code="alpha"), self.teacher)

    def test_missing_credentials_return_none(self):
        backend = SchoolScopedBackend()
        self.assertIsNone(backend.authenticate(None, username=None, password="x"))
        self.assertIsNone(backend.authenticate(None, username="Tea01", password=None))

    def test_get_user_returns_active_user(self):
        self.assertEqual(SchoolScopedBackend().get_user(self.teacher.pk), self.teacher)

    def test_get_user_rejects_user_of_deactivated_school(self):
        self.school_a.is_active = False
        self.school_a.save()
        self.assertIsNone(SchoolScopedBackend().get_user(self.teacher.pk))

    def test_get_user_rejects_inactive_user_and_unknown_id(self):
        self.teacher.is_active = False
        self.teacher.save()
        backend = SchoolScopedBackend()
        self.assertIsNone(backend.get_user(self.teacher.pk))
        self.assertIsNone(backend.get_user(999999))
