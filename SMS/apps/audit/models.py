from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from smsApp.querysets import SchoolQuerySet


class AuditLog(models.Model):
    """Immutable record of a sensitive operation."""

    school = models.ForeignKey(
        "schools.School",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor_label = models.CharField(max_length=150, blank=True)
    actor_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=60, db_index=True)
    module = models.CharField(max_length=60)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    previous_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    new_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SchoolQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "created_at"], name="audit_school_created_idx"),
            models.Index(fields=["module", "action"], name="audit_module_action_idx"),
        ]

    def __str__(self):
        stamp = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        return f"{stamp} {self.action} {self.object_repr}".strip()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit log entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")
