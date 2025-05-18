from datetime import timedelta
import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, PermissionsMixin
from django.utils.timezone import now
from django.contrib.auth.hashers import make_password
from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class Toko(models.Model):
    # Initially just a simple model to link users
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner = self.users.filter(role="Pemilik").first()
        return f"Toko {self.id} - {owner.username if owner else 'No owner'}"


class User(AbstractBaseUser, PermissionsMixin):
    # User fields
    username = models.CharField(max_length=254, blank=True)
    email = models.EmailField(max_length=254, unique=True)

    # Additional fields required for Django auth system
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=now)

    # Custom fields
    ROLE_CHOICES = [
        ("BPR", "BPR"),
        ("Pemilik", "Pemilik"),
        ("Pengelola", "Pengelola"),
        ("Karyawan", "Karyawan"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Pemilik")

    # Add foreign key to Toko
    toko = models.ForeignKey(
        Toko, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )

    # Required fields
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    # User manager
    objects = UserManager()


class Invitation(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=[
            ("Pemilik", "Pemilik"),
            ("Pengelola", "Pengelola"),
            ("Karyawan", "Karyawan"),
        ],
    )
    toko = models.ForeignKey(
        Toko, on_delete=models.CASCADE, related_name="invitations"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    token = models.CharField(max_length=512, unique=True)
    expires_at = models.DateTimeField()