"""API views for authentication and the current user's profile."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import PasswordChangeCompleted
from .serializers import ChangePasswordSerializer, MeSerializer, SchoolAwareTokenObtainPairSerializer


class SchoolAwareTokenObtainPairView(TokenObtainPairView):
    serializer_class = SchoolAwareTokenObtainPairSerializer
    # Accept browser-style form posts as well as JSON API requests.
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated, PasswordChangeCompleted]
    allow_password_change_pending = False

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated, PasswordChangeCompleted]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    allow_password_change_pending = True

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})
