"""Enforces the first-login password change.

A user with must_change_password set can only reach the change-password
page, the logout page and static/media files. Every other URL redirects
back to the change-password page, so the requirement cannot be bypassed
by navigating directly to another page.
"""
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse

EXEMPT_VIEW_NAMES = {"accounts:change-password", "accounts:logout"}


class PasswordChangeEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            if request.path.startswith(("/static/", "/media/")):
                return self.get_response(request)
            try:
                view_name = resolve(request.path_info).view_name
            except Resolver404:
                view_name = None
            if view_name not in EXEMPT_VIEW_NAMES:
                return redirect(reverse("accounts:change-password"))
        return self.get_response(request)
