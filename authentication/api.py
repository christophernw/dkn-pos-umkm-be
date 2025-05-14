from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.conf import settings
from django.db.utils import IntegrityError
import jwt
from ninja import Router
from ninja_jwt.tokens import RefreshToken, AccessToken
from ninja_jwt.exceptions import TokenError
from authentication.models import Invitation, Toko, User
from produk.api import AuthBearer
from .schemas import (
    RemoveUserRequest,
    SessionData,
    RefreshTokenRequest,
    TokenValidationRequest,
    InvitationRequest,
)

router = Router()


@router.post("/process-session")
def process_session(request, session_data: SessionData):
    user_data = session_data.user
    email = user_data.get("email")

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": user_data.get("name"),
        },
    )

    if created:
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
            "toko_id": user.toko.id if user.toko else None,
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
    user = get_object_or_404(User, id=request.auth)

    users = (
        User.objects.filter(toko=user.toko)
        if user.toko
        else User.objects.filter(id=user.id)
    )

    def role_priority(role):
        return {"Pemilik": 0, "Pengelola": 1, "Karyawan": 2}.get(role, 3)

    users_data = sorted(
        [
            {
                "id": u.id,
                "name": u.username,
                "email": u.email,
                "role": u.role,
                "toko_id": u.toko.id if u.toko else None,
            }
            for u in users
        ],
        key=lambda u: role_priority(u["role"]),
    )

    return users_data


@router.post("/send-invitation", response={200: dict, 400: dict}, auth=AuthBearer())
def send_invitation(request, payload: InvitationRequest):
    user = get_object_or_404(User, id=request.auth)

    if user.role not in ["Pemilik", "Pengelola"]:
        return 400, {"error": "Hanya Pemilik atau Pengelola yang dapat mengirim undangan."}
    if not user.toko:
        return 400, {"error": "User doesn't have a toko."}

    email = payload.email.strip().lower()
    name = payload.name.strip()
    role = payload.role.strip()

    if User.objects.filter(email=email, toko=user.toko).exists():
        return 400, {"error": "User sudah ada di toko ini."}
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

        toko = get_object_or_404(Toko, id=toko_id)

        user, _ = User.objects.get_or_create(email=email, defaults={"username": name, "role": role})
        user.role = role
        user.username = name
        user.toko = toko
        user.save()

        invitation.delete()

        return {"valid": True, "message": "User successfully registered"}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token expired"}
    except jwt.DecodeError:
        return {"valid": False, "error": "Invalid token"}


@router.post("/remove-user-from-toko", response={200: dict, 400: dict, 403: dict}, auth=AuthBearer())
def remove_user_from_toko(request, payload: RemoveUserRequest):
    requester = get_object_or_404(User, id=request.auth)

    if requester.role != "Pemilik":
        return 403, {"error": "Only Pemilik can remove users from toko"}

    user_to_remove = get_object_or_404(User, id=payload.user_id)

    if not requester.toko or requester.toko != user_to_remove.toko:
        return 400, {"error": "User is not in your toko"}
    if requester.id == user_to_remove.id:
        return 400, {"error": "Cannot remove yourself from your own toko"}

    user_to_remove.toko = Toko.objects.create()
    user_to_remove.role = "Pemilik"
    user_to_remove.save()

    return {
        "message": f"User {user_to_remove.username} removed from toko",
        "user": {
            "id": user_to_remove.id,
            "name": user_to_remove.username,
            "email": user_to_remove.email,
            "role": user_to_remove.role,
        },
    }


@router.get("/pending-invitations", response={200: list[dict], 404: dict}, auth=AuthBearer())
def get_pending_invitations(request):
    user = get_object_or_404(User, id=request.auth)

    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}

    invitations = Invitation.objects.filter(toko=user.toko)

    return 200, [
        {
            "id": invitation.id,
            "email": invitation.email,
            "name": invitation.name,
            "role": invitation.role,
            "created_by": invitation.created_by.username,
            "created_at": invitation.expires_at - timedelta(days=1),
            "expires_at": invitation.expires_at,
        }
        for invitation in invitations
    ]


@router.delete("/delete-invitation/{invitation_id}", response={200: dict, 404: dict, 403: dict}, auth=AuthBearer())
def delete_invitation(request, invitation_id: int):
    user = get_object_or_404(User, id=request.auth)

    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}

    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.toko != user.toko:
        return 403, {"message": "You don't have permission to delete this invitation"}

    invitation.delete()
    return 200, {"message": "Invitation deleted successfully"}