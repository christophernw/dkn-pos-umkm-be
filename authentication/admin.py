from django.contrib import admin
from .models import Invitation, User

# Register your models here.
admin.site.register(User)
admin.site.register(Invitation)