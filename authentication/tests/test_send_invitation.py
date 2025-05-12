import jwt
from django.db import IntegrityError
from django.test import TestCase
from django.utils.timezone import now
from django.conf import settings
from ninja.testing import TestClient
from datetime import timedelta
from unittest.mock import patch

from authentication.models import Invitation, User, Toko
from authentication.api import router 

class SendInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        # Create a toko
        self.toko = Toko.objects.create()
        
        # Create owner with toko
        self.owner = User.objects.create_user(
            username="owner", 
            email="owner@example.com", 
            password="password"
        )
        self.owner.role = "Pemilik"
        self.owner.toko = self.toko
        self.owner.save()
        
        # Create JWT token for authentication
        self.owner_token = jwt.encode(
            {"user_id": self.owner.id}, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )

    def test_send_invitation_success(self):
        response = self.client.post("/send-invitation", 
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Invitation sent")
        
        # Verify invitation was created in the database
        self.assertTrue(Invitation.objects.filter(email="newuser@example.com").exists())

    def test_send_invitation_existing_user(self):
        # Create a user already in the same toko
        existing_user = User.objects.create_user(
            username="existing", 
            email="existing@example.com", 
            password="password"
        )
        existing_user.role = "Karyawan"
        existing_user.toko = self.toko
        existing_user.save()

        response = self.client.post("/send-invitation", 
            json={
                "name": "Existing User",
                "email": "existing@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User sudah ada di toko ini.")

    def test_send_invitation_already_invited(self):
        # Create an invitation for the same email
        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "invited@example.com",
            "name": "Invited User",
            "role": "Karyawan",
            "toko_id": self.toko.id,
            "exp": expiration,
        }
        invitation_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        
        Invitation.objects.create(
            email="invited@example.com", 
            name="Invited User", 
            role="Karyawan",
            toko=self.toko, 
            created_by=self.owner, 
            token=invitation_token, 
            expires_at=expiration
        )

        response = self.client.post("/send-invitation", 
            json={
                "name": "Invited User",
                "email": "invited@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Undangan sudah dikirim ke email ini.")

    @patch("authentication.models.Invitation.objects.create", side_effect=IntegrityError)
    def test_send_invitation_integrity_error(self, mock_create):
        response = self.client.post("/send-invitation", 
            json={
                "name": "Error User",
                "email": "error@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invitation already exists.")

    def test_send_invitation_user_without_toko(self):
        # Create user without toko
        user_without_toko = User.objects.create_user(
            username="no_toko", 
            email="no_toko@example.com", 
            password="password"
        )
        user_without_toko.role = "Pemilik"
        user_without_toko.save()
        
        # Create token for user without toko
        user_without_toko_token = jwt.encode(
            {"user_id": user_without_toko.id}, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )

        response = self.client.post("/send-invitation", 
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {user_without_toko_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User doesn't have a toko.")

    def test_send_invitation_with_karyawan_role(self):
        # Create a user with "Karyawan" role in the same toko
        karyawan_user = User.objects.create_user(
            username="karyawan", 
            email="karyawan@example.com", 
            password="password"
        )
        karyawan_user.role = "Karyawan"
        karyawan_user.toko = self.toko
        karyawan_user.save()

        # Generate token for this user
        karyawan_token = jwt.encode(
            {"user_id": karyawan_user.id}, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )

        # Attempt to send invitation
        response = self.client.post("/send-invitation", 
            json={
                "name": "Another User",
                "email": "another@example.com",
                "role": "Karyawan"
            }, 
            headers={"Authorization": f"Bearer {karyawan_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Hanya Pemilik atau Pengelola yang dapat mengirim undangan.")
