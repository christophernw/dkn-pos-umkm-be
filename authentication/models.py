# authentication/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta

class StoreInvitation(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
        (EXPIRED, 'Expired'),
    ]
    
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee_email = models.EmailField()
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations', null=True, blank=True)
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    
    # def save(self, *args, **kwargs):
    #     # Set expiration date if not already set
    #     if not self.expires_at:
    #         self.expires_at = timezone.now() + timedelta(days=7)
    #     super().save(*args, **kwargs)