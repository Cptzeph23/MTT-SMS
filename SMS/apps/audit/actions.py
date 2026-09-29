"""Audit action and module identifiers."""

MODULE_AUTH = "auth"
MODULE_ACCOUNTS = "accounts"
MODULE_SCHOOLS = "schools"

LOGIN = "auth.login"
LOGOUT = "auth.logout"
LOGIN_FAILED = "auth.login_failed"
LOGIN_LOCKED = "auth.login_locked"

USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_ROLE_CHANGED = "user.role_changed"
PASSWORD_CHANGED = "user.password_changed"
PASSWORD_RESET = "user.password_reset"
PASSWORD_RESET_REQUESTED = "user.password_reset_requested"
PASSWORD_RESET_COMPLETED = "user.password_reset_completed"

SCHOOL_CREATED = "school.created"
SCHOOL_UPDATED = "school.updated"
