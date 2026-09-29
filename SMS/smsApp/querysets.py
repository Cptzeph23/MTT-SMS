"""Reusable queryset for models that belong to a school."""
from django.db import models


class SchoolQuerySet(models.QuerySet):
    """Adds school-level isolation helpers to a queryset.

    The model must expose a `school` foreign key.
    """

    def for_school(self, school):
        """Restrict to one school (instance or primary key)."""
        if school is None:
            return self.none()
        return self.filter(school=school)

    def for_user(self, user):
        """Restrict to the records the given user is allowed to see.

        Super Admin sees every school. Any other authenticated user only sees
        their own school. Anonymous users see nothing.
        """
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        if getattr(user, "is_super_admin", False):
            return self.all()
        school_id = getattr(user, "school_id", None)
        if school_id is None:
            return self.none()
        return self.filter(school_id=school_id)