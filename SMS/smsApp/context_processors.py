"""Template context available on every page."""
from .navigation import items_for_role


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "nav_items": items_for_role(user.role),
        "current_school": user.school,
    }