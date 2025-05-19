from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
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

# authentication/api.py
@router.post("/process-session")
def process_session(request, session_data: SessionData):
    user_data = session_data.user
    email = user_data.get("email")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=user_data.get("name"),
            email=email,
        )
        
        # Regular user flow - always create a toko for new users
        # BPR user will have a toko too, but we'll ignore it in the logic
        toko = Toko.objects.create()
        user.toko = toko
        user.save()

    refresh = RefreshToken.for_user(user)
    
    # Check if this is the BPR email without changing the role
    is_bpr = (email == settings.BPR_EMAIL)

    return {
        "message": "Login successful",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.username,
            "role": user.role,
            "toko_id": user.toko.id if user.toko else None,
            "is_bpr": is_bpr,  # Flag for frontend without changing DB
        },
    }

@router.post("/refresh-token", response={200: dict, 401: dict})
def refresh_token(request, refresh_data: RefreshTokenRequest):
    try:
        refresh = RefreshToken(refresh_data.refresh)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}
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
            "toko_id": u.toko.id if u.toko else None,
        }
        for u in users
    ]

    # Sort users based on role hierarchy: Pemilik, Pengelola, Karyawan
    def role_priority(role):
        if role == "Pemilik":
            return 0
        elif role == "Pengelola":
            return 1
        else:  # "Karyawan"
            return 2

    users_data.sort(key=lambda u: role_priority(u["role"]))

    return users_data


@router.post("/send-invitation", response={200: dict, 400: dict}, auth=AuthBearer())
def send_invitation(request, payload: InvitationRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    role = payload.role.strip()
    user = User.objects.get(id=request.auth)

    if user.role not in ['Pemilik', 'Pengelola']:
        return 400, {"error": "Hanya Pemilik atau Pengelola yang dapat mengirim undangan."}

    # Check if user has a toko
    if not user.toko:
        return 400, {"error": "User doesn't have a toko."}

    # If user already exists in the toko, return an error
    existing_user = User.objects.filter(email=email, toko=user.toko).first()
    if existing_user:
        return 400, {"error": "User sudah ada di toko ini."}

    # Check if invitation already exists for this email and toko
    if Invitation.objects.filter(email=email, toko=user.toko).exists():
        return 400, {"error": "Undangan sudah dikirim ke email ini."}

    expiration = now() + timedelta(days=1)
    token_payload = {
        "email": email,
        "name": name,
        "role": role,
        "toko_id": user.toko.id,
        "exp": expiration,
    }
    token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

    try:
        Invitation.objects.create(
            email=email,
            name=name,
            role=role,
            toko=user.toko,
            created_by=user,
            token=token,
            expires_at=expiration,
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
        toko_id = decoded.get("toko_id")

        invitation = Invitation.objects.filter(email=email, token=payload.token).first()
        if not invitation:
            return {"valid": False, "error": "Invalid invitation"}

        # Get toko information
        toko = Toko.objects.get(id=toko_id)

        # Check if user already exists
        user = User.objects.filter(email=email).first()

        if not user:
            # Create new user only if doesn't exist
            user = User.objects.create_user(username=name, email=email, role=role)
        else:
            # Update role for existing user
            user.role = role
            user.username = name

        # Set toko relationship (for both new and existing users)
        user.toko = toko
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


@router.post(
    "/remove-user-from-toko",
    response={200: dict, 400: dict, 403: dict},
    auth=AuthBearer(),
)
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

    # Store user information before removal for the email
    removed_user_email = user_to_remove.email
    removed_user_name = user_to_remove.username
    
    # Give new toko to user
    toko = Toko.objects.create()
    user_to_remove.toko = toko
    
    # Reset role to regular user 
    user_to_remove.role = "Pemilik"  # Default to lowest role when removed
    user_to_remove.save()

    return {
        "message": f"User {removed_user_name} removed from toko",
        "user": {
            "id": user_to_remove.id,
            "name": removed_user_name,
            "email": removed_user_email,
            "role": user_to_remove.role,
        },
    }

@router.get("/pending-invitations", response={200: list[dict], 404: dict}, auth=AuthBearer())
def get_pending_invitations(request):
    """Get all pending invitations created for the user's toko."""
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)

    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}

    # Get invitations where the toko is the user's toko
    invitations = Invitation.objects.filter(toko=user.toko)
    
    invitations_data = [
        {
            "id": invitation.id,
            "email": invitation.email,
            "name": invitation.name,
            "role": invitation.role,
            "created_by": invitation.created_by.username,
            "created_at": invitation.expires_at - timedelta(days=1),  # Assuming invitations always expire in 1 day
            "expires_at": invitation.expires_at,
        }
        for invitation in invitations
    ]
    
    return 200, invitations_data

@router.delete("/delete-invitation/{invitation_id}", response={200: dict, 404: dict, 403: dict}, auth=AuthBearer())
def delete_invitation(request, invitation_id: int):
    """Delete an invitation by ID. Only users in the same toko can delete invitations."""
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}
    
    try:
        invitation = get_object_or_404(Invitation, id=invitation_id)
        
        # Check if the invitation belongs to the user's toko
        if invitation.toko.id != user.toko.id:
            return 403, {"message": "You don't have permission to delete this invitation"}
        
        # Delete the invitation
        invitation.delete()
        
        return 200, {"message": "Invitation deleted successfully"}
    except Exception as e:
        return 404, {"message": f"Error deleting invitation: {str(e)}"}
    
# Updated BPR shops endpoint to exclude BPR's own toko
@router.get("/bpr/shops", response={200: list[dict], 403: dict}, auth=AuthBearer())
def get_all_shops(request):
    """Get all shops for BPR admin user, excluding the BPR's own toko."""
    user_id = request.auth
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if the user is a BPR user
        if user.email != settings.BPR_EMAIL:
            return 403, {"error": "Only BPR users can access this endpoint"}
        
        # Get all shops except BPR's own toko
        shops = Toko.objects.all()
        
        # If BPR user has a toko, exclude it
        if user.toko:
            shops = shops.exclude(id=user.toko.id)
        
        shops_data = []
        for shop in shops:
            owner = shop.users.filter(role="Pemilik").first()
            if owner:
                shops_data.append({
                    "id": shop.id,
                    "owner": owner.username if owner else "No owner",
                    "created_at": shop.created_at,
                    "user_count": shop.users.count(),
                })
        
        return 200, shops_data
    except Exception as e:
        print(f"Error: {str(e)}")
        return 403, {"error": "Access denied"}
    
@router.get("/bpr/shop/{shop_id}", response={200: dict, 403: dict, 404: dict}, auth=AuthBearer())
def get_shop_info(request, shop_id: int):
    """Get information about a specific shop for BPR users."""
    user_id = request.auth
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if the user is a BPR user
        if user.email != settings.BPR_EMAIL:
            return 403, {"error": "Only BPR users can access this endpoint"}
        
        # Get the shop
        shop = get_object_or_404(Toko, id=shop_id)
        
        # Get the shop owner
        owner = shop.users.filter(role="Pemilik").first()
        
        return 200, {
            "id": shop.id,
            "owner": owner.username if owner else "No owner",
            "created_at": shop.created_at,
            "user_count": shop.users.count(),
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return 403, {"error": "Access denied"}