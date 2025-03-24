from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    ROLE_CHOICES = [("Pemilik", "Pemilik"), ("Karyawan", "Karyawan")]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Karyawan")

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