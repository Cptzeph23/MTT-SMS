"""Account business rules shared by the web interface and the API."""
import secrets

from django.contrib.auth import password_validation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit import actions
from apps.audit.services import record

from .models import Role, User

_LOWER = "abcdefghijkmnopqrstuvwxyz"
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGITS = "23456789"
_ALPHABET = _LOWER + _UPPER + _DIGITS


def _values(*roles):
    return frozenset(role.value for role in roles)


# Which roles each actor role may create and reset.
MANAGEABLE_ROLES = {
    Role.SUPER_ADMIN.value: _values(
        Role.PRINCIPAL,
        Role.DEPUTY_PRINCIPAL,
        Role.FINANCE_ADMIN,
        Role.TEACHER,
        Role.PARENT,
    ),
    Role.PRINCIPAL.value: _values(
        Role.DEPUTY_PRINCIPAL, Role.FINANCE_ADMIN, Role.TEACHER, Role.PARENT
    ),
}


def generate_temporary_password(length=12):
    """Return a random password without easily confused characters."""
    if length < 8:
        raise ValueError("Temporary passwords must be at least 8 characters long.")
    chars = [
        secrets.choice(_LOWER),
        secrets.choice(_UPPER),
        secrets.choice(_DIGITS),
    ]
    chars += [secrets.choice(_ALPHABET) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _assert_can_manage(actor, *, school_id, role):
    """Raise PermissionDenied unless the actor may manage this role and school."""
    if actor is None or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication is required.")
    allowed = MANAGEABLE_ROLES.get(actor.role, frozenset())
    if role not in allowed:
        raise PermissionDenied("You do not have permission to manage this type of account.")
    if actor.role != Role.SUPER_ADMIN and actor.school_id != school_id:
        raise PermissionDenied("You cannot manage accounts of another school.")


@transaction.atomic
def create_user(
    *,
    actor,
    school,
    username,
    role,
    first_name="",
    last_name="",
    email="",
    phone="",
    request=None,
):
    """Create a school account with a temporary password.

    Returns (user, temporary_password). The temporary password exists only in
    the return value: show it once to the administrator and never store it.
    """
    try:
        role_value = Role(role).value
    except ValueError:
        raise ValidationError({"role": "Select a valid role."}) from None

    _assert_can_manage(
        actor, school_id=school.pk if school is not None else None, role=role_value
    )

    temporary_password = generate_temporary_password()
    user = User(
        username=str(username).strip(),
        school=school,
        role=role_value,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=User.objects.normalize_email(email),
        phone=phone.strip(),
        must_change_password=True,
    )
    user.set_password(temporary_password)
    if User.objects.filter(school=school, username__iexact=user.username).exists():
        raise ValidationError(
            {"username": "A user with this username already exists in this school."}
        )
    user.full_clean()
    user.save()

    record(
        action=actions.USER_CREATED,
        module=actions.MODULE_ACCOUNTS,
        actor=actor,
        school=school,
        obj=user,
        new_value={"username": user.username, "role": user.role},
        request=request,
    )
    return user, temporary_password


@transaction.atomic
def reset_password(*, actor, user, request=None):
    """Replace a user's password with a new temporary one and return it."""
    if actor is not None and actor.pk == user.pk:
        raise PermissionDenied("Use the change password option for your own account.")
    _assert_can_manage(actor, school_id=user.school_id, role=user.role)

    temporary_password = generate_temporary_password()
    user.set_password(temporary_password)
    user.must_change_password = True
    user.password_changed_at = None
    user.save(update_fields=["password", "must_change_password", "password_changed_at"])

    record(
        action=actions.PASSWORD_RESET,
        module=actions.MODULE_ACCOUNTS,
        actor=actor,
        school=user.school,
        obj=user,
        request=request,
    )
    return temporary_password


@transaction.atomic
def change_password(*, user, new_password, request=None):
    """Set a new password chosen by the user and clear the first-login flag."""
    if user.check_password(new_password):
        raise ValidationError(
            {"new_password": ["The new password must be different from your current password."]}
        )
    password_validation.validate_password(new_password, user)

    user.set_password(new_password)
    user.must_change_password = False
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "must_change_password", "password_changed_at"])

    record(
        action=actions.PASSWORD_CHANGED,
        module=actions.MODULE_ACCOUNTS,
        actor=user,
        school=user.school,
        obj=user,
        request=request,
    )
    return user
