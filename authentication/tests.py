from django.test import TestCase
from ninja.testing import TestClient
from .api import router
import json
from django.contrib.auth.models import User
from ninja_jwt.tokens import RefreshToken

class TestAuth(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.client.post("/register", data=json.dumps({
            "phone_number": "08123456789",
            "first_name": "Christo",
            "last_name": "Wijaya",
            "password": "waterseven1030"
        }))


    def test_register(self):
        response = self.client.post(
            "/register",
            data=json.dumps({
                "phone_number": "1234567890",
                "first_name": "John",
                "last_name": "Doe",
                "password": "password"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Akun berhasil dibuat")
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())


    def test_register_existing(self):
        response = self.client.post("/register", data=json.dumps({
            "phone_number": "08123456789",
            "first_name": "Christo",
            "last_name": "Wijaya",
            "password": "waterseven1030"
        }))

        self.assertEqual(response.status_code, 400)


    def test_register_invalid_phone_number(self):
        response = self.client.post("/register", data=json.dumps({
            "phone_number": "12345",
            "first_name": "John",
            "last_name": "Doe",
            "password": "password"
        }))
        self.assertEqual(response.status_code, 400)

        response2 = self.client.post("/register", data=json.dumps({
            "phone_number": "12345a",
            "first_name": "John",
            "last_name": "Doe",
            "password": "password"
        }))
        self.assertEqual(response2.status_code, 400)

        response3 = self.client.post("/register", data=json.dumps({
            "phone_number": "123456789012345",
            "first_name": "John",
            "last_name": "Doe",
            "password": "password"
        }))
        self.assertEqual(response3.status_code, 400)


    def test_login(self):
        response = self.client.post("/login", data=json.dumps({
            "phone_number": "08123456789",
            "password": "waterseven1030"
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Login berhasil")
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())


    def test_login_password_invalid(self):
        response = self.client.post("/login", data=json.dumps({
            "phone_number": "08123456789",
            "password": "wrongpassword"
        }))
        self.assertEqual(response.status_code, 404)


    def test_login_user_not_found(self):
        response = self.client.post("/login", data=json.dumps({
            "phone_number": "1234567890",
            "password": "password"
        }))
        self.assertEqual(response.status_code, 404)


    def test_refresh(self):
        login_res = self.client.post("/login", data=json.dumps({
            "phone_number": "08123456789",
            "password": "waterseven1030"
        }))
        tokens = login_res.json()
        refresh = tokens["refresh"]

        response = self.client.post("/refresh", data=json.dumps({
            "refresh": refresh
        }))
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())


    def test_refresh_invalid(self):
        response = self.client.post("/refresh", data=json.dumps({
            "refresh": "invalidtoken"
        }))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Token invalid atau telah kadaluarsa")


    def test_refresh_with_deleted_user(self):
        user = User.objects.create_user(username="testuser", password="password123")
        refresh_token = RefreshToken.for_user(user)
    
        user.delete()
    
        response = self.client.post("/refresh", data=json.dumps({"refresh": str(refresh_token)}))
    
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Pengguna tidak ditemukan atau token tidak valid")


    def test_me(self):
        login_res = self.client.post("/login", data=json.dumps({
            "phone_number": "08123456789",
            "password": "waterseven1030"
        }))
        tokens = login_res.json()
        access = tokens["access"]

        response = self.client.get("/me", headers={"Authorization": f"Bearer {access}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone_number"], "08123456789")
        self.assertEqual(response.json()["first_name"], "Christo")
        self.assertEqual(response.json()["last_name"], "Wijaya")


    def test_me_invalid(self):
        response = self.client.get("/me", headers={"Authorization ": "Bearer invalidtoken"})
        self.assertEqual(response.status_code, 401)

    
    def test_validate_token(self):
        login_res = self.client.post("/login", data=json.dumps({
            "phone_number": "08123456789",
            "password": "waterseven1030"
        }), content_type='application/json')
        tokens = login_res.json()
        access = tokens["access"]

        response = self.client.post("/validate", headers={"Authorization": f"Bearer {access}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Token valid")


    def test_validate_invalid(self):
        response = self.client.post("/validate", headers={"Authorization": "Bearer invalidtoken"})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("message", response.json())


    def test_validate_wrong_method(self):
        response = self.client.get("/validate", headers={"Authorization": "Bearer invalidtoken"})
        self.assertEqual(response.status_code, 405)


    def test_process_session_new_user(self):
        """Test Google sign-in process when user doesn't exist"""
        response = self.client.post(
            "/process-session",
            data=json.dumps({
                "user": {
                    "name": "Google User",
                    "email": "google@example.com"
                }
            }),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Login successful")
        self.assertIn("refresh", response.json())
        self.assertIn("access", response.json())
        
        # Verify user was created
        user = User.objects.get(email="google@example.com")
        self.assertEqual(user.username, "Google User")

    def test_process_session_existing_user(self):
        """Test Google sign-in process when user already exists"""
        # First create a user
        existing_user = User.objects.create_user(
            username="Existing Google User",
            email="existing@example.com"
        )
        
        # Then simulate the process-session call
        response = self.client.post(
            "/process-session",
            data=json.dumps({
                "user": {
                    "name": "Some Name", # Different name to verify it isn't changed
                    "email": "existing@example.com"
                }
            }),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Login successful")
        self.assertIn("refresh", response.json())
        self.assertIn("access", response.json())
        self.assertEqual(response.json()["user"]["email"], "existing@example.com")
        
        # Verify user count hasn't changed (no duplicate created)
        user_count = User.objects.filter(email="existing@example.com").count()
        self.assertEqual(user_count, 1)
