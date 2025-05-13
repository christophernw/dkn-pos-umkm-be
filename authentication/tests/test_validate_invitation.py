import jwt
from django.conf import settings
from django.test import TestCase
from django.utils.timezone import now
from ninja.testing import TestClient
from datetime import timedelta

from authentication.models import Invitation, Toko, User
from authentication.api import router 

class ValidateInvitationTests(TestCase):
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

    def test_validate_invitation_success(self):
        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "newuser@example.com", 
            "name": "New User", 
            "role": "Karyawan", 
            "toko_id": self.toko.id,
            "exp": expiration
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(
            email="newuser@example.com", 
            name="New User", 
            role="Karyawan",
            toko=self.toko, 
            created_by=self.owner, 
            token=token, 
            expires_at=expiration
        )

        response = self.client.post("/validate-invitation", json={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "User successfully registered")
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_validate_invitation_expired(self):
        expired_time = now() - timedelta(days=1)
        token_payload = {
            "email": "expired@example.com", 
            "name": "Expired User", 
            "role": "Karyawan", 
            "toko_id": self.toko.id,
            "exp": expired_time
        }
        expired_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(
            email="expired@example.com", 
            name="Expired User", 
            role="Karyawan",
            toko=self.toko, 
            created_by=self.owner, 
            token=expired_token, 
            expires_at=expired_time
        )

        response = self.client.post("/validate-invitation", json={"token": expired_token})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["error"], "Token expired")

    def test_validate_invitation_invalid_token(self):
        response = self.client.post("/validate-invitation", json={"token": "invalid_token"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["error"], "Invalid token")

    def test_validate_invitation_not_found(self):
        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "notfound@example.com", 
            "name": "NotFound", 
            "role": "Karyawan", 
            "toko_id": self.toko.id, 
            "exp": expiration
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        
        response = self.client.post("/validate-invitation", json={"token": token})
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["error"], "Invalid invitation")

    def test_validate_invitation_set_toko_relationship(self):
        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "role": "Karyawan",
            "toko_id": self.toko.id,
            "exp": expiration,
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(
            email="newuser@example.com",
            name="New User",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner,
            token=token,
            expires_at=expiration,
        )

        response = self.client.post("/validate-invitation", json={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "User successfully registered")

        new_user = User.objects.get(email="newuser@example.com")
        self.assertEqual(new_user.toko, self.toko)

    def test_validate_invitation_existing_user_no_toko(self):
        User.objects.create_user(
            username="existing_user",
            email="existing@example.com",
            password="password"
        )
        
        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "existing@example.com",
            "name": "Existing User",
            "role": "Karyawan",
            "toko_id": self.toko.id,
            "exp": expiration,
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(
            email="existing@example.com",
            name="Existing User",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner,
            token=token,
            expires_at=expiration,
        )

        response = self.client.post("/validate-invitation", json={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "User successfully registered")

        updated_user = User.objects.get(email="existing@example.com")
        self.assertEqual(updated_user.toko, self.toko)

    def test_validate_invitation_update_existing_user_role(self):
        User.objects.create_user(
            username="existing_user",
            email="existing@example.com",
            password="password",
            role="Karyawan",
        )

        expiration = now() + timedelta(days=1)
        token_payload = {
            "email": "existing@example.com",
            "name": "Existing User",
            "role": "Pengelola",
            "toko_id": self.toko.id,
            "exp": expiration,
        }
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(
            email="existing@example.com",
            name="Existing User",
            role="Pengelola",
            toko=self.toko,
            created_by=self.owner,
            token=token,
            expires_at=expiration,
        )

        response = self.client.post("/validate-invitation", json={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "User successfully registered")

        updated_user = User.objects.get(email="existing@example.com")
        self.assertEqual(updated_user.role, "Pengelola")
        self.assertEqual(updated_user.toko, self.toko)

