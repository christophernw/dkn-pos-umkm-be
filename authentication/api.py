from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User
from pydantic import BaseModel, Field, field_validator
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import StoreInvitation
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.http import Http404
from typing import List, Optional
import uuid
import random
import re

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

    @classmethod
    def from_user(cls, user):
        """Create UserResponse from User model"""
        return cls(
            id=user.id,
            email=user.email,
            name=user.username,
            date_joined=user.date_joined.isoformat(),
            is_active=user.is_active
        )

class UsersListResponse(BaseModel):
    users: List[UserResponse]
    total_count: int

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=150)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            # Simple email validation regex
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

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
    users_queryset = User.objects.all().order_by('id')
    
    # Use list comprehension for cleaner code
    user_responses = [
        UserResponse.from_user(user) 
        for user in users_queryset
    ]
    
    # Use queryset count() instead of len() for better performance with large datasets
    total_count = users_queryset.count()
    
    return 200, UsersListResponse(
        users=user_responses,
        total_count=total_count
    )

# NEW FUNCTION 1: Get user by ID
@router.get("/users/{user_id}", response={200: UserResponse, 404: dict})
def get_user_by_id(request, user_id: int):
    """Get a specific user by their ID"""
    try:
        user = get_object_or_404(User, id=user_id)
        return 200, UserResponse.from_user(user)
    except Http404:
        return 404, {"error": USER_NOT_FOUND}

# NEW FUNCTION 2: Update user profile
@router.put("/users/{user_id}", response={200: UserResponse, 404: dict, 422: dict})
def update_user_profile(request, user_id: int, payload: UpdateUserRequest):
    """Update user profile information"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if email is being updated and if it's already taken
        if payload.email is not None:
            # Check if another user has this email
            existing_user = User.objects.filter(email=payload.email).exclude(id=user_id).first()
            if existing_user:
                return 422, {"error": "Email already exists for another user"}
            user.email = payload.email
        
        # Check if username is being updated and if it's already taken
        if payload.name is not None:
            # Check if another user has this username
            existing_user = User.objects.filter(username=payload.name).exclude(id=user_id).first()
            if existing_user:
                return 422, {"error": "Username already exists for another user"}
            user.username = payload.name
        
        user.save()
        return 200, UserResponse.from_user(user)
        
    except Http404:
        return 404, {"error": USER_NOT_FOUND}

# NEW FUNCTION 3: Deactivate user (soft delete)
@router.delete("/users/{user_id}", response={200: dict, 404: dict, 422: dict})
def deactivate_user(request, user_id: int):
    """Deactivate a user (soft delete by setting is_active to False)"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if user is already inactive
        if not user.is_active:
            return 422, {"error": "User is already inactive"}
        
        user.is_active = False
        user.save()
        
        return 200, {
            "message": "User deactivated successfully",
            "user_id": user_id,
            "is_active": False
        }
        
    except Http404:
        return 404, {"error": USER_NOT_FOUND}