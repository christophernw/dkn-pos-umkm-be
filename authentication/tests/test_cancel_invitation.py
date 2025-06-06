from django.test import TestCase
from django.utils.timezone import now

from datetime import timedelta
import jwt
from django.conf import settings
from ninja.testing import TestClient

from authentication.models import Invitation, User, Toko
from authentication.api import router

class DeleteInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        
        self.toko = Toko.objects.create()
        
        self.owner = User.objects.create_user(
            username="owner", 
            email="owner@example.com", 
            password="password"
        )
        self.owner.role = "Pemilik"
        self.owner.toko = self.toko
        self.owner.save()
        
        payload = {"user_id": self.owner.id}
        self.token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        expiration = now() + timedelta(days=1)
        invitation_token = jwt.encode(
            {
                "email": "invited@example.com",
                "name": "Invited User",
                "role": "Karyawan",
                "toko_id": self.toko.id,
                "exp": expiration,
            }, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        
        self.invitation = Invitation.objects.create(
            email="invited@example.com",
            name="Invited User",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner, 
            token=invitation_token,
            expires_at=expiration,
        )

    def test_delete_invitation_success(self):
        response = self.client.delete(
            f"/delete-invitation/{self.invitation.id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Invitation deleted successfully")
        self.assertFalse(Invitation.objects.filter(id=self.invitation.id).exists())

    def test_delete_invitation_not_found(self):
        non_existent_invitation_id = 99999

        response = self.client.delete(
            f"/delete-invitation/{non_existent_invitation_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_invitation_wrong_toko(self):
        other_toko = Toko.objects.create()
        other_owner = User.objects.create_user(
            username="otherowner", 
            email="otherowner@example.com", 
            password="password"
        )
        other_owner.role = "Pemilik"
        other_owner.toko = other_toko
        other_owner.save()
        
        expiration = now() + timedelta(days=1)
        other_invitation_token = jwt.encode(
            {
                "email": "otherinvited@example.com",
                "name": "Other Invited",
                "role": "Karyawan",
                "toko_id": other_toko.id,
                "exp": expiration,
            }, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        
        other_invitation = Invitation.objects.create(
            email="otherinvited@example.com",
            name="Other Invited",
            role="Karyawan",
            toko=other_toko,
            created_by=other_owner,
            token=other_invitation_token,
            expires_at=expiration,
        )

        response = self.client.delete(
            f"/delete-invitation/{other_invitation.id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "You don't have permission to delete this invitation")

    def test_delete_invitation_user_without_toko(self):
        user_without_toko = User.objects.create_user(
            username="no_toko", 
            email="no_toko@example.com", 
            password="password"
        )
        user_without_toko.role = "Pemilik"
        user_without_toko.save()
        
        payload = {"user_id": user_without_toko.id}
        token_no_toko = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        response = self.client.delete(
            f"/delete-invitation/{self.invitation.id}",
            headers={"Authorization": f"Bearer {token_no_toko}"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "User doesn't have a toko")


