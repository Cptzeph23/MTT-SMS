from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "school",
        "actor_label",
        "actor_role",
        "module",
        "action",
        "object_type",
        "object_repr",
    )
    list_filter = ("module", "action", "school")
    search_fields = ("actor_label", "object_repr", "object_id")
    date_hierarchy = "created_at"
    list_select_related = ("school",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
