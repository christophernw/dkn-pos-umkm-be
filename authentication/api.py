from datetime import datetime, timedelta
import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from authentication.models import Invitation, Toko, User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from produk.api import AuthBearer
from django.conf import settings
from django.utils.timezone import now
from django.db.utils import IntegrityError

from .schemas import (
    RemoveUserRequest,
    SessionData,
    RefreshTokenRequest,
    TokenValidationRequest,
    AddUserRequest,
    InvitationRequest,
)

router = Router()

@router.post("/process-session")
def process_session(request, session_data: SessionData):
    user_data = session_data.user

    try:
        user = User.objects.get(email=user_data.get("email"))
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=user_data.get("name"),
            email=user_data.get("email"),
        )
            
    toko = Toko.objects.create()
    user.toko = toko
    user.save()

    refresh = RefreshToken.for_user(user)

    return {
        "message": "Login successful",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.username,
            "role": user.role,
            "toko_id": user.toko.id if user.toko else None
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
        AccessToken(token_data.token)
        return {"valid": True}
    except TokenError:
        return {"valid": False}
        
@router.get("/get-users", response={200: list[dict], 401: dict}, auth=AuthBearer())
def get_users(request):
    user = User.objects.get(id=request.auth)
    
    if user.toko:
        # Get all users in the same toko
        users = User.objects.filter(toko=user.toko)
    else:
        # If user has no toko, just return the user
        users = User.objects.filter(id=user.id)
    
    users_data = [
        {
            "id": u.id,
            "name": u.username,
            "email": u.email,
            "role": u.role,
            "toko_id": u.toko.id if u.toko else None
        }
        for u in users
    ]

    # Sort users based on role hierarchy: Pemilik, Administrator, Karyawan
    def role_priority(role):
        if role == "Pemilik":
            return 0
        elif role == "Administrator":
            return 1
        else:  # "Karyawan"
            return 2

    users_data.sort(key=lambda u: role_priority(u['role']))

    return users_data

@router.post("/send-invitation", response={200: dict, 400: dict}, auth=AuthBearer())
def send_invitation(request, payload: InvitationRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    role = payload.role.strip()
    owner = User.objects.get(id=request.auth)
    
    # If user already exists in the toko, return an error
    existing_user = User.objects.filter(email=email, toko=owner.toko).first()
    if existing_user:
        return 400, {"error": "User sudah ada di toko ini."}

    if Invitation.objects.filter(email=email, owner=owner).exists():
        return 400, {"error": "Undangan sudah dikirim ke email ini."}

    expiration = now() + timedelta(days=1)
    token_payload = {"email": email, "name": name, "role": role, "owner_id": owner.id, "exp": expiration}
    token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

    try:
        Invitation.objects.create(
            email=email, name=name, role=role, owner=owner, token=token, expires_at=expiration
        )
        return 200, {"message": "Invitation sent", "token": token}
    except IntegrityError:
        return 400, {"error": "Invitation already exists."}
    
@router.post("/validate-invitation")
def validate_invitation(request, payload: TokenValidationRequest):
    try:
        decoded = jwt.decode(payload.token, settings.SECRET_KEY, algorithms=["HS256"])
        email = decoded.get("email")
        name = decoded.get("name")
        role = decoded.get("role")
        owner_id = decoded.get("owner_id")

        invitation = Invitation.objects.filter(email=email, token=payload.token).first()
        if not invitation:
            return {"valid": False, "error": "Invalid invitation"}

        # Get owner information once
        owner = User.objects.get(id=owner_id)
        
        # Check if user already exists
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Create new user only if doesn't exist
            user = User.objects.create_user(username=name, email=email, role=role)
        else:
            # Update role for existing user
            user.role = role
        
        # Set toko relationship (for both new and existing users)
        if owner.toko:
            user.toko = owner.toko
            user.save()
        
        # Clean up the invitation
        invitation.delete()
        
        return {
            "valid": True,
            "message": "User successfully registered",
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token expired"}
    except jwt.DecodeError:
        return {"valid": False, "error": "Invalid token"}

@router.post("/remove-user-from-toko", response={200: dict, 400: dict, 403: dict}, auth=AuthBearer())
def remove_user_from_toko(request, payload: RemoveUserRequest):
    # Get the requesting user (must be a Pemilik)
    requester = User.objects.get(id=request.auth)
    
    # Verify requester is a Pemilik
    if requester.role != "Pemilik":
        return 403, {"error": "Only Pemilik can remove users from toko"}
    
    # Get the user to be removed
    try:
        user_to_remove = User.objects.get(id=payload.user_id)
    except User.DoesNotExist:
        return 400, {"error": "User not found"}
    
    # Verify users belong to the same toko
    if not requester.toko or requester.toko != user_to_remove.toko:
        return 400, {"error": "User is not in your toko"}
    
    # Prevent removing oneself
    if requester.id == user_to_remove.id:
        return 400, {"error": "Cannot remove yourself from your own toko"}
    
    # Store the user's current toko and set to None temporarily
    original_toko = user_to_remove.toko
    user_to_remove.toko = None
    
    # Create a new toko for the removed user
    user_to_remove.role = "Pemilik"
    new_toko = Toko.objects.create()
    user_to_remove.toko = new_toko
    user_to_remove.save()
    
    return {
        "message": f"User {user_to_remove.username} removed from toko and given a new toko",
        "user": {
            "id": user_to_remove.id,
            "name": user_to_remove.username,
            "email": user_to_remove.email,
            "role": user_to_remove.role,
            "new_toko_id": new_toko.id
        }
    }