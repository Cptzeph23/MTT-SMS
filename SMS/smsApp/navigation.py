"""Role-based navigation registry.

Each phase appends the entries for its module here. Hiding a menu item is
only a convenience: every view still enforces permissions on the server.
"""
from dataclasses import dataclass

from apps.accounts.models import Role

ALL_ROLES = tuple(role.value for role in Role)


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    roles: tuple


NAV_ITEMS = (
    NavItem("Dashboard", "core:dashboard", ALL_ROLES),
)


def items_for_role(role):
    """Return the navigation items visible to a role."""
    return [item for item in NAV_ITEMS if role in item.roles]