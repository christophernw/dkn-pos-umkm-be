from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.api import router  # Adjust import if needed
from ninja.testing import TestClient
from rest_framework.test import APIClient
from django.urls import reverse

from authentication.models import Business, BusinessUser

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

class AddUserTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # Buat pengguna pemilik bisnis
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password")
        self.owner_token = str(RefreshToken.for_user(self.owner).access_token)

        # Buat bisnis terkait pemilik
        self.business = Business.objects.create(owner=self.owner)

    def test_add_user_success(self):
        """Menguji apakah owner bisa menambahkan pengguna baru ke bisnisnya."""
        payload = {
            "name": "newuser",
            "email": "newuser@example.com",
            "role": "Karyawan"
        }

        response = self.client.post(
            "/add-user",
            json=payload,
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "newuser@example.com")
        self.assertEqual(response.json()["user"]["role"], "Karyawan")

    def test_add_user_existing_email(self):
        """Menguji penambahan user dengan email yang sudah ada."""
        User.objects.create_user(username="existinguser", email="existing@example.com", password="password")

        payload = {
            "name": "existinguser",
            "email": "existing@example.com",
            "role": "Karyawan"
        }

        response = self.client.post(
            "/add-user",
            json=payload,
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())