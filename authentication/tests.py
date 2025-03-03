from django.test import TestCase
from django.contrib.auth.models import User

class RegisterTestCase(TestCase):
    def test_register_user(self):
        response = self.client.post("/api/auth/register", {
            "username": "testuser",
            "password": "securepassword",
            "email": "test@example.com"
        }, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())
        self.assertTrue(User.objects.filter(username="testuser").exists())
