from django.contrib import admin

from apps.audit import actions
from apps.audit.services import record

from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = {
                field: form.initial.get(field)
                for field in form.changed_data
                if field in form.initial
            }
        super().save_model(request, obj, form, change)
        current = {field: getattr(obj, field) for field in form.changed_data if hasattr(obj, field)}
        record(
            action=actions.SCHOOL_UPDATED if change else actions.SCHOOL_CREATED,
            module=actions.MODULE_SCHOOLS,
            actor=request.user,
            school=obj,
            obj=obj,
            previous_value=previous,
            new_value=current,
            request=request,
        )
