"""Reusable DRF permission classes."""
from rest_framework.permissions import BasePermission


class PasswordChangeCompleted(BasePermission):
    """Blocks API access until a temporary password has been replaced.

    Views that must stay reachable during that period (the change-password
    endpoint itself) set `allow_password_change_pending = True`.
    """

    message = "You must change your temporary password before continuing."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True  # authentication is enforced by IsAuthenticated
        if not getattr(user, "must_change_password", False):
            return True
        return bool(getattr(view, "allow_password_change_pending", False))


class RoleAllowed(BasePermission):
    """Restricts a view to the roles listed in `view.allowed_roles`."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        allowed = getattr(view, "allowed_roles", None)
        if allowed is None:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in allowed)
