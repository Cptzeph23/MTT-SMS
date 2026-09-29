from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "api"

urlpatterns = [
    path("token/", views.SchoolAwareTokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", views.MeAPIView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordAPIView.as_view(), name="change-password"),
]
