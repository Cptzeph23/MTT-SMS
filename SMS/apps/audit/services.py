"""Single entry point for writing audit records."""
from smsApp.utils import get_client_ip

from .models import AuditLog


def record(
    *,
    action,
    module,
    actor=None,
    school=None,
    obj=None,
    object_type="",
    object_id="",
    object_repr="",
    previous_value=None,
    new_value=None,
    request=None,
):
    """Write one immutable audit entry and return it.

    Never pass passwords or tokens in previous_value or new_value.
    """
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None

    if obj is not None:
        object_type = object_type or obj.__class__.__name__
        object_id = object_id or str(getattr(obj, "pk", "") or "")
        object_repr = object_repr or str(obj)

    if school is not None:
        school_id = school.pk
    elif actor is not None:
        school_id = actor.school_id
    else:
        school_id = None

    return AuditLog.objects.create(
        school_id=school_id,
        actor=actor,
        actor_label=(actor.get_username() if actor is not None else "")[:150],
        actor_role=(actor.role if actor is not None else "")[:20],
        action=action,
        module=module,
        object_type=object_type[:100],
        object_id=str(object_id)[:64],
        object_repr=str(object_repr)[:255],
        previous_value=previous_value,
        new_value=new_value,
        ip_address=get_client_ip(request),
    )
