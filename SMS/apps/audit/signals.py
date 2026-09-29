"""Authentication events recorded in the audit log."""
import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from . import actions
from .services import record

logger = logging.getLogger(__name__)


def _safe_record(**kwargs):
    """Audit failures must never block authentication."""
    try:
        record(**kwargs)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to write audit entry for %s", kwargs.get("action"))


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    _safe_record(
        action=actions.LOGIN,
        module=actions.MODULE_AUTH,
        actor=user,
        obj=user,
        request=request,
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
    _safe_record(
        action=actions.LOGOUT,
        module=actions.MODULE_AUTH,
        actor=user,
        obj=user,
        request=request,
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    from apps.schools.models import School

    username = str(credentials.get("username") or "")[:150]
    school_code = str(credentials.get("school_code") or "")[:30]
    school = None
    if school_code:
        school = School.objects.filter(code__iexact=school_code).first()
    _safe_record(
        action=actions.LOGIN_FAILED,
        module=actions.MODULE_AUTH,
        school=school,
        object_type="User",
        object_repr=username,
        new_value={"school_code": school_code},
        request=request,
    )
