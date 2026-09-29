"""Serializers for the authentication API."""
from django.contrib.auth import authenticate
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.services import change_password as change_password_service


class SchoolAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds an optional school_code, required for every role except Super Admin."""

    school_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        school_code = (attrs.get("school_code") or "").strip() or None
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
            "school_code": school_code,
        }
        request = self.context.get("request")
        if request is not None:
            authenticate_kwargs["request"] = request

        self.user = authenticate(**authenticate_kwargs)
        if self.user is None or not self.user.is_active:
            raise exceptions.AuthenticationFailed(
                "No active account found with the given credentials.",
                "no_active_account",
            )

        refresh = self.get_token(self.user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "must_change_password": self.user.must_change_password,
            "role": self.user.role,
        }


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def save(self, **kwargs):
        request = self.context["request"]
        change_password_service(
            user=request.user,
            new_password=self.validated_data["new_password"],
            request=request,
        )
        return request.user


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    school_id = serializers.IntegerField(allow_null=True)
    school_code = serializers.SerializerMethodField()
    must_change_password = serializers.BooleanField()

    def get_school_code(self, obj):
        return obj.school.code if obj.school_id else None
