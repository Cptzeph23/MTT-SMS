from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts import throttle


@override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_not_locked_initially(self):
        self.assertFalse(throttle.is_locked("1.1.1.1", "alpha", "tea1"))

    def test_locks_after_max_failures(self):
        for _ in range(2):
            throttle.register_failure("1.1.1.1", "alpha", "tea1")
        self.assertFalse(throttle.is_locked("1.1.1.1", "alpha", "tea1"))
        throttle.register_failure("1.1.1.1", "alpha", "tea1")
        self.assertTrue(throttle.is_locked("1.1.1.1", "alpha", "tea1"))

    def test_failure_count_increments(self):
        self.assertEqual(throttle.register_failure("1.1.1.1", "alpha", "tea1"), 1)
        self.assertEqual(throttle.register_failure("1.1.1.1", "alpha", "tea1"), 2)

    def test_counts_are_independent_per_user_school_and_ip(self):
        for _ in range(3):
            throttle.register_failure("1.1.1.1", "alpha", "tea1")
        self.assertTrue(throttle.is_locked("1.1.1.1", "alpha", "TEA1"))
        self.assertFalse(throttle.is_locked("1.1.1.1", "alpha", "tea2"))
        self.assertFalse(throttle.is_locked("1.1.1.1", "beta", "tea1"))
        self.assertFalse(throttle.is_locked("2.2.2.2", "alpha", "tea1"))

    def test_clear_resets_the_counter(self):
        for _ in range(3):
            throttle.register_failure("1.1.1.1", "alpha", "tea1")
        throttle.clear("1.1.1.1", "alpha", "tea1")
        self.assertFalse(throttle.is_locked("1.1.1.1", "alpha", "tea1"))
