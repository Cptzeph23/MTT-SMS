from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit import actions
from apps.audit.services import record

from .models import User
from .services import reset_password


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "school",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone",
        )


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserEditForm
    add_form = UserCreationForm

    list_display = ("username", "get_full_name", "school", "role", "is_active", "must_change_password")
    list_filter = ("role", "school", "is_active", "must_change_password")
    list_select_related = ("school",)
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    ordering = ("school__name", "username")
    readonly_fields = ("last_login", "date_joined", "password_changed_at")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            "Access",
            {
                "fields": (
                    "school",
                    "role",
                    "must_change_password",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined", "password_changed_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "school",
                    "role",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    actions = ["reset_to_temporary_password"]

    def save_model(self, request, obj, form, change):
        previous_role = form.initial.get("role") if change and "role" in form.changed_data else None
        super().save_model(request, obj, form, change)
        if not change:
            record(
                action=actions.USER_CREATED,
                module=actions.MODULE_ACCOUNTS,
                actor=request.user,
                school=obj.school,
                obj=obj,
                new_value={"username": obj.username, "role": obj.role},
                request=request,
            )
        elif previous_role is not None:
            record(
                action=actions.USER_ROLE_CHANGED,
                module=actions.MODULE_ACCOUNTS,
                actor=request.user,
                school=obj.school,
                obj=obj,
                previous_value={"role": previous_role},
                new_value={"role": obj.role},
                request=request,
            )

    @admin.action(description="Reset selected users to a temporary password")
    def reset_to_temporary_password(self, request, queryset):
        for target in queryset.select_related("school"):
            try:
                temporary = reset_password(actor=request.user, user=target, request=request)
            except (PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{target.username}: {exc}", level=messages.ERROR)
            else:
                self.message_user(
                    request,
                    f"Temporary password for {target.username}: {temporary} "
                    "(shown once; the user must change it at first login).",
                    level=messages.SUCCESS,
                )
