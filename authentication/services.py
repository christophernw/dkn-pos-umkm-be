from django.utils.timezone import now
from datetime import timedelta
from ninja_jwt.exceptions import TokenError
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
import jwt

from backend import settings
from .repositories import UserRepository, TokoRepository, InvitationRepository, TokenRepository
from django.core.cache import cache

class AuthService:
    @staticmethod
    def process_user_session(user_data):
        email = user_data.get("email")
        cache_key = f"user_session_{email}"

        cached_user = cache.get(cache_key)
        if cached_user:
            return cached_user

        user, created = UserRepository.get_or_create_user(
            email=email,
            defaults={
                "username": user_data.get("name"),
                "is_active": True,
            },
        )

        if created:
            toko = TokoRepository.create_toko()
            user.toko = toko
            user.save()

        refresh = TokenRepository.create_refresh_token_for_user(user)

        is_bpr = (email == settings.BPR_EMAIL)

        response_data = {
            "message": "Login successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.username,
                "role": user.role,
                "toko_id": user.toko.id if user.toko else None,
                "is_bpr": is_bpr,
            },
        }

        cache.set(cache_key, response_data, timeout=3600)

        return response_data

    @staticmethod
    def refresh_token(refresh_token_str):
        try:
            refresh = TokenRepository.get_refresh_token(refresh_token_str)
            return {"access": str(refresh.access_token), "refresh": str(refresh)}, None
        except TokenError as e:
            return None, f"Invalid refresh token: {str(e)}"

    @staticmethod
    def validate_token(token_str):
        try:
            TokenRepository.get_access_token(token_str)
            return {"valid": True}
        except TokenError:
            return {"valid": False}

    @staticmethod
    def logout(refresh_token_str):
        """Blacklist the refresh token to logout the user."""
        try:
            # Check for None or empty token
            if not refresh_token_str:
                return None, "Token is missing or invalid"
                
            # Get the refresh token object to validate it
            refresh = TokenRepository.get_refresh_token(refresh_token_str)
            
            # For ninja_jwt, we need to:
            # 1. Find or create an outstanding token record
            # 2. Create a blacklist entry for that token
            
            # First, try to find if token is already registered
            try:
                outstanding = OutstandingToken.objects.get(token=refresh_token_str)
            except OutstandingToken.DoesNotExist:
                # Token not found in database, so it can't be blacklisted
                return {"message": "Token not found or already expired"}, None
            
            # Check if already blacklisted
            if BlacklistedToken.objects.filter(token=outstanding).exists():
                return {"message": "Token already blacklisted"}, None
                
            # Create blacklist entry
            BlacklistedToken.objects.create(token=outstanding)
            
            return {"message": "Successfully logged out"}, None
        except Exception as e:
            # Catch any other exceptions
            return None, f"Logout failed: {str(e)}"
        
class UserService:
    @staticmethod
    def get_users_for_toko(user_id):
        user = UserRepository.get_user_by_id(user_id)

        users_qs = (
            UserRepository.get_users_by_toko(user.toko)
            if user.toko
            else UserRepository.get_users_by_toko(None).filter(id=user.id)
        )

        role_priority = {"Pemilik": 0, "Pengelola": 1, "Karyawan": 2}

        return sorted(
            [
                {
                    "id": u.id,
                    "name": u.username,
                    "email": u.email,
                    "role": u.role,
                    "toko_id": u.toko.id if u.toko else None,
                }
                for u in users_qs
            ],
            key=lambda u: role_priority.get(u["role"], 3),
        )

    @staticmethod
    def remove_user_from_toko(requester_id, user_id_to_remove):
        requester = UserRepository.get_user_by_id(requester_id)
        
        if requester.role != "Pemilik":
            return None, "Only Pemilik can remove users from toko"

        user_to_remove = UserRepository.get_user_by_id(user_id_to_remove)

        if not requester.toko or requester.toko != user_to_remove.toko:
            return None, "User is not in your toko"
        
        if requester.id == user_to_remove.id:
            return None, "Cannot remove yourself from your own toko"

        user_to_remove = UserRepository.get_user_with_new_toko(user_to_remove.id)

        return {
            "message": f"User {user_to_remove.username} removed from toko",
            "user": {
                "id": user_to_remove.id,
                "name": user_to_remove.username,
                "email": user_to_remove.email,
                "role": user_to_remove.role,
            },
        }, None


