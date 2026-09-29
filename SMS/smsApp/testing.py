"""Helpers shared by the automated tests of every app."""
from apps.accounts.models import User
from apps.schools.models import School

DEFAULT_PASSWORD = "Str0ng-Test-Pass-91"


def make_school(code="alpha", name=None, **kwargs):
    return School.objects.create(code=code, name=name or code.title(), **kwargs)


def make_user(school, role, username, password=DEFAULT_PASSWORD, **kwargs):
    kwargs.setdefault("must_change_password", False)
    return User.objects.create_user(
        username, password, school=school, role=role, **kwargs
    )


def make_super_admin(username="root", password=DEFAULT_PASSWORD):
    return User.objects.create_superuser(username, password)
