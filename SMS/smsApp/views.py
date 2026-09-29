"""Dashboard router and shared error views."""
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from apps.accounts.models import Role

from .mixins import RoleRequiredMixin

ROLE_DASHBOARD_URL_NAMES = {
    Role.SUPER_ADMIN: "core:dashboard-super-admin",
    Role.PRINCIPAL: "core:dashboard-principal",
    Role.DEPUTY_PRINCIPAL: "core:dashboard-deputy-principal",
    Role.FINANCE_ADMIN: "core:dashboard-finance",
    Role.TEACHER: "core:dashboard-teacher",
    Role.PARENT: "core:dashboard-parent",
}


class DashboardRouterView(RoleRequiredMixin, TemplateView):
    """The single entry point every login redirects to.

    The user never chooses a dashboard; this view sends each role straight to
    its own dashboard, so RBAC alone decides where a user lands.
    """

    allowed_roles = tuple(Role.values)

    def get(self, request, *args, **kwargs):
        url_name = ROLE_DASHBOARD_URL_NAMES.get(request.user.role)
        if url_name is None:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("No dashboard is configured for this role.")
        return redirect(url_name)


class SuperAdminDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.SUPER_ADMIN,)
    template_name = "core/dashboard_super_admin.html"


class PrincipalDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.PRINCIPAL,)
    template_name = "core/dashboard_principal.html"


class DeputyPrincipalDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.DEPUTY_PRINCIPAL,)
    template_name = "core/dashboard_deputy_principal.html"


class FinanceDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.FINANCE_ADMIN,)
    template_name = "core/dashboard_finance.html"


class TeacherDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.TEACHER,)
    template_name = "core/dashboard_teacher.html"


class ParentDashboardView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.PARENT,)
    template_name = "core/dashboard_parent.html"


def custom_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def custom_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    return render(request, "errors/500.html", status=500)
