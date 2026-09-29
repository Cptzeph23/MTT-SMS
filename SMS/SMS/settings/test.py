"""Automated test settings. Uses in-memory SQLite and local storage only."""
import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

SECRET_KEY = "test-only-secret-key-for-automated-tests-0123456789-abcdefghijklmnop"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": True,
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sms-test",
    }
}

MEDIA_ROOT = Path(tempfile.gettempdir()) / "sms-test-media"

# Tests must never reach external services.
SUPABASE_URL = ""
SUPABASE_S3_ENDPOINT = ""
SUPABASE_S3_ACCESS_KEY_ID = ""
SUPABASE_S3_SECRET_ACCESS_KEY = ""

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900
TRUSTED_PROXY_COUNT = 0

LOGGING["root"]["level"] = "CRITICAL"  # noqa: F405