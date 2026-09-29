"""Reusable web-view access control.

Server-side enforcement only. Hiding a menu item is never sufficient on its
own; every dashboard and module view must also use a mixin such as this one.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    """Restricts a view to one or more roles.

    Set `allowed_roles` to a tuple of `Role` values on the view class. A
    request from a user of any other role raises PermissionDenied (HTTP 403)
    rather than silently redirecting, so a user cannot reach another role's
    dashboard simply by typing its URL.
    """

    allowed_roles = ()

    def get(self, request, *args, **kwargs):
        self._check_role(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._check_role(request)
        return super().post(request, *args, **kwargs)

    def _check_role(self, request):
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not have access to this dashboard.")
