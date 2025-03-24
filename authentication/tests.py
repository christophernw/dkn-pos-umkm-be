from django.test import TestCase
from authentication.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.api import router 
from ninja.testing import TestClient

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
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik")
        self.karyawan = User.objects.create_user(username="karyawan", email="karyawan@example.com", password="password", role="Karyawan")
        self.refresh = RefreshToken.for_user(self.owner)
        
    def test_add_user_valid(self):
        response = self.client.post("/add-user", json={
            "name": "New Karyawan",
            "email": "new_karyawan@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "User berhasil ditambahkan.")
        
    def test_add_user_invalid(self):
        response = self.client.post("/add-user", json={
            "name": "Karyawan Duplicate",
            "email": "karyawan@example.com", 
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("User sudah terdaftar", response.json()["error"])


class GetUsersTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik")
        self.karyawan = User.objects.create_user(username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", owner=self.owner)
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