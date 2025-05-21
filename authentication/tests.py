from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.core.cache import cache
import jwt
from authentication.models import Invitation, User, Toko
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.api import router, process_session
from ninja.testing import TestClient
from django.utils.timezone import now
from authentication.schemas import SessionData

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="password",
            toko=self.toko,
            role="Pemilik"
        )
        self.refresh = RefreshToken.for_user(self.user)

    def test_process_session_existing_user(self):
        response = self.client.post("/process-session", json={"user": {"email": "test@example.com", "name": "testuser"}})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())
        self.assertEqual(response.json()["user"]["email"], "test@example.com")

    def test_process_session_new_user(self):
        response = self.client.post("/process-session", json={"user": {"email": "new@example.com", "name": "newuser"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "new@example.com")
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_process_session_bpr_user(self):
        response = self.client.post("/process-session", json={"user": {"email": settings.BPR_EMAIL, "name": "bpruser"}})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["user"]["is_bpr"])

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

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class GetUsersTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik", toko=self.toko)
        self.karyawan = User.objects.create_user(username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", toko=self.toko)
        self.refresh = RefreshToken.for_user(self.owner)

    def test_get_users_as_owner(self):
        response = self.client.get("/get-users", headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})  
        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertEqual(len(users), 2)
        self.assertTrue(any(user['role'] == "Pemilik" for user in users)) 

    def test_get_users_as_karyawan(self):
        self.refresh = RefreshToken.for_user(self.karyawan) 
        response = self.client.get("/get-users", headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})
        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertEqual(len(users), 2)
        self.assertTrue(any(user['role'] == "Pemilik" for user in users)) 
        self.assertTrue(any(user['role'] == "Karyawan" for user in users))  

    def test_get_users_no_toko(self):
        user_no_toko = User.objects.create_user(
            username="notoko",
            email="notoko@example.com",
            password="password",
            role="Pemilik"
        )
        refresh = RefreshToken.for_user(user_no_toko)
        response = self.client.get("/get-users", headers={"Authorization": f"Bearer {str(refresh.access_token)}"})
        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["email"], "notoko@example.com")

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class InvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password",
            role="Pemilik",
            toko=self.toko
        )
        self.refresh = RefreshToken.for_user(self.owner)

    def test_send_invitation(self):
        invitation_data = {
            "name": "New Invite",
            "email": "invite@example.com",
            "role": "Karyawan"
        }
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
        self.assertTrue(Invitation.objects.filter(email="invite@example.com").exists())

    def test_send_invitation_duplicate(self):
        # First invitation
        invitation_data = {
            "name": "New Invite",
            "email": "invite@example.com",
            "role": "Karyawan"
        }
        self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        
        # Try to send duplicate invitation
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_send_invitation_unauthorized(self):
        karyawan = User.objects.create_user(
            username="karyawan",
            email="karyawan@example.com",
            password="password",
            role="Karyawan",
            toko=self.toko
        )
        refresh = RefreshToken.for_user(karyawan)
        
        invitation_data = {
            "name": "New Invite",
            "email": "invite@example.com",
            "role": "Karyawan"
        }
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_validate_invitation(self):
        # First create an invitation
        invitation_data = {
            "name": "New Invite",
            "email": "invite@example.com",
            "role": "Karyawan"
        }
        invite_response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        token = invite_response.json()["token"]
        
        # Test validation
        response = self.client.post("/validate-invitation", json={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertTrue(User.objects.filter(email="invite@example.com").exists())

    def test_validate_invitation_expired(self):
        # Create expired invitation
        expired_token = jwt.encode(
            {
                "email": "expired@example.com",
                "name": "Expired User",
                "role": "Karyawan",
                "toko_id": self.toko.id,
                "exp": now() - timedelta(days=1)
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        response = self.client.post("/validate-invitation", json={"token": expired_token})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertIn("error", response.json())

    def test_validate_invitation_invalid_token(self):
        response = self.client.post("/validate-invitation", json={"token": "invalid_token"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertIn("error", response.json())

    def test_get_pending_invitations(self):
        # Create some invitations
        Invitation.objects.create(
            email="invite1@example.com",
            name="Invite 1",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner,
            token="test_token_1",
            expires_at=now() + timedelta(days=1)
        )
        
        response = self.client.get(
            "/pending-invitations",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        invitations = response.json()
        self.assertEqual(len(invitations), 1)
        self.assertEqual(invitations[0]["email"], "invite1@example.com")

    def test_delete_invitation(self):
        # Create an invitation
        invitation = Invitation.objects.create(
            email="invite1@example.com",
            name="Invite 1",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner,
            token="test_token_1",
            expires_at=now() + timedelta(days=1)
        )
        
        response = self.client.delete(
            f"/delete-invitation/{invitation.id}",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invitation.objects.filter(id=invitation.id).exists())

    def test_delete_invitation_not_found(self):
        response = self.client.delete(
            "/delete-invitation/999",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.json())

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class BPRTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.bpr_user = User.objects.create_user(
            username="bpruser",
            email=settings.BPR_EMAIL,
            password="password",
            role="Pemilik",
            toko=Toko.objects.create()
        )
        self.refresh = RefreshToken.for_user(self.bpr_user)

    def test_bpr_get_all_shops(self):
        # Create some test shops
        for i in range(3):
            toko = Toko.objects.create()
            User.objects.create_user(
                username=f"shop{i}",
                email=f"shop{i}@example.com",
                toko=toko,
                role="Pemilik"
            )
        
        response = self.client.get(
            "/bpr/shops",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        shops = response.json()
        self.assertEqual(len(shops), 3)  # Should get all shops except BPR's own

    def test_bpr_get_shop_info(self):
        # Create a test shop
        toko = Toko.objects.create()
        
        response = self.client.get(
            f"/bpr/shop/{toko.id}",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        shop_info = response.json()
        self.assertEqual(shop_info["id"], toko.id)
        self.assertEqual(shop_info["owner"], "shopowner")

    def test_bpr_access_unauthorized(self):
        # Create non-BPR user
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="password",
            role="Pemilik",
            toko=Toko.objects.create()
        )
        refresh = RefreshToken.for_user(regular_user)
        
        response = self.client.get(
            "/bpr/shops",
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())