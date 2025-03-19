from django.shortcuts import render
from ninja import Router
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

router = Router()

