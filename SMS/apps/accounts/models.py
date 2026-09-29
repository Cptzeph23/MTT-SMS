from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from smsApp.querysets import SchoolQuerySet


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    PRINCIPAL = "principal", "Principal"
    DEPUTY_PRINCIPAL = "deputy_principal", "Deputy Principal"
    FINANCE_ADMIN = "finance_admin", "Finance Admin"
    TEACHER = "teacher", "Teacher"
    PARENT = "parent", "Parent/Guardian"


# Every role that belongs to exactly one school.
SCHOOL_ROLES = (
    Role.PRINCIPAL,
    Role.DEPUTY_PRINCIPAL,
    Role.FINANCE_ADMIN,
    Role.TEACHER,
    Role.PARENT,
)

username_validator = RegexValidator(
    regex=r"^[\w.@+/-]+$",
    message="Usernames may contain letters, digits and the characters . @ + - _ /",
)


class UserManager(BaseUserManager.from_queryset(SchoolQuerySet)):
    """Manager with school-scoped queries and user creation helpers."""

    def _create_user(self, username, password, **extra_fields):
        if not username or not str(username).strip():
            raise ValueError("The username must be set.")
        extra_fields["email"] = self.normalize_email(extra_fields.get("email"))
        user = self.model(username=str(username).strip(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        if not extra_fields.get("role"):
            raise ValueError("A role is required.")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields["role"] = Role.SUPER_ADMIN.value
        extra_fields["school"] = None
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("must_change_password", False)
        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(username, password, **extra_fields)


class User(AbstractUser):
    """System user. Usernames are unique per school (case-insensitive)."""

    username = models.CharField(
        "username",
        max_length=150,
        validators=[username_validator],
        help_text="Admission number, staff ID or phone number. Unique within the school.",
    )
    school = models.ForeignKey(
        "schools.School",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)
    must_change_password = models.BooleanField(
        default=True,
        help_text="When set, the user must choose a new password before doing anything else.",
    )
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["school__name", "username"]
        constraints = [
            models.UniqueConstraint(
                Lower("username"), "school", name="uniq_user_school_username_ci"
            ),
            models.UniqueConstraint(
                Lower("username"),
                condition=Q(school__isnull=True),
                name="uniq_user_platform_username_ci",
            ),
            models.CheckConstraint(
                condition=(
                    Q(role=Role.SUPER_ADMIN.value, school__isnull=True)
                    | (~Q(role=Role.SUPER_ADMIN.value) & Q(school__isnull=False))
                ),
                name="user_role_school_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "role"], name="user_school_role_idx"),
            models.Index(fields=["school", "is_active"], name="user_school_active_idx"),
        ]

    def clean(self):
        super().clean()
        if self.role == Role.SUPER_ADMIN:
            if self.school_id is not None:
                raise ValidationError(
                    {"school": "Super Admin accounts must not belong to a school."}
                )
        elif self.role and self.school_id is None:
            raise ValidationError({"school": "This role must belong to a school."})

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.username
