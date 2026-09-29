"""Tests for the JWT authentication API."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from smsApp.testing import DEFAULT_PASSWORD, make_school, make_super_admin, make_user

NEW_STRONG_PASSWORD = "Vq7#mLp29-Xz"


class TokenObtainTests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.teacher = make_user(self.school, Role.TEACHER, "tea1", must_change_password=False)
        self.admin = make_super_admin("root")

    def test_school_user_obtains_token_with_school_code(self):
        response = self.client.post(
            reverse("api:token-obtain"),
            {"username": "tea1", "password": DEFAULT_PASSWORD, "school_code": "alpha"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["role"], "teacher")
        self.assertFalse(response.data["must_change_password"])

    def test_wrong_school_code_is_rejected(self):
        response = self.client.post(
            reverse("api:token-obtain"),
            {"username": "tea1", "password": DEFAULT_PASSWORD, "school_code": "beta"},
        )
        self.assertEqual(response.status_code, 401)

    def test_super_admin_obtains_token_without_school_code(self):
        response = self.client.post(
            reverse("api:token-obtain"), {"username": "root", "password": DEFAULT_PASSWORD}
        )
        self.assertEqual(response.status_code, 200)

    def test_must_change_password_flag_is_reported(self):
        make_user(self.school, Role.TEACHER, "newbie", must_change_password=True)
        response = self.client.post(
            reverse("api:token-obtain"),
            {"username": "newbie", "password": DEFAULT_PASSWORD, "school_code": "alpha"},
        )
        self.assertTrue(response.data["must_change_password"])


class MeAndChangePasswordAPITests(TestCase):
    def setUp(self):
        self.school = make_school("alpha")
        self.pending_user = make_user(
            self.school, Role.TEACHER, "newbie", must_change_password=True
        )
        self.active_user = make_user(
            self.school, Role.TEACHER, "tea1", must_change_password=False
        )

    def _token_for(self, username):
        response = self.client.post(
            reverse("api:token-obtain"),
            {"username": username, "password": DEFAULT_PASSWORD, "school_code": "alpha"},
        )
        return response.data["access"]

    def test_pending_user_is_blocked_from_me_endpoint(self):
        token = self._token_for("newbie")
        response = self.client.get(
            reverse("api:me"), HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 403)

    def test_pending_user_can_change_password_then_reach_me(self):
        token = self._token_for("newbie")
        auth_header = f"Bearer {token}"
        response = self.client.post(
            reverse("api:change-password"),
            {"current_password": DEFAULT_PASSWORD, "new_password": NEW_STRONG_PASSWORD},
            HTTP_AUTHORIZATION=auth_header,
        )
        self.assertEqual(response.status_code, 200)
        me_response = self.client.get(reverse("api:me"), HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(me_response.status_code, 200)
        self.assertFalse(me_response.data["must_change_password"])

    def test_wrong_current_password_is_rejected(self):
        token = self._token_for("newbie")
        response = self.client.post(
            reverse("api:change-password"),
            {"current_password": "wrong", "new_password": NEW_STRONG_PASSWORD},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_active_user_sees_own_profile(self):
        token = self._token_for("tea1")
        response = self.client.get(reverse("api:me"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "tea1")
        self.assertEqual(response.data["school_code"], "alpha")

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(reverse("api:me"))
        self.assertEqual(response.status_code, 401)
