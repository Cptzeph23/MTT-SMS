from django.db import models

from smsApp.models import TimeStampedModel


class School(TimeStampedModel):
    """A school (tenant). Branding and configuration are added in Phase 2."""

    name = models.CharField(max_length=200)
    code = models.SlugField(
        max_length=30,
        unique=True,
        help_text="Short unique code used in the login address, for example 'stmarys'.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().lower()
        super().save(*args, **kwargs)
