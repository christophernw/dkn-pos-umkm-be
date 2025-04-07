from datetime import timedelta
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now

class Toko(models.Model):
    # Initially just a simple model to link users
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        owner = self.users.filter(role="Pemilik").first()
        return f"Toko {self.id} - {owner.username if owner else 'No owner'}"

class User(AbstractUser):
    ROLE_CHOICES = [
        ("Pemilik", "Pemilik"), 
        ("Administrator", "Administrator"), 
        ("Karyawan", "Karyawan")
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Pemilik")
    
    # Add foreign key to Toko
    toko = models.ForeignKey(Toko, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

class Invitation(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20, 
        choices=[("Pemilik", "Pemilik"), ("Administrator", "Administrator"), ("Karyawan", "Karyawan")]
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invitations")
    token = models.CharField(max_length=512, unique=True)
    expires_at = models.DateTimeField()