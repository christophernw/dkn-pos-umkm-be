from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

router = Router()

class SessionData(BaseModel):
    user: dict
    
class RefreshTokenRequest(BaseModel):
    refresh: str

class TokenValidationRequest(BaseModel):
    token: str

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
        },
    }