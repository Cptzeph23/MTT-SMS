"""Abstract base models shared by every domain app."""
from django.db import models

from .querysets import SchoolQuerySet


class TimeStampedModel(models.Model):
    """Adds creation and modification timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SchoolScopedModel(TimeStampedModel):
    """Base for every record owned by a school.

    Always query through `Model.objects.for_user(request.user)` or
    `Model.objects.for_school(school)` so data never leaks across schools.
    """

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    objects = SchoolQuerySet.as_manager()

    class Meta:
        abstract = True
