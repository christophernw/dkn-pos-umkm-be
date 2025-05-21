from silk.profiling.profiler import silk_profile

from ninja import Router

from produk.api import AuthBearer
from .schemas import (
    RemoveUserRequest,
    SessionData,
    RefreshTokenRequest,
    TokenValidationRequest,
    InvitationRequest,
    LogoutRequest,
    LogoutResponse,
)
from .services import AuthService, BPRService, UserService, InvitationService

router = Router()

# authentication/api.py
@router.post("/process-session")
def process_session(request, session_data: SessionData):
    return AuthService.process_user_session(session_data.user)


@router.post("/refresh-token", response={200: dict, 401: dict})
def refresh_token(request, refresh_data: RefreshTokenRequest):
    result, error = AuthService.refresh_token(refresh_data.refresh)
    if error:
        return 401, {"error": error}
    return result


@router.post("/validate-token")
def validate_token(request, token_data: TokenValidationRequest):
    return AuthService.validate_token(token_data.token)


@router.get("/get-users", response={200: list[dict], 401: dict}, auth=AuthBearer())
@silk_profile(name='Get Users Profilling')
def get_users(request):
    return UserService.get_users_for_toko(request.auth)


@router.post("/send-invitation", response={200: dict, 400: dict}, auth=AuthBearer())
def send_invitation(request, payload: InvitationRequest):
    result, error = InvitationService.send_invitation(
        request.auth, 
        payload.email, 
        payload.name, 
        payload.role
    )
    if error:
        return 400, {"error": error}
    return 200, result


@router.post("/validate-invitation")
def validate_invitation(request, payload: TokenValidationRequest):
    return InvitationService.validate_invitation(payload.token)


@router.post("/remove-user-from-toko", response={200: dict, 400: dict, 403: dict}, auth=AuthBearer())
def remove_user_from_toko(request, payload: RemoveUserRequest):
    result, error = UserService.remove_user_from_toko(request.auth, payload.user_id)
    if not result:
        status_code = 403 if "Only Pemilik" in error else 400
        return status_code, {"error": error}
    return result


@router.get("/pending-invitations", response={200: list[dict], 404: dict}, auth=AuthBearer())
@silk_profile(name='Get Pending Invitatoin Users Profilling')
def get_pending_invitations(request):
    result, error = InvitationService.get_pending_invitations(request.auth)
    if error:
        return 404, {"message": error}
    return 200, result


@router.delete("/delete-invitation/{invitation_id}", response={200: dict, 404: dict, 403: dict}, auth=AuthBearer())
def delete_invitation(request, invitation_id: int):
    result, error = InvitationService.delete_invitation(request.auth, invitation_id)
    if not result:
        status_code = 403 if "permission" in error else 404
        return status_code, {"message": error}
    return 200, result

@router.post("/logout", response={200: LogoutResponse, 401: dict})
def logout(request, logout_data: LogoutRequest):
    """Logout a user by blacklisting their refresh token."""
    result, error = AuthService.logout(logout_data.refresh)
    if error:
        return 401, {"error": error}
    return 200, result

@router.get("/bpr/shops", response={200: list[dict], 403: dict}, auth=AuthBearer())
def get_all_shops_for_bpr(request):
    shops, error = BPRService.get_all_shops(request.auth)
    if error:
        return 403, {"error": error}
    return 200, shops


@router.get("/bpr/shop/{shop_id}", response={200: dict, 403: dict, 404: dict}, auth=AuthBearer())
def get_shop_info_for_bpr(request, shop_id: int):
    shop_info, error = BPRService.get_shop_info(request.auth, shop_id)
    if error == "Only BPR users can access this endpoint":
        return 403, {"error": error}
    elif error == "Shop not found":
        return 404, {"error": error}
    return 200, shop_info

@router.get("/me", response={200: dict, 404: dict}, auth=AuthBearer())
@silk_profile(name='Get User Info')
def get_user_info(request):
    """Get detailed information about the currently authenticated user"""
    result, error = UserService.get_user_info(request.auth)
    if error:
        return 404, {"error": error}
    return 200, result