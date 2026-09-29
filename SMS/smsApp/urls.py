from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("dashboard/", views.DashboardRouterView.as_view(), name="dashboard"),
    path(
        "dashboard/super-admin/",
        views.SuperAdminDashboardView.as_view(),
        name="dashboard-super-admin",
    ),
    path(
        "dashboard/principal/",
        views.PrincipalDashboardView.as_view(),
        name="dashboard-principal",
    ),
    path(
        "dashboard/deputy-principal/",
        views.DeputyPrincipalDashboardView.as_view(),
        name="dashboard-deputy-principal",
    ),
    path("dashboard/finance/", views.FinanceDashboardView.as_view(), name="dashboard-finance"),
    path("dashboard/teacher/", views.TeacherDashboardView.as_view(), name="dashboard-teacher"),
    path("dashboard/parent/", views.ParentDashboardView.as_view(), name="dashboard-parent"),
]
