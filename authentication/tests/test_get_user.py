from django.conf import settings
from django.test import TestCase
from django.utils import timezone
import jwt
from rest_framework_simplejwt.tokens import RefreshToken
from ninja.testing import TestClient
from datetime import timedelta

from authentication.models import Toko, User
from authentication.api import router 

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

    def test_get_users_as_admin(self):
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            role="Pengelola",  
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
        self.assertIn("Pengelola", roles)
        self.assertIn("Karyawan", roles)

    def test_get_users_without_toko(self):
        user_without_toko = User.objects.create_user(
            username="no_toko_user", email="no_toko@example.com", password="password", toko=None
        )

        refresh = RefreshToken.for_user(user_without_toko)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )

        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["id"], user_without_toko.id)
        self.assertIsNone(users[0]["toko_id"])

    def test_get_users_expired_token(self):
        payload = {
            "user_id": self.owner.id,
            "exp": timezone.now() - timedelta(days=1) 
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(response.status_code, 401) 

