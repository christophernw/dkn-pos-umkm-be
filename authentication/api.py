import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User
from pydantic import BaseModel, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from authentication.models import Business, BusinessUser
from produk.api import AuthBearer
from django.db import transaction

router = Router()

class SessionData(BaseModel):
    user: dict
    
class RefreshTokenRequest(BaseModel):
    refresh: str

class TokenValidationRequest(BaseModel):
    token: str

class AddUserRequest(BaseModel):
    name: str
    email: str
    role: str

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

    # Generate refresh token for the user
    refresh = RefreshToken.for_user(user)

    # Check if the user already has a business, if not create one
    try:
        business_user = BusinessUser.objects.get(user=user)
        business = business_user.business
    except BusinessUser.DoesNotExist:
        business = Business.objects.create(owner=user)
        BusinessUser.objects.create(user=user, business=business, role="Pemilik")

    business_users = BusinessUser.objects.filter(business=business)
    users_data = [
        {
            "id": bu.user.id,
            "name": bu.user.username,
            "email": bu.user.email,
            "role": bu.role
        }
        for bu in business_users
    ]
    
    return {
        "message": "Login successful",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.username,
            "users": users_data,
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
    
@router.post("/add-user", response={200: dict, 400: dict}, auth=AuthBearer())
def add_user(request, payload: AddUserRequest):

    name = payload.name.strip()
    role = payload.role.strip()
    email = payload.email.strip().lower()

    try:
        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                return 400, {"error": "Email sudah digunakan."}
        
            user = User.objects.create_user(username=name, email=email)
            
            try:
                business = Business.objects.get(owner=request.auth)
            except Business.DoesNotExist:
                return 400, {"error": "Bisnis tidak ditemukan untuk user ini."}
            
            # Cek apakah user sudah terdaftar dalam bisnis
            if BusinessUser.objects.filter(user=user, business=business).exists():
                return 400, {"error": "Pengguna sudah terdaftar di bisnis ini."}
                
            # Buat relasi BusinessUser
            BusinessUser.objects.create(user=user, business=business, role=role)

            return {"message": "User berhasil ditambahkan.", 
                    "user": {
                        "id": user.id,
                        "name": user.username,
                        "email": user.email,
                        "role": role
                    }}

    except ValidationError as e:
        return 400, {"error": str(e)}    
    except Exception as e:
        return 400, {"error": f"Terjadi kesalahan: {str(e)}"}
    
@router.get("/users", response={200: list[dict], 401: dict}, auth=AuthBearer())
def get_users(request):
    try:
        business = Business.objects.get(owner=request.user)
        
        business_users = BusinessUser.objects.filter(business=business)

        users_data = [
            {
                "id": bu.user.id,
                "name": bu.user.username,
                "email": bu.user.email,
                "role": bu.role
            }
            for bu in business_users
        ]

        return users_data

    except Business.DoesNotExist:
        return 400, {"error": "Anda tidak memiliki bisnis yang terdaftar."}
