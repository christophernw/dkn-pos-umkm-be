from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User
from pydantic import BaseModel, Field
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import StoreInvitation
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List
import uuid
import random

USER_NOT_FOUND = "User not found"
router = Router()

# Updated model with explicit validation
class UserData(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    date_joined: str
    is_active: bool

class UsersListResponse(BaseModel):
    users: List[UserResponse]
    total_count: int

class SessionData(BaseModel):
    user: UserData
    
class RefreshTokenRequest(BaseModel):
    refresh: str

class TokenValidationRequest(BaseModel):
    token: str

class StoreInvitationRequest(BaseModel):
    invitee_email: str

class StoreInvitationResponse(BaseModel):
    id: int
    inviter_name: str
    invitee_email: str
    token: str
    status: str
    created_at: str
    expires_at: str

class InvitationAcceptRequest(BaseModel):
    token: str

class InvitationDeclineRequest(BaseModel):
    token: str

@router.post("/process-session")
def process_session(request, session_data: SessionData):
    user_data = session_data.user

    try:
        # Try to find existing user by email
        user = User.objects.get(email=user_data.email)
    except User.DoesNotExist:
        # User doesn't exist, create new one
        
        # Check if username exists first to avoid IntegrityError
        if User.objects.filter(username=user_data.name).exists():
            # Username already exists, generate a unique one
            unique_suffix = str(random.randint(1000, 9999))
            username = f"{user_data.name}_{unique_suffix}"
        else:
            # Username is available
            username = user_data.name
            
        # Now create the user with the available or modified username
        user = User.objects.create_user(
            username=username,
            email=user_data.email,
        )

    refresh = RefreshToken.for_user(user)

    return {
        "message": "Login successful",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.username,
        },
    }

@router.post("/refresh-token", response={200: dict, 401: dict})
def refresh_token(request, refresh_data: RefreshTokenRequest):
    try:
        refresh = RefreshToken(refresh_data.refresh)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }
    except TokenError as e:
        return 401, {"error": f"Invalid refresh token: {str(e)}"}

@router.post("/validate-token")
def validate_token(request, token_data: TokenValidationRequest):
    try:
        # Verify the token is valid
        AccessToken(token_data.token)
        return {"valid": True}
    except TokenError:
        return {"valid": False}

@router.get("/users", response={200: UsersListResponse})
def get_all_users(request):
    """Get all users in the system"""
    users = User.objects.all().order_by('id')
    
    user_responses = []
    for user in users:
        user_responses.append(UserResponse(
            id=user.id,
            email=user.email,
            name=user.username,
            date_joined=user.date_joined.isoformat(),
            is_active=user.is_active
        ))
    
    return 200, UsersListResponse(
        users=user_responses,
        total_count=len(user_responses)
    )