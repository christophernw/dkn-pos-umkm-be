from datetime import timedelta
from unittest.mock import patch
from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase
import jwt
from authentication.models import Invitation, Toko, User
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.api import router 
from ninja.testing import TestClient
from django.utils.timezone import now

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
        self.refresh = RefreshToken.for_user(self.user)

    def test_process_session_existing_user(self):
        response = self.client.post("/process-session", json={"user": {"email": "test@example.com", "name": "testuser"}})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_process_session_new_user(self):
        response = self.client.post("/process-session", json={"user": {"email": "new@example.com", "name": "newuser"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "new@example.com")

    def test_refresh_token_valid(self):
        response = self.client.post("/refresh-token", json={"refresh": str(self.refresh)})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_refresh_token_invalid(self):
        response = self.client.post("/refresh-token", json={"refresh": "invalid_token"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_validate_token_valid(self):
        access_token = str(self.refresh.access_token)
        response = self.client.post("/validate-token", json={"token": access_token})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])

    def test_validate_token_invalid(self):
        response = self.client.post("/validate-token", json={"token": "invalid_token"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

class GetUsersTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password", role="Pemilik", toko=self.toko
        )
        self.karyawan = User.objects.create_user(
            username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", toko=self.toko
        )

    def test_get_users_as_owner(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 2)
        roles = [user["role"] for user in users]
        self.assertIn("Pemilik", roles)
        self.assertIn("Karyawan", roles)

    def test_get_users_as_karyawan(self):
        refresh = RefreshToken.for_user(self.karyawan)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 2)
        roles = [user["role"] for user in users]
        self.assertIn("Pemilik", roles)
        self.assertIn("Karyawan", roles)

        def test_get_users_as_administrator(self):
            # Tambahkan Administrator ke toko yang sama
            admin = User.objects.create_user(
                username="admin",
                email="admin@example.com",
                password="password",
                role="Administrator",
                toko=self.toko
            )
            refresh = RefreshToken.for_user(admin)
            access_token = str(refresh.access_token)

            response = self.client.get(
                "/get-users", headers={"Authorization": f"Bearer {access_token}"}
            )
            self.assertEqual(response.status_code, 200)

            users = response.json()
            self.assertEqual(len(users), 3)

            roles = [user["role"] for user in users]
            self.assertIn("Pemilik", roles)
            self.assertIn("Administrator", roles)
            self.assertIn("Karyawan", roles)


class SendInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik")
        self.refresh = RefreshToken.for_user(self.owner)

    def test_send_invitation_success(self):
        response = self.client.post("/send-invitation", json={
            "name": "New User",
            "email": "newuser@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Invitation sent")

    def test_send_invitation_existing_user(self):
        User.objects.create_user(username="existing", email="existing@example.com", password="password", role="Karyawan")

        response = self.client.post("/send-invitation", json={
            "name": "Existing User",
            "email": "existing@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User sudah ada di toko ini.")

    def test_send_invitation_already_invited(self):
        Invitation.objects.create(
            email="invited@example.com", name="Invited User", role="Karyawan",
            owner=self.owner, token="dummy", expires_at=now() + timedelta(days=1)
        )

        response = self.client.post("/send-invitation", json={
            "name": "Invited User",
            "email": "invited@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Undangan sudah dikirim ke email ini.")

    @patch("authentication.models.Invitation.objects.create", side_effect=IntegrityError)
    def test_send_invitation_integrity_error(self, mock_create):
        response = self.client.post("/send-invitation", json={
            "name": "Error User",
            "email": "error@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invitation already exists.")


class ValidateInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik")
        self.refresh = RefreshToken.for_user(self.owner)

    def test_validate_invitation_success(self):
        expiration = now() + timedelta(days=1)
        token_payload = {"email": "newuser@example.com", "name": "New User", "role": "Karyawan", "owner_id": self.owner.id, "exp": expiration}
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(email="newuser@example.com", name="New User", role="Karyawan",
                                  owner=self.owner, token=token, expires_at=expiration)

        response = self.client.post("/validate-invitation", json={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "User successfully registered")
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_validate_invitation_expired(self):
        expired_time = now() - timedelta(days=1)
        token_payload = {"email": "expired@example.com", "name": "Expired User", "role": "Karyawan", "owner_id": self.owner.id, "exp": expired_time}
        expired_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")

        Invitation.objects.create(email="expired@example.com", name="Expired User", role="Karyawan",
                                  owner=self.owner, token=expired_token, expires_at=expired_time)

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
        token_payload = {"email": "notfound@example.com", "name": "NotFound", "role": "Karyawan", "owner_id": self.owner.id, "exp": expiration}
        token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        
        response = self.client.post("/validate-invitation", json={"token": token})
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["error"], "Invalid invitation")