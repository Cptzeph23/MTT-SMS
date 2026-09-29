"""Root URL configuration."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("smsApp.urls")),
    path("api/v1/", include("apps.api.urls")),
]

handler403 = "smsApp.views.custom_403"
handler404 = "smsApp.views.custom_404"
handler500 = "smsApp.views.custom_500"