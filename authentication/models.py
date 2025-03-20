from django.db import models
from django.contrib.auth.models import User

class Business(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business")
    

class BusinessUser(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="business_membership")
    role = models.CharField(max_length=20, choices=[("Pemilik", "Pemilik"), ("Karyawan", "Karyawan")])

    class Meta:
        unique_together = ("business", "user")  
