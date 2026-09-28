"""Phase 0 scaffold verification tests.

These tests confirm that the project layout, dependency files, environment
template and domain application skeletons exist as planned. They need no
database and no configured services.
"""
import importlib
from pathlib import Path

from django.test import SimpleTestCase

SMS_DIR = Path(__file__).resolve().parent.parent  # folder containing manage.py
REPO_ROOT = SMS_DIR

DOMAIN_APPS = {
    "accounts": "AccountsConfig",
    "schools": "SchoolsConfig",
    "people": "PeopleConfig",
    "academics": "AcademicsConfig",
    "assessments": "AssessmentsConfig",
    "attendance": "AttendanceConfig",
    "finance": "FinanceConfig",
    "reports": "ReportsConfig",
    "imports": "ImportsConfig",
    "notifications": "NotificationsConfig",
    "audit": "AuditConfig",
    "api": "ApiConfig",
}

REQUIRED_ENV_KEYS = {
    "DJANGO_SECRET_KEY",
    "DJANGO_DEBUG",
    "DJANGO_ALLOWED_HOSTS",
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_S3_ENDPOINT",
    "SUPABASE_PUBLIC_BUCKET",
    "SUPABASE_PRIVATE_BUCKET",
    "REDIS_URL",
    "CELERY_TASK_ALWAYS_EAGER",
    "SMS_PROVIDER",
    "JWT_ACCESS_MINUTES",
    "JWT_REFRESH_DAYS",
}


class ScaffoldLayoutTests(SimpleTestCase):
    def test_manage_py_is_in_sms_dir(self):
        self.assertTrue((SMS_DIR / "manage.py").is_file())

    def test_required_directories_exist(self):
        for path in (
            SMS_DIR / "apps",
            SMS_DIR / "templates",
            SMS_DIR / "static",
            REPO_ROOT / "requirements",
            REPO_ROOT / "docs",
        ):
            with self.subTest(path=str(path)):
                self.assertTrue(path.is_dir())

    def test_requirements_files_exist_and_list_core_stack(self):
        base = (REPO_ROOT / "requirements" / "base.txt").read_text()
        for package in (
            "Django",
            "djangorestframework",
            "djangorestframework-simplejwt",
            "psycopg",
            "django-storages",
            "celery",
            "redis",
            "reportlab",
            "openpyxl",
        ):
            with self.subTest(package=package):
                self.assertIn(package, base)
        for name in ("dev.txt", "prod.txt"):
            with self.subTest(file=name):
                text = (REPO_ROOT / "requirements" / name).read_text()
                self.assertIn("-r base.txt", text)

    def test_env_example_declares_required_keys(self):
        lines = (SMS_DIR / ".env.example").read_text().splitlines()
        declared = {
            line.split("=", 1)[0].strip()
            for line in lines
            if "=" in line and not line.lstrip().startswith("#")
        }
        self.assertEqual(REQUIRED_ENV_KEYS - declared, set())

    def test_env_example_contains_no_real_secrets(self):
        text = (SMS_DIR / ".env.example").read_text()
        self.assertNotIn("eyJ", text)  # JWT-style keys such as Supabase service keys

    def test_gitignore_protects_secrets_and_venv(self):
        entries = {
            line.strip()
            for line in (REPO_ROOT / ".gitignore").read_text().splitlines()
        }
        for required in (".env", ".venv/", "db.sqlite3", "__pycache__/"):
            with self.subTest(entry=required):
                self.assertIn(required, entries)


class DomainAppSkeletonTests(SimpleTestCase):
    def test_each_domain_app_config_is_importable_and_named_correctly(self):
        for label, class_name in DOMAIN_APPS.items():
            with self.subTest(app=label):
                module = importlib.import_module(f"apps.{label}.apps")
                config = getattr(module, class_name)
                self.assertEqual(config.name, f"apps.{label}")

    def test_each_domain_app_has_migrations_and_tests_packages(self):
        for label in DOMAIN_APPS:
            with self.subTest(app=label):
                base = SMS_DIR / "apps" / label
                self.assertTrue((base / "__init__.py").is_file())
                self.assertTrue((base / "migrations" / "__init__.py").is_file())
                self.assertTrue((base / "tests" / "__init__.py").is_file())
