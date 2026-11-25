"""Custom User model and RBAC models."""
import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import TimeStampedModel, UUIDModel


class RoleScope(models.TextChoices):
    PLATFORM = "platform", "Platform"
    INSTITUTION = "institution", "Institution"


class UserManager(BaseUserManager):
    """Manager for email-based global User accounts."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        normalized_email = self.normalize_email(email).strip().lower()
        user = self.model(email=normalized_email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Global user identity across institutions."""

    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    class Meta:
        db_table = "app_users"
        ordering = ["first_name", "last_name", "email"]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"


class Role(UUIDModel):
    """Defined role catalogue (platform or institution scoped)."""

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    scope = models.CharField(max_length=20, choices=RoleScope.choices)

    class Meta:
        db_table = "roles"
        ordering = ["scope", "code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.scope})"


class Permission(UUIDModel):
    """Granular backend authorization permission."""

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    scope = models.CharField(max_length=20, choices=RoleScope.choices)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "permissions"
        ordering = ["scope", "code"]

    def __str__(self) -> str:
        return self.code


class RolePermission(models.Model):
    """Mapping between roles and granular permissions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission"),
        ]

    def clean(self):
        if self.role_id and self.permission_id and self.role.scope != self.permission.scope:
            raise ValidationError("Role and Permission must share the same scope.")

    def __str__(self) -> str:
        return f"{self.role.code} -> {self.permission.code}"


class PlatformRole(models.Model):
    """Platform-level role assignments (e.g., PLATFORM_SUPER_ADMIN)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="platform_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="platform_assignments")
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_platform_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "platform_roles"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uq_platform_user_role"),
        ]

    def clean(self):
        if self.role_id and self.role.scope != RoleScope.PLATFORM:
            raise ValidationError("Only platform-scoped roles can be assigned in PlatformRole.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.role.code}"

