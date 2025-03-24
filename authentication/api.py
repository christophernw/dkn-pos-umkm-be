import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from authentication.models import User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from produk.api import AuthBearer

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

class UserResponse(BaseModel):
    id: int
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
        
@router.post("/get-users", response={200: list[dict], 401: dict}, auth=AuthBearer())
def get_users(request):
    try:
        user = request.auth
        if user.role == "Pemilik":
            users = User.objects.filter(owner=user)
        else:
            users = User.objects.filter(owner=user.owner)
        users_data = [
            {
                "id": u.id,
                "name": u.username,
                "email": u.email,
                "role": u.role
            }
            for u in users
        ]
        print(users)
        return users_data
    except Exception as e:
        return 400, {"error": f"Terjadi kesalahan: {str(e)}"}

# @router.post("/add-user", response={200: dict, 400: dict}, auth=AuthBearer())
# def add_user(request, payload: AddUserRequest):

#     name = payload.name.strip()
#     role = payload.role.strip()
#     email = payload.email.strip().lower()

#     try:
#         with transaction.atomic():
#             user = User.objects.get_or_create(username=name, email=email)
            
#             try:
#                 business = Business.objects.get(owner=request.auth)
#             except Business.DoesNotExist:
#                 return 400, {"error": "Bisnis tidak ditemukan untuk user ini."}
            
#             if BusinessUser.objects.filter(user=user, business=business).exists():
#                 return 400, {"error": "Pengguna sudah terdaftar di bisnis ini."}
                
#             BusinessUser.objects.create(user=user, business=business, role=role)

#             return {"message": "User berhasil ditambahkan.", 
#                     "user": {
#                         "id": user.id,
#                         "name": user.username,
#                         "email": user.email,
#                         "role": role
#                     }}

#     except ValidationError as e:
#         return 400, {"error": str(e)}    
#     except Exception as e:
#         return 400, {"error": f"Terjadi kesalahan: {str(e)}"}
    
# @router.get("/users", response={200: list[dict], 401: dict}, auth=AuthBearer())
# def get_users(request):
#     try:
#         user = request.auth

#         business = Business.objects.get(owner=user)
        
#         business_users = BusinessUser.objects.filter(business=business)

#         users_data = [
#             {
#                 "id": bu.user.id,
#                 "name": bu.user.username,
#                 "email": bu.user.email,
#                 "role": bu.role
#             }
#             for bu in business_users
#         ]

#         return users_data

#     except Business.DoesNotExist:
#         return 400, {"error": "Anda tidak memiliki bisnis yang terdaftar."}
