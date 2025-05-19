from django.shortcuts import get_object_or_404
from django.db.utils import IntegrityError
from django.conf import settings
import jwt
from .models import User, Toko, Invitation
from ninja_jwt.tokens import RefreshToken, AccessToken


class UserRepository:
    @staticmethod
    def get_user_by_id(user_id):
        return get_object_or_404(User, id=user_id)
    
    @staticmethod
    def get_or_create_user(email, defaults=None):
        return User.objects.get_or_create(email=email, defaults=defaults or {})
    
    @staticmethod
    def get_users_by_toko(toko):
        return User.objects.select_related("toko").filter(toko=toko)
    
    @staticmethod
    def get_user_with_new_toko(user_id):
        user = get_object_or_404(User, id=user_id)
        user.toko = Toko.objects.create()
        user.role = "Pemilik"
        user.save()
        return user


class TokoRepository:
    @staticmethod
    def get_toko_by_id(toko_id):
        return get_object_or_404(Toko, id=toko_id)
    
    @staticmethod
    def create_toko():
        return Toko.objects.create()


class InvitationRepository:
    @staticmethod
    def create_invitation(email, name, role, toko, user, token, expiration):
        try:
            return Invitation.objects.create(
                email=email,
                name=name,
                role=role,
                toko=toko,
                created_by=user,
                token=token,
                expires_at=expiration,
            )
        except IntegrityError:
            return None
    
    @staticmethod
    def get_invitation_by_id(invitation_id):
        return get_object_or_404(Invitation, id=invitation_id)
    
    @staticmethod
    def get_invitation_by_email_and_token(email, token):
        return Invitation.objects.filter(email=email, token=token).first()
    
    @staticmethod
    def get_invitations_by_toko(toko):
        return Invitation.objects.select_related("created_by").filter(toko=toko)
    
    @staticmethod
    def delete_invitation(invitation):
        invitation.delete()


class TokenRepository:
    @staticmethod
    def create_jwt_token(payload, expiration=None):
        if expiration:
            payload["exp"] = expiration
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    @staticmethod
    def decode_jwt_token(token):
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    
    @staticmethod
    def create_refresh_token_for_user(user):
        return RefreshToken.for_user(user)
    
    @staticmethod
    def get_access_token(token_string):
        return AccessToken(token_string)
    
    @staticmethod
    def get_refresh_token(token_string):
        return RefreshToken(token_string)