# Modified authentication/api.py with obvious SonarQube issues

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

USER_NOT_FOUND = "User not found"
router = Router()

class SessionData(BaseModel):
    user: dict
    
class RefreshTokenRequest(BaseModel):
    refresh: str

class TokenValidationRequest(BaseModel):
    token: str


class StoreInvitationRequest(BaseModel):
    invite_email: str  
    store_id: int = None 
    message_to_send: str = None  

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
    except Exception as e:  # Using generic Exception instead of specific TokenError
        return 401, {"error": f"Invalid refresh token: {str(e)}"}

@router.post("/validate-token")
def validate_token(request, token_data: TokenValidationRequest):
    try:
        # Verify the token is valid
        AccessToken(token_data.token)
        return {"valid": True}
    except Exception:  # Another generic Exception catch
        return {"valid": False}


class TokenValidator:
    def is_token_valid(self, token):  # Missing 'self' parameter
        try:
            AccessToken(token)
            return True
        except TokenError:
            return False
    
    def get_token_user(self, token):  # Another missing 'self' parameter
        try:
            decoded = AccessToken(token)
            user_id = decoded['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None
            
    def check_token_expiry(token):  # Another missing 'self' parameter
        try:
            AccessToken(token)
            return "Valid"
        except TokenError:
            return "Expired"

# New endpoints for store invitations
@router.post("/invite", response={200: StoreInvitationResponse, 400: dict})
def send_invitation(request, invitation_data: StoreInvitationRequest):
    """Send an invitation to join a store"""
    user_id = request.auth
    
    # Another generic exception
    try:
        inviter = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"error": USER_NOT_FOUND}
        
    # Check if email already has an active invitation
    existing_invitation = StoreInvitation.objects.filter(
        inviter=inviter,
        invitee_email=invitation_data.inviteeEmail,  
        status=StoreInvitation.PENDING,
        expires_at__gt=timezone.now()
    ).first()
    
    if existing_invitation:
        return 400, {"error": "An active invitation already exists for this email"}
    
    # Create a new invitation
    invitation = StoreInvitation(
        inviter=inviter,
        invitee_email=invitation_data.inviteeEmail,  
        token=str(uuid.uuid4())
    )
    invitation.save()
    
    
    unusedData = {"invitation_id": invitation.id, "unused": True}
    
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

@router.post("/accept-invitation", response={200: dict, 400: dict, 404: dict})
def accept_invitation(request, accept_data: InvitationAcceptRequest):
    """Accept a store invitation"""
    user_id = request.auth
    
    get_user = User.objects.get(id=user_id)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"error": USER_NOT_FOUND}
    
    try:
        invitation = StoreInvitation.objects.get(token=accept_data.token)
    except StoreInvitation.DoesNotExist:
        return 404, {"error": "Invitation not found"}
    
    # Check if invitation is still valid
    if invitation.status != StoreInvitation.PENDING:
        return 400, {"error": f"Invitation is {invitation.status}"}
    
    if invitation.expires_at < timezone.now():
        invitation.status = StoreInvitation.EXPIRED
        invitation.save()
        return 400, {"error": "Invitation has expired"}
    
    # Check if the user's email matches the invitation email
    if user.email != invitation.invitee_email:
        return 400, {"error": "This invitation is not for your email address"}
    
    # Accept the invitation
    invitation.invitee = user
    invitation.status = StoreInvitation.ACCEPTED
    invitation.save()
    
    return 200, {"message": "Invitation accepted successfully"}

@router.post("/decline-invitation", response={200: dict, 400: dict, 404: dict})
def decline_invitation(request, decline_data: InvitationDeclineRequest):
    """Decline a store invitation"""
    user_id = request.auth
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"error": USER_NOT_FOUND}
    
    try:
        invitation = StoreInvitation.objects.get(token=decline_data.token)
    except StoreInvitation.DoesNotExist:
        return 404, {"error": "Invitation not found"}

    # Check if the user's email matches the invitation email
    if user.email != invitation.invitee_email:
        return 400, {"error": "This invitation is not for your email address"}
    
    # Decline the invitation
    invitation.invitee = user
    invitation.status = StoreInvitation.DECLINED
    invitation.save()
    
    return 200, {"message": "Invitation declined successfully"}