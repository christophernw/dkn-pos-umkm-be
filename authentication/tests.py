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

    def test_process_session_cache_hit(self):
        # Prepare a fake cached response
        cache_key = f"user_session_{self.user.email}"
        cached_response = {
            "message": "Login successful (cached)",
            "refresh": "cached_refresh_token",
            "access": "cached_access_token",
            "user": {
                "id": self.user.id,
                "email": self.user.email,
                "name": self.user.username,
                "role": self.user.role,
                "toko_id": self.user.toko.id if self.user.toko else None,
                "is_bpr": False,
            },
        }
        cache.set(cache_key, cached_response, timeout=3600)
        response = self.client.post("/process-session", json={"user": {"email": self.user.email, "name": self.user.username}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), cached_response)

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
        
    def test_remove_user_from_toko_cannot_remove_self(self):
        # Owner tries to remove themselves
        payload = {"user_id": self.owner.id}
        response = self.client.post(
            "/remove-user-from-toko",
            json=payload,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Cannot remove yourself from your own toko")

    def test_get_users_with_pengelola(self):
        # Add a Pengelola user
        User.objects.create_user(
            username="pengelola",
            email="pengelola@example.com",
            password="password",
            role="Pengelola",
            toko=self.toko
        )
        response = self.client.get("/get-users", headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})
        self.assertEqual(response.status_code, 200)
        users = response.json()
        roles = [user["role"] for user in users]
        # Should be sorted: Pemilik, Pengelola, Karyawan
        self.assertEqual(roles, ["Pemilik", "Pengelola", "Karyawan"])

    def test_remove_user_from_toko_user_not_found(self):
        # Try to remove a user that does not exist
        payload = {"user_id": 99999}
        response = self.client.post(
            "/remove-user-from-toko",
            json=payload,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "User not found")

    def test_remove_user_from_toko_user_not_in_same_toko(self):
        # Create a user in a different toko
        other_toko = Toko.objects.create()
        other_user = User.objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="password",
            role="Karyawan",
            toko=other_toko
        )
        payload = {"user_id": other_user.id}
        response = self.client.post(
            "/remove-user-from-toko",
            json=payload,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "User is not in your toko")

    def test_remove_user_from_toko_requester_not_pemilik(self):
        # Create a Pengelola user as requester
        pengelola = User.objects.create_user(
            username="pengelola2",
            email="pengelola2@example.com",
            password="password",
            role="Pengelola",
            toko=self.toko
        )
        refresh = RefreshToken.for_user(pengelola)
        payload = {"user_id": self.karyawan.id}
        response = self.client.post(
            "/remove-user-from-toko",
            json=payload,
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Only Pemilik can remove users from toko")

    def test_remove_user_from_toko_success_response_fields(self):
        # Owner removes karyawan from toko
        payload = {"user_id": self.karyawan.id}
        response = self.client.post(
            "/remove-user-from-toko",
            json=payload,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], self.karyawan.email)
        self.assertEqual(data["user"]["name"], self.karyawan.username)

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

    def test_validate_invitation_not_found(self):
        # Create a valid token but do not create an invitation in DB
        token = jwt.encode(
            {
                "email": "notfound@example.com",
                "name": "Not Found",
                "role": "Karyawan",
                "toko_id": self.toko.id,
                "exp": now() + timedelta(days=1)
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        response = self.client.post("/validate-invitation", json={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Invalid invitation")

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

    def test_send_invitation_no_toko(self):
        user_no_toko = User.objects.create_user(
            username="notoko",
            email="notoko2@example.com",
            password="password",
            role="Pemilik"
        )
        refresh = RefreshToken.for_user(user_no_toko)
        invitation_data = {
            "name": "Invite",
            "email": "invite2@example.com",
            "role": "Karyawan"
        }
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "User doesn't have a toko.")

    def test_send_invitation_user_already_in_toko(self):
        # Owner tries to invite an existing user in the same toko
        invitation_data = {
            "name": self.owner.username,
            "email": self.owner.email,
            "role": "Pemilik"
        }
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "User sudah ada di toko ini.")

    @patch("authentication.api.Invitation.objects.create")
    def test_send_invitation_integrity_error(self, mock_create):
        mock_create.side_effect = IntegrityError()
        invitation_data = {
            "name": "Invite",
            "email": "invite3@example.com",
            "role": "Karyawan"
        }
        response = self.client.post(
            "/send-invitation",
            json=invitation_data,
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Invitation already exists.")

    def test_validate_invitation_existing_user_role_update(self):
        # Create an existing user
        user = User.objects.create_user(
            username="oldname",
            email="updateuser@example.com",
            password="password",
            role="Karyawan",
            toko=self.toko
        )
        # Create invitation token with new role and name
        token = jwt.encode(
            {
                "email": "updateuser@example.com",
                "name": "newname",
                "role": "Pengelola",
                "toko_id": self.toko.id,
                "exp": now() + timedelta(days=1)
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        Invitation.objects.create(
            email="updateuser@example.com",
            name="newname",
            role="Pengelola",
            toko=self.toko,
            created_by=self.owner,
            token=token,
            expires_at=now() + timedelta(days=1)
        )
        response = self.client.post("/validate-invitation", json={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        user.refresh_from_db()
        self.assertEqual(user.role, "Pengelola")
        self.assertEqual(user.username, "newname")

    def test_get_pending_invitations_no_toko(self):
        user_no_toko = User.objects.create_user(
            username="notoko",
            email="notoko3@example.com",
            password="password",
            role="Pemilik"
        )
        refresh = RefreshToken.for_user(user_no_toko)
        response = self.client.get(
            "/pending-invitations",
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "User doesn't have a toko")

    def test_delete_invitation_no_toko(self):
        user_no_toko = User.objects.create_user(
            username="notoko",
            email="notoko4@example.com",
            password="password",
            role="Pemilik"
        )
        refresh = RefreshToken.for_user(user_no_toko)
        response = self.client.delete(
            "/delete-invitation/1",
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "User doesn't have a toko")

    def test_delete_invitation_wrong_toko(self):
        # Create another toko and invitation
        other_toko = Toko.objects.create()
        other_owner = User.objects.create_user(
            username="otherowner",
            email="otherowner@example.com",
            password="password",
            role="Pemilik",
            toko=other_toko
        )
        invitation = Invitation.objects.create(
            email="invite4@example.com",
            name="Invite 4",
            role="Karyawan",
            toko=other_toko,
            created_by=other_owner,
            token="othertoken",
            expires_at=now() + timedelta(days=1)
        )
        response = self.client.delete(
            f"/delete-invitation/{invitation.id}",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "You don't have permission to delete this invitation")

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
        User.objects.create_user(
            username="shopowner",
            email="shopowner@example.com",
            toko=toko,
            role="Pemilik"
        )
        
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

    def test_bpr_shops_non_bpr_user(self):
        # Create a non-BPR user
        user = User.objects.create_user(
            username="notbpr",
            email="notbpr@example.com",
            password="password",
            role="Pemilik",
            toko=Toko.objects.create()
        )
        refresh = RefreshToken.for_user(user)
        response = self.client.get(
            "/bpr/shops",
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Only BPR users can access this endpoint")

    def test_bpr_shop_info_non_bpr_user(self):
        # Create a non-BPR user
        user = User.objects.create_user(
            username="notbpr",
            email="notbpr@example.com",
            password="password",
            role="Pemilik",
            toko=Toko.objects.create()
        )
        refresh = RefreshToken.for_user(user)
        
        # Try to access shop info with non-BPR user
        response = self.client.get(
            "/bpr/shop/1",
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Only BPR users can access this endpoint")

    @patch('authentication.api.Toko.objects.all')
    def test_bpr_shops_general_exception(self, mock_toko_all):
        # Mock the Toko.objects.all() to raise an exception
        mock_toko_all.side_effect = Exception("Test exception")
        
        response = self.client.get(
            "/bpr/shops",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Access denied")

    @patch('authentication.api.Toko.objects.get')
    def test_bpr_shop_info_general_exception(self, mock_toko_get):
        # Mock the Toko.objects.get() to raise DoesNotExist exception
        mock_toko_get.side_effect = Toko.DoesNotExist()
        
        response = self.client.get(
            "/bpr/shop/0",
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Access denied")