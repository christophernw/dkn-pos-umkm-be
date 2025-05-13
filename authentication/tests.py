from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from authentication.api import router
from ninja.testing import TestClient
from unittest.mock import patch

class AuthAPITests(TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.client = TestClient(router)
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="password123"
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    # process_session tests
    def test_process_session_existing_user(self):
        """Test login with existing user (positive case)"""
        response = self.client.post(
            "/process-session", 
            json={"user": {"email": "test@example.com", "name": "testuser"}}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())
        self.assertEqual(response.json()["user"]["email"], "test@example.com")
        self.assertEqual(response.json()["message"], "Login successful")

    def test_process_session_new_user(self):
        """Test user creation for new email (positive case)"""
        response = self.client.post(
            "/process-session", 
            json={"user": {"email": "new@example.com", "name": "newuser"}}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())
        self.assertEqual(response.json()["user"]["email"], "new@example.com")
        self.assertEqual(response.json()["user"]["name"], "newuser")
        
        # Verify user was actually created in the database
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.username, "newuser")

    def test_process_session_missing_email(self):
        """Test process_session with missing email (negative case)"""
        response = self.client.post(
            "/process-session", 
            json={"user": {"name": "nameonly"}}
        )
        # This should fail validation because email is required
        self.assertEqual(response.status_code, 422)

    def test_process_session_missing_name(self):
        """Test process_session with missing name (corner case)"""
        response = self.client.post(
            "/process-session", 
            json={"user": {"email": "emailonly@example.com"}}
        )
        # This should fail validation because name is required
        self.assertEqual(response.status_code, 422)

    def test_process_session_special_characters(self):
        """Test process_session with special characters in name/email (corner case)"""
        response = self.client.post(
            "/process-session", 
            json={"user": {"email": "special+chars@example.com", "name": "User with spaces & symbols!"}}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        
        # Verify user was created with these details
        user = User.objects.get(email="special+chars@example.com")
        self.assertEqual(user.username, "User with spaces & symbols!")

    def test_process_session_duplicate_username(self):
        """Test when the username already exists but email is different (corner case)"""
        # First create a user with the username
        User.objects.create_user(username="duplicate_name", email="first@example.com")
        
        # Now try to process a session with same username but different email
        response = self.client.post(
            "/process-session", 
            json={"user": {"email": "second@example.com", "name": "duplicate_name"}}
        )
        self.assertEqual(response.status_code, 200)
        
        # This should create a new user with email second@example.com
        # but with a slightly modified username since duplicate_name is taken
        new_user = User.objects.get(email="second@example.com")
        self.assertIsNotNone(new_user)
        # Django might handle duplicates differently, so just check it exists

    # refresh_token tests
    def test_refresh_token_valid(self):
        """Test refreshing with valid token (positive case)"""
        response = self.client.post(
            "/refresh-token", 
            json={"refresh": str(self.refresh)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_refresh_token_invalid(self):
        """Test with invalid token (negative case)"""
        response = self.client.post(
            "/refresh-token", 
            json={"refresh": "invalid_token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    @patch('rest_framework_simplejwt.tokens.RefreshToken.__init__')
    def test_refresh_token_expired(self, mock_init):
        """Test refresh_token with expired token (corner case)"""
        # Mock the init method to raise TokenError with expired message
        mock_init.side_effect = TokenError('Token has expired')
        
        response = self.client.post(
            "/refresh-token", 
            json={"refresh": "expired_token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["error"].lower())

    def test_refresh_token_malformed(self):
        """Test refresh_token with malformed token (corner case)"""
        response = self.client.post(
            "/refresh-token", 
            json={"refresh": "not-even-a-jwt"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_refresh_token_missing(self):
        """Test refresh_token with missing token (negative case)"""
        response = self.client.post(
            "/refresh-token", 
            json={}
        )
        self.assertEqual(response.status_code, 422)  # Validation error

    # validate_token tests
    def test_validate_token_valid(self):
        """Test validating valid token (positive case)"""
        response = self.client.post(
            "/validate-token", 
            json={"token": self.access_token}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])

    def test_validate_token_invalid(self):
        """Test validating invalid token (negative case)"""
        response = self.client.post(
            "/validate-token", 
            json={"token": "invalid_token"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

    @patch('rest_framework_simplejwt.tokens.AccessToken.__init__')
    def test_validate_token_expired(self, mock_init):
        """Test validate_token with expired token (corner case)"""
        # Mock the init method to raise TokenError with expired message
        mock_init.side_effect = TokenError('Token has expired')
        
        response = self.client.post(
            "/validate-token", 
            json={"token": "expired_token"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

    def test_validate_token_malformed(self):
        """Test validate_token with malformed token (corner case)"""
        response = self.client.post(
            "/validate-token", 
            json={"token": "not-even-a-jwt"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

    def test_validate_token_missing(self):
        """Test validate_token with missing token (negative case)"""
        response = self.client.post(
            "/validate-token", 
            json={}
        )
        self.assertEqual(response.status_code, 422)  # Validation error

    # Additional edge cases
    def test_tokens_with_unicode_characters(self):
        """Test handling tokens with unicode characters (corner case)"""
        response = self.client.post(
            "/validate-token", 
            json={"token": "invalid-tökën-with-üñiçödé"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])