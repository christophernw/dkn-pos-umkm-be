import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from authentication.models import User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from produk.api import AuthBearer
from .schemas import (
    SessionData,
    RefreshTokenRequest,
    TokenValidationRequest,
    AddUserRequest,
    UserResponse,
    ErrorResponse
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


from django.db.utils import IntegrityError

@router.post("/add-user", response={200: dict, 400: dict}, auth=AuthBearer())
def add_user(request, payload: AddUserRequest):
    name = payload.name.strip()
    role = payload.role.strip()
    email = payload.email.strip().lower()
    owner = User.objects.get(id=request.auth)

    if User.objects.filter(email=email).exists():
        return 400, {"error": "User sudah terdaftar."}

    try:
        user = User.objects.create_user(
            username=name,
            email=email,
            role=role,
            owner=owner,
        )
        return 200, {"message": "User berhasil ditambahkan.", "user_id": user.id}
    except IntegrityError:
        return 400, {"error": "User sudah terdaftar."}
        
@router.get("/get-users", response={200: list[dict], 401: dict}, auth=AuthBearer())
def get_users(request):
    try:
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
    except Exception as e:
        return 401, {"error": f"Terjadi kesalahan: {str(e)}"}