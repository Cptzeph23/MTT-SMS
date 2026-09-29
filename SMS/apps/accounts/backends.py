"""School-scoped authentication backend.

Users log in with a school code plus their username. Super Admin accounts have
no school and log in without a school code. A school user can never sign in
through the platform login and vice versa.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from apps.schools.models import School


class SchoolScopedBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, school_code=None, **kwargs):
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)
        if username is None or password is None:
            return None
        username = str(username).strip()

        queryset = user_model._default_manager.select_related("school")
        if school_code:
            school = School.objects.filter(
                code__iexact=str(school_code).strip(), is_active=True
            ).first()
            if school is None:
                user_model().set_password(password)  # equalise timing
                return None
            queryset = queryset.filter(school=school)
        else:
            queryset = queryset.filter(school__isnull=True)

        try:
            user = queryset.get(username__iexact=username)
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            user_model().set_password(password)  # equalise timing
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            user = user_model._default_manager.select_related("school").get(pk=user_id)
        except (user_model.DoesNotExist, ValueError, TypeError):
            return None
        if not self.user_can_authenticate(user):
            return None
        if user.school_id is not None and not user.school.is_active:
            return None
        return user
