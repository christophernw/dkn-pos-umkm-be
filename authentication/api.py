from ninja import Router
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User
from pydantic import BaseModel
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import StoreInvitation
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

router = Router()

class SessionData(BaseModel):
    user: dict
    
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

# New endpoints for store invitations
@router.post("/invite", response={200: StoreInvitationResponse, 400: dict})
def send_invitation(request, invitation_data: StoreInvitationRequest):
    """Send an invitation to join a store"""
    user_id = request.auth
    
    try:
        inviter = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"error": "User not found"}
        
    # Check if email already has an active invitation
    existing_invitation = StoreInvitation.objects.filter(
        inviter=inviter,
        invitee_email=invitation_data.invitee_email,
        status=StoreInvitation.PENDING,
        expires_at__gt=timezone.now()
    ).first()
    
    if existing_invitation:
        return 400, {"error": "An active invitation already exists for this email"}
    
    # Create a new invitation
    invitation = StoreInvitation(
        inviter=inviter,
        invitee_email=invitation_data.invitee_email,
        token=str(uuid.uuid4())
    )
    invitation.save()
    
    return 200, {
        "id": invitation.id,
        "inviter_name": invitation.inviter.username,
        "invitee_email": invitation.invitee_email,
        "token": invitation.token,
        "status": invitation.status,
        "created_at": invitation.created_at.isoformat(),
        "expires_at": invitation.expires_at.isoformat()
    }

@router.get("/invitations", response=list[StoreInvitationResponse])
def list_invitations(request):
    """List all invitations sent by the current user"""
    user_id = request.auth
    
    invitations = StoreInvitation.objects.filter(inviter_id=user_id)
    
    result = []
    for invitation in invitations:
        result.append({
            "id": invitation.id,
            "inviter_name": invitation.inviter.username,
            "invitee_email": invitation.invitee_email,
            "token": invitation.token,
            "status": invitation.status,
            "created_at": invitation.created_at.isoformat(),
            "expires_at": invitation.expires_at.isoformat()
        })
        
    return result

