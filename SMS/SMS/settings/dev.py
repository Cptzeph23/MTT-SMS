"""Local development settings."""
from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS as _BASE_ALLOWED_HOSTS
from .base import SECRET_KEY as _BASE_SECRET_KEY
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
SECRET_KEY = _BASE_SECRET_KEY or "dev-only-insecure-key-never-use-in-production"
ALLOWED_HOSTS = _BASE_ALLOWED_HOSTS or ["localhost", "127.0.0.1", "[::1]"]
