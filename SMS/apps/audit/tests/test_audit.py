from django.contrib.auth import authenticate
from django.test import RequestFactory, TestCase

from apps.accounts.models import Role
from apps.audit import actions
from apps.audit.models import AuditLog
from apps.audit.services import record
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_user


class AuditRecordTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.user = make_user(self.school, Role.PRINCIPAL, "pa")

    def test_record_captures_actor_school_and_object(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.1.2.3")
        entry = record(
            action="test.action",
            module="testing",
            actor=self.user,
            obj=self.school,
            previous_value={"name": "Old"},
            new_value={"name": "New"},
            request=request,
        )
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.actor_label, "pa")
        self.assertEqual(entry.actor_role, "principal")
        self.assertEqual(entry.school, self.school)
        self.assertEqual(entry.object_type, "School")
        self.assertEqual(entry.object_id, str(self.school.pk))
        self.assertEqual(entry.ip_address, "10.1.2.3")
        self.assertEqual(entry.previous_value, {"name": "Old"})

    def test_record_without_actor(self):
        entry = record(action="test.action", module="testing")
        self.assertIsNone(entry.actor)
        self.assertIsNone(entry.school)

    def test_entries_are_immutable(self):
        entry = record(action="test.action", module="testing")
        entry.action = "changed"
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()

    def test_scoped_queryset_isolates_schools(self):
        other_school = make_school("beta")
        record(action="a", module="m", school=self.school)
        record(action="b", module="m", school=other_school)
        self.assertEqual(AuditLog.objects.for_user(self.user).count(), 1)


class AuthenticationAuditTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.user = make_user(self.school, Role.TEACHER, "tea1")

    def test_successful_login_is_recorded(self):
        self.assertTrue(
            self.client.login(username="tea1", password=DEFAULT_PASSWORD, school_code="alpha")
        )
        self.assertTrue(
            AuditLog.objects.filter(action=actions.LOGIN, actor=self.user).exists()
        )

    def test_failed_login_is_recorded_without_password(self):
        result = authenticate(username="ghost", password="secret-guess", school_code="alpha")
        self.assertIsNone(result)
        entry = AuditLog.objects.get(action=actions.LOGIN_FAILED)
        self.assertEqual(entry.object_repr, "ghost")
        self.assertEqual(entry.school, self.school)
        self.assertNotIn("secret-guess", str(entry.__dict__))

    def test_failed_login_with_unknown_school_is_recorded(self):
        authenticate(username="ghost", password="x", school_code="nowhere")
        entry = AuditLog.objects.get(action=actions.LOGIN_FAILED)
        self.assertIsNone(entry.school)
        self.assertEqual(entry.new_value, {"school_code": "nowhere"})

    def test_logout_is_recorded(self):
        self.client.login(username="tea1", password=DEFAULT_PASSWORD, school_code="alpha")
        self.client.logout()
        self.assertTrue(
            AuditLog.objects.filter(action=actions.LOGOUT, actor=self.user).exists()
        )
