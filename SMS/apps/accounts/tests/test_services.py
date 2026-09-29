from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Role
from apps.accounts.services import (
    change_password,
    create_user,
    generate_temporary_password,
    reset_password,
)
from apps.audit import actions
from apps.audit.models import AuditLog
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user

STRONG_PASSWORD = "Vq7#mLp29-Xz"


class TemporaryPasswordTests(SimpleTestCase):
    def test_length_and_character_classes(self):
        for _ in range(50):
            password = generate_temporary_password()
            self.assertEqual(len(password), 12)
            self.assertTrue(any(c.islower() for c in password))
            self.assertTrue(any(c.isupper() for c in password))
            self.assertTrue(any(c.isdigit() for c in password))

    def test_avoids_confusing_characters(self):
        for _ in range(50):
            password = generate_temporary_password()
            for char in "lIO01":
                self.assertNotIn(char, password)

    def test_passwords_are_unique(self):
        self.assertEqual(len({generate_temporary_password() for _ in range(30)}), 30)

    def test_rejects_short_length(self):
        with self.assertRaises(ValueError):
            generate_temporary_password(6)


class CreateUserServiceTests(TestCase):
    def setUp(self):
        self.school_a = make_school("alpha")
        self.school_b = make_school("beta")
        self.admin = make_super_admin("root")
        self.principal = make_user(self.school_a, Role.PRINCIPAL, "pa")
        self.teacher = make_user(self.school_a, Role.TEACHER, "ta")

    def test_principal_creates_teacher_in_own_school(self):
        user, temporary = create_user(
            actor=self.principal,
            school=self.school_a,
            username="tea9",
            role=Role.TEACHER,
            first_name="Amina",
            last_name="Otieno",
        )
        self.assertEqual(user.school, self.school_a)
        self.assertEqual(user.role, Role.TEACHER)
        self.assertTrue(user.must_change_password)
        self.assertNotEqual(user.password, temporary)
        self.assertTrue(user.check_password(temporary))

    def test_principal_cannot_create_principal(self):
        with self.assertRaises(PermissionDenied):
            create_user(
                actor=self.principal, school=self.school_a, username="p2", role=Role.PRINCIPAL
            )

    def test_principal_cannot_create_in_other_school(self):
        with self.assertRaises(PermissionDenied):
            create_user(
                actor=self.principal, school=self.school_b, username="t2", role=Role.TEACHER
            )

    def test_teacher_cannot_create_users(self):
        with self.assertRaises(PermissionDenied):
            create_user(
                actor=self.teacher, school=self.school_a, username="t2", role=Role.PARENT
            )

    def test_super_admin_creates_principal_in_any_school(self):
        user, _ = create_user(
            actor=self.admin, school=self.school_b, username="pb", role=Role.PRINCIPAL
        )
        self.assertEqual(user.school, self.school_b)

    def test_super_admin_cannot_create_school_user_without_school(self):
        with self.assertRaises(ValidationError):
            create_user(actor=self.admin, school=None, username="x1", role=Role.TEACHER)

    def test_duplicate_username_in_same_school_is_rejected(self):
        create_user(actor=self.principal, school=self.school_a, username="dup", role=Role.PARENT)
        with self.assertRaises(ValidationError):
            create_user(actor=self.principal, school=self.school_a, username="DUP", role=Role.PARENT)

    def test_same_username_allowed_in_other_school(self):
        create_user(actor=self.admin, school=self.school_a, username="adm1", role=Role.PARENT)
        user, _ = create_user(
            actor=self.admin, school=self.school_b, username="adm1", role=Role.PARENT
        )
        self.assertEqual(user.school, self.school_b)

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_user(actor=self.admin, school=self.school_a, username="x", role="janitor")

    def test_creation_is_audited_without_password(self):
        user, temporary = create_user(
            actor=self.principal, school=self.school_a, username="aud1", role=Role.TEACHER
        )
        entry = AuditLog.objects.get(action=actions.USER_CREATED, object_id=str(user.pk))
        self.assertEqual(entry.actor, self.principal)
        self.assertEqual(entry.school, self.school_a)
        self.assertEqual(entry.new_value["role"], "teacher")
        self.assertNotIn(temporary, str(entry.new_value))
        self.assertNotIn("password", entry.new_value)


class ResetPasswordServiceTests(TestCase):
    def setUp(self):
        self.school_a = make_school("alpha")
        self.school_b = make_school("beta")
        self.principal = make_user(self.school_a, Role.PRINCIPAL, "pa")
        self.other_principal = make_user(self.school_a, Role.PRINCIPAL, "pa2")
        self.teacher = make_user(self.school_a, Role.TEACHER, "ta")
        self.foreign_teacher = make_user(self.school_b, Role.TEACHER, "tb")

    def test_principal_resets_teacher_password(self):
        temporary = reset_password(actor=self.principal, user=self.teacher)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.must_change_password)
        self.assertTrue(self.teacher.check_password(temporary))
        self.assertFalse(self.teacher.check_password(DEFAULT_PASSWORD))

    def test_reset_is_audited(self):
        reset_password(actor=self.principal, user=self.teacher)
        entry = AuditLog.objects.get(action=actions.PASSWORD_RESET)
        self.assertEqual(entry.actor, self.principal)
        self.assertEqual(entry.object_id, str(self.teacher.pk))

    def test_principal_cannot_reset_user_of_other_school(self):
        with self.assertRaises(PermissionDenied):
            reset_password(actor=self.principal, user=self.foreign_teacher)

    def test_principal_cannot_reset_own_password(self):
        with self.assertRaises(PermissionDenied):
            reset_password(actor=self.principal, user=self.principal)

    def test_principal_cannot_reset_another_principal(self):
        with self.assertRaises(PermissionDenied):
            reset_password(actor=self.principal, user=self.other_principal)

    def test_teacher_cannot_reset_passwords(self):
        parent = make_user(self.school_a, Role.PARENT, "par1")
        with self.assertRaises(PermissionDenied):
            reset_password(actor=self.teacher, user=parent)

    def test_super_admin_can_reset_any_school_user(self):
        admin = make_super_admin("root")
        temporary = reset_password(actor=admin, user=self.foreign_teacher)
        self.foreign_teacher.refresh_from_db()
        self.assertTrue(self.foreign_teacher.check_password(temporary))


class ChangePasswordServiceTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.user = make_user(
            self.school, Role.TEACHER, "tea1", must_change_password=True
        )

    def test_change_password_clears_first_login_flag(self):
        change_password(user=self.user, new_password=STRONG_PASSWORD)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertIsNotNone(self.user.password_changed_at)
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))

    def test_same_password_is_rejected(self):
        with self.assertRaises(ValidationError):
            change_password(user=self.user, new_password=DEFAULT_PASSWORD)
        self.user.refresh_from_db()
        self.assertTrue(self.user.must_change_password)

    def test_weak_password_is_rejected(self):
        for weak in ("password123", "12345678901", "short1A"):
            with self.subTest(password=weak), self.assertRaises(ValidationError):
                change_password(user=self.user, new_password=weak)

    def test_change_is_audited_without_password(self):
        change_password(user=self.user, new_password=STRONG_PASSWORD)
        entry = AuditLog.objects.get(action=actions.PASSWORD_CHANGED)
        self.assertEqual(entry.actor, self.user)
        self.assertNotIn(STRONG_PASSWORD, str(entry.__dict__))
