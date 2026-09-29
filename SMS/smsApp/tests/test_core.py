"""Tests for the shared core: settings, storage, navigation and helpers."""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from storages.backends.s3 import S3Storage

from apps.accounts.models import Role
from smsApp.context_processors import navigation as navigation_processor
from smsApp.navigation import items_for_role
from smsApp.storage import private_storage, public_storage, s3_configured
from smsApp.testing import make_school, make_user
from smsApp.utils import get_client_ip

S3_SETTINGS = {
    "SUPABASE_URL": "https://abcdef.supabase.co",
    "SUPABASE_S3_ENDPOINT": "https://abcdef.supabase.co/storage/v1/s3",
    "SUPABASE_S3_ACCESS_KEY_ID": "test-key-id",
    "SUPABASE_S3_SECRET_ACCESS_KEY": "test-secret",
    "SUPABASE_S3_REGION": "us-east-1",
    "SUPABASE_PUBLIC_BUCKET": "sms-public",
    "SUPABASE_PRIVATE_BUCKET": "sms-private",
    "SUPABASE_SIGNED_URL_SECONDS": 120,
}


class ProjectConfigurationTests(TestCase):
    def test_uses_isolated_test_database(self):
        self.assertIn("sqlite3", settings.DATABASES["default"]["ENGINE"])

    def test_custom_user_model_is_active(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_project_apps_are_installed(self):
        for app in ("smsApp", "apps.schools", "apps.accounts", "apps.audit"):
            with self.subTest(app=app):
                self.assertIn(app, settings.INSTALLED_APPS)

    def test_system_checks_pass(self):
        call_command("check", verbosity=0)

    def test_no_model_changes_are_missing_migrations(self):
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)


class ClientIpTests(SimpleTestCase):
    def test_uses_remote_addr_by_default(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_uses_forwarded_entry_added_by_trusted_proxy(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="9.9.9.9, 5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "5.6.7.8")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_falls_back_when_forwarded_chain_is_too_short(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_invalid_address_returns_none(self):
        request = RequestFactory().get("/", REMOTE_ADDR="not-an-ip")
        self.assertIsNone(get_client_ip(request))

    def test_no_request_returns_none(self):
        self.assertIsNone(get_client_ip(None))


class NavigationTests(TestCase):
    def test_every_role_sees_the_dashboard(self):
        for role in Role:
            with self.subTest(role=role.value):
                labels = [item.label for item in items_for_role(role.value)]
                self.assertIn("Dashboard", labels)

    def test_unknown_role_sees_nothing(self):
        self.assertEqual(items_for_role("janitor"), [])

    def test_context_processor_for_anonymous_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertEqual(navigation_processor(request), {})

    def test_context_processor_for_authenticated_user(self):
        school = make_school("alpha")
        request = RequestFactory().get("/")
        request.user = make_user(school, Role.TEACHER, "tea1")
        context = navigation_processor(request)
        self.assertEqual(context["current_school"], school)
        self.assertTrue(context["nav_items"])


class StorageTests(SimpleTestCase):
    @override_settings(
        SUPABASE_S3_ENDPOINT="", SUPABASE_S3_ACCESS_KEY_ID="", SUPABASE_S3_SECRET_ACCESS_KEY=""
    )
    def test_falls_back_to_local_disk_without_credentials(self):
        self.assertFalse(s3_configured())
        self.assertIsInstance(public_storage(), FileSystemStorage)
        self.assertIsInstance(private_storage(), FileSystemStorage)

    @override_settings(**S3_SETTINGS)
    def test_public_storage_uses_public_bucket_and_stable_urls(self):
        self.assertTrue(s3_configured())
        storage = public_storage()
        self.assertIsInstance(storage, S3Storage)
        self.assertEqual(storage.bucket_name, "sms-public")
        self.assertFalse(storage.querystring_auth)
        self.assertEqual(
            storage.custom_domain, "abcdef.supabase.co/storage/v1/object/public/sms-public"
        )

    @override_settings(**S3_SETTINGS)
    def test_private_storage_uses_signed_urls(self):
        storage = private_storage()
        self.assertIsInstance(storage, S3Storage)
        self.assertEqual(storage.bucket_name, "sms-private")
        self.assertTrue(storage.querystring_auth)
        self.assertEqual(storage.querystring_expire, 120)
        self.assertFalse(storage.file_overwrite)
