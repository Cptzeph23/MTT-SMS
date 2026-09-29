from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Role, User
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user


class UserModelTests(TestCase):
    def setUp(self):
        self.school_a = make_school("alpha")
        self.school_b = make_school("beta")

    def test_create_superuser_has_platform_defaults(self):
        admin = make_super_admin("root")
        self.assertEqual(admin.role, Role.SUPER_ADMIN)
        self.assertIsNone(admin.school)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertFalse(admin.must_change_password)
        self.assertTrue(admin.is_super_admin)

    def test_new_school_users_must_change_password_by_default(self):
        user = User.objects.create_user(
            "t1", DEFAULT_PASSWORD, school=self.school_a, role=Role.TEACHER
        )
        self.assertTrue(user.must_change_password)

    def test_create_user_requires_a_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("t1", DEFAULT_PASSWORD, school=self.school_a)

    def test_password_is_hashed(self):
        user = make_user(self.school_a, Role.TEACHER, "t1")
        self.assertNotEqual(user.password, DEFAULT_PASSWORD)
        self.assertTrue(user.check_password(DEFAULT_PASSWORD))

    def test_clean_rejects_school_role_without_school(self):
        user = User(username="t1", role=Role.TEACHER)
        with self.assertRaises(ValidationError) as ctx:
            user.clean()
        self.assertIn("school", ctx.exception.message_dict)

    def test_clean_rejects_super_admin_with_school(self):
        user = User(username="root", role=Role.SUPER_ADMIN, school=self.school_a)
        with self.assertRaises(ValidationError) as ctx:
            user.clean()
        self.assertIn("school", ctx.exception.message_dict)

    def test_database_rejects_school_role_without_school(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(username="t1", role=Role.TEACHER, password="x")

    def test_database_rejects_super_admin_with_school(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(
                username="root", role=Role.SUPER_ADMIN, school=self.school_a, password="x"
            )

    def test_same_username_allowed_in_different_schools(self):
        make_user(self.school_a, Role.PARENT, "ADM/2026/001")
        make_user(self.school_b, Role.PARENT, "ADM/2026/001")
        self.assertEqual(User.objects.filter(username="ADM/2026/001").count(), 2)

    def test_username_unique_within_school_ignoring_case(self):
        make_user(self.school_a, Role.PARENT, "adm001")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_user(self.school_a, Role.PARENT, "ADM001")

    def test_platform_usernames_are_unique_ignoring_case(self):
        make_super_admin("root")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_super_admin("ROOT")

    def test_username_validator_allows_slashes_and_rejects_spaces(self):
        good = User(username="ADM/2026/001", role=Role.PARENT, school=self.school_a)
        good.full_clean(exclude=["password"])
        bad = User(username="has space", role=Role.PARENT, school=self.school_a)
        with self.assertRaises(ValidationError) as ctx:
            bad.full_clean(exclude=["password"])
        self.assertIn("username", ctx.exception.message_dict)


class UserScopingTests(TestCase):
    def setUp(self):
        self.school_a = make_school("alpha")
        self.school_b = make_school("beta")
        self.admin = make_super_admin("root")
        self.principal_a = make_user(self.school_a, Role.PRINCIPAL, "pa")
        self.teacher_a = make_user(self.school_a, Role.TEACHER, "ta")
        self.principal_b = make_user(self.school_b, Role.PRINCIPAL, "pb")

    def test_super_admin_sees_all_users(self):
        self.assertEqual(User.objects.for_user(self.admin).count(), 4)

    def test_school_user_sees_only_own_school(self):
        visible = set(User.objects.for_user(self.principal_a).values_list("username", flat=True))
        self.assertEqual(visible, {"pa", "ta"})

    def test_anonymous_sees_nothing(self):
        self.assertEqual(User.objects.for_user(AnonymousUser()).count(), 0)

    def test_for_school_none_returns_nothing(self):
        self.assertEqual(User.objects.for_school(None).count(), 0)

    def test_for_school_filters(self):
        self.assertEqual(User.objects.for_school(self.school_b).count(), 1)