class InvitationService:
    @staticmethod
    def send_invitation(user_id, email, name, role):
        user = UserRepository.get_user_by_id(user_id)

        if user.role not in ["Pemilik", "Pengelola"]:
            return None, "Hanya Pemilik atau Pengelola yang dapat mengirim undangan."
        
        if not user.toko:
            return None, "User doesn't have a toko."

        email = email.strip().lower()
        name = name.strip()
        role = role.strip()

        if UserRepository.get_users_by_toko(user.toko).filter(email=email).exists():
            return None, "User sudah ada di toko ini."
        
        if InvitationRepository.get_invitations_by_toko(user.toko).filter(email=email).exists():
            return None, "Undangan sudah dikirim ke email ini."

        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": email,
            "name": name,
            "role": role,
            "toko_id": user.toko.id,
            "exp": expiration,
        }
        token = TokenRepository.create_jwt_token(token_payload)

        invitation = InvitationRepository.create_invitation(
            email=email,
            name=name,
            role=role,
            toko=user.toko,
            user=user,
            token=token,
            expiration=expiration,
        )
        
        if not invitation:
            return None, "Invitation already exists."
        
        return {"message": "Invitation sent", "token": token}, None

    @staticmethod
    def validate_invitation(token_str):
        try:
            decoded = TokenRepository.decode_jwt_token(token_str)
            email = decoded.get("email")
            name = decoded.get("name")
            role = decoded.get("role")
            toko_id = decoded.get("toko_id")

            invitation = InvitationRepository.get_invitation_by_email_and_token(email, token_str)
            if not invitation:
                return {"valid": False, "error": "Invalid invitation"}

            toko = TokoRepository.get_toko_by_id(toko_id)

            user, created = UserRepository.get_or_create_user(
                email=email, 
                defaults={
                    "username": name, 
                    "role": role,
                    "is_active": True  
                }
            )
            
            if not created and not user.is_active:
                return {"valid": False, "error": "User account is inactive. Please contact administrator."}
                
            user.role = role
            user.username = name
            user.toko = toko
            user.save()

            InvitationRepository.delete_invitation(invitation)

            return {"valid": True, "message": "User successfully registered"}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.DecodeError:
            return {"valid": False, "error": "Invalid token"}

    @staticmethod
    def get_pending_invitations(user_id):
        user = UserRepository.get_user_by_id(user_id)

        if not user.toko:
            return None, "User doesn't have a toko"

        invitations = InvitationRepository.get_invitations_by_toko(user.toko)

        return [
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
        ], None

    @staticmethod
    def delete_invitation(user_id, invitation_id):
        user = UserRepository.get_user_by_id(user_id)

        if not user.toko:
            return None, "User doesn't have a toko"

        invitation = InvitationRepository.get_invitation_by_id(invitation_id)

        if invitation.toko != user.toko:
            return None, "You don't have permission to delete this invitation"

        InvitationRepository.delete_invitation(invitation)
        return {"message": "Invitation deleted successfully"}, None

class BPRService:
    @staticmethod
    def get_all_shops(user_id):
        try:
            user = UserRepository.get_user_by_id(user_id)

            if user.email != settings.BPR_EMAIL:
                return None, "Only BPR users can access this endpoint"

            shops = TokoRepository.get_all_toko()

            if user.toko:
                shops = shops.exclude(id=user.toko.id)

            shops_data = []
            for shop in shops:
                owner = UserRepository.get_owner_of_toko(shop)
                shops_data.append({
                    "id": shop.id,
                    "owner": owner.username if owner else "No owner",
                    "created_at": shop.created_at,
                    "user_count": UserRepository.count_users_in_toko(shop),
                })

            return shops_data, None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None, "Access denied"

    @staticmethod
    def get_shop_info(user_id, shop_id):
        try:
            user = UserRepository.get_user_by_id(user_id)

            if user.email != settings.BPR_EMAIL:
                return None, "Only BPR users can access this endpoint"

            shop = TokoRepository.get_toko_by_id(shop_id)
            if not shop:
                return None, "Shop not found"

            owner = UserRepository.get_owner_of_toko(shop)

            return {
                "id": shop.id,
                "owner": owner.username if owner else "No owner",
                "created_at": shop.created_at,
                "user_count": UserRepository.count_users_in_toko(shop),
            }, None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None, "Access denied"