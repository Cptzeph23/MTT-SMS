"""Cache-based protection against password guessing.

Failures are counted per client IP, school code and username. In production
the cache is Redis, so counts are shared between worker processes.
"""
import hashlib

from django.conf import settings
from django.core.cache import cache


def _key(ip, school_code, username):
    raw = "|".join(
        [ip or "-", (school_code or "-").strip().lower(), (username or "-").strip().lower()]
    )
    return "login-throttle:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def max_attempts():
    return getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)


def lockout_seconds():
    return getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)


def is_locked(ip, school_code, username):
    return cache.get(_key(ip, school_code, username), 0) >= max_attempts()


def register_failure(ip, school_code, username):
    """Record a failed attempt and return the number of failures so far."""
    key = _key(ip, school_code, username)
    if cache.add(key, 1, timeout=lockout_seconds()):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=lockout_seconds())
        return 1


def clear(ip, school_code, username):
    cache.delete(_key(ip, school_code, username))
