from datetime import timedelta
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.timezone import now

class User(AbstractUser):
    ROLE_CHOICES = [("Pemilik", "Pemilik"), ("Karyawan", "Karyawan")]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Pemilik")

    owner = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="employees",
        limit_choices_to={"role": "Pemilik"},
    )

    # Tambahkan related_name untuk menghindari konflik
    groups = models.ManyToManyField(Group, related_name="authentication_users", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="authentication_user_permissions", blank=True)

class Invitation(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=[("Pemilik", "Pemilik"), ("Karyawan", "Karyawan")])
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invitations")
    token = models.CharField(max_length=512, unique=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return self.expires_at > now()

