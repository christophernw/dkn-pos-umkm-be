from datetime import datetime, timedelta
import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from authentication.models import Invitation, User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from produk.api import AuthBearer
from django.conf import settings
from django.utils.timezone import now
from django.db.utils import IntegrityError

from .schemas import (
    SessionData,
    RefreshTokenRequest,
    TokenValidationRequest,
    AddUserRequest,
    InvitationRequest,
)

USER_ALREADY_EXISTS_ERROR = "User sudah terdaftar."

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

    refresh = RefreshToken.for_user(user)

    return {
        "message": "Login successful",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.username,
            "role": user.role
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
    if user.role == "Pemilik" or user.role == "pemilik":
        users = User.objects.filter(owner=user) | User.objects.filter(id=user.id)
    else:
        users = User.objects.filter(owner=user.owner)| User.objects.filter(id=user.id)
        if user.owner:
            users = users | User.objects.filter(id=user.owner.id)
    users_data = [
        {
            "id": u.id,
            "name": u.username,
            "email": u.email,
            "role": u.role
        }
        for u in users
    ]

    users_data.sort(key=lambda u: u['role'] != "Pemilik")  

    return users_data

@router.post("/send-invitation", response={200: dict, 400: dict}, auth=AuthBearer())
def send_invitation(request, payload: InvitationRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    role = payload.role.strip()
    owner = User.objects.get(id=request.auth)

    if User.objects.filter(email=email).exists():
        return 400, {"error": USER_ALREADY_EXISTS_ERROR}

    if Invitation.objects.filter(email=email).exists():
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

        User.objects.create_user(username=name, email=email, role=role, owner_id=owner_id)
        invitation.delete()
        return {
            "valid": True,
            "message": "User successfully registered",
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token expired"}
    except jwt.DecodeError:
        return {"valid": False, "error": "Invalid token"}


    

