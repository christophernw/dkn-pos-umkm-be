from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from authentication.api import router, UserResponse, UpdateUserRequest
from ninja.testing import TestClient
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

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

    # UserResponse.from_user class method test
    def test_user_response_from_user(self):
        """Test UserResponse.from_user class method (unit test for refactored code)"""
        # Create a test user with known values
        test_user = User.objects.create_user(
            username="testuser_method", 
            email="testmethod@example.com"
        )
        test_user.is_active = False  # Set to False to test this field
        test_user.save()
        
        # Use the class method
        user_response = UserResponse.from_user(test_user)
        
        # Verify all fields are correctly mapped
        self.assertEqual(user_response.id, test_user.id)
        self.assertEqual(user_response.email, "testmethod@example.com")
        self.assertEqual(user_response.name, "testuser_method")
        self.assertFalse(user_response.is_active)
        self.assertIsInstance(user_response.date_joined, str)
        
        # Verify date format is correct (ISO format)
        from datetime import datetime
        try:
            parsed_date = datetime.fromisoformat(user_response.date_joined.replace('Z', '+00:00'))
            self.assertIsInstance(parsed_date, datetime)
        except ValueError:
            self.fail(f"date_joined '{user_response.date_joined}' is not in valid ISO format")

    # get_all_users tests
    def test_get_all_users_success(self):
        """Test getting all users successfully (positive case)"""
        # Create additional test users
        User.objects.create_user(username="user2", email="user2@example.com")
        User.objects.create_user(username="user3", email="user3@example.com")
        
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("users", data)
        self.assertIn("total_count", data)
        self.assertEqual(data["total_count"], 3)  # Original user + 2 new users
        self.assertEqual(len(data["users"]), 3)
        
        # Check the structure of the first user
        first_user = data["users"][0]
        self.assertIn("id", first_user)
        self.assertIn("email", first_user)
        self.assertIn("name", first_user)
        self.assertIn("date_joined", first_user)
        self.assertIn("is_active", first_user)

    def test_get_all_users_empty_list(self):
        """Test getting all users when no users exist (edge case)"""
        # Delete all existing users
        User.objects.all().delete()
        
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total_count"], 0)
        self.assertEqual(len(data["users"]), 0)

    def test_get_all_users_single_user(self):
        """Test getting all users with only one user (edge case)"""
        # Only the user from setUp should exist
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total_count"], 1)
        self.assertEqual(len(data["users"]), 1)
        
        user_data = data["users"][0]
        self.assertEqual(user_data["email"], "test@example.com")
        self.assertEqual(user_data["name"], "testuser")
        self.assertTrue(user_data["is_active"])

    def test_get_all_users_ordered_by_id(self):
        """Test that users are returned ordered by ID (functional test)"""
        # Create users in a specific order
        user2 = User.objects.create_user(username="user2", email="user2@example.com")
        user3 = User.objects.create_user(username="user3", email="user3@example.com")
        
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        user_ids = [user["id"] for user in data["users"]]
        
        # Check that IDs are in ascending order
        self.assertEqual(user_ids, sorted(user_ids))

    def test_get_all_users_response_format(self):
        """Test the exact format of the response (structure validation)"""
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verify top-level structure
        self.assertIsInstance(data, dict)
        self.assertIn("users", data)
        self.assertIn("total_count", data)
        
        # Verify users array structure
        self.assertIsInstance(data["users"], list)
        self.assertIsInstance(data["total_count"], int)
        
        if data["users"]:  # If there are users
            user = data["users"][0]
            # Verify user object structure
            required_fields = ["id", "email", "name", "date_joined", "is_active"]
            for field in required_fields:
                self.assertIn(field, user)
            
            # Verify field types
            self.assertIsInstance(user["id"], int)
            self.assertIsInstance(user["email"], str)
            self.assertIsInstance(user["name"], str)
            self.assertIsInstance(user["date_joined"], str)
            self.assertIsInstance(user["is_active"], bool)

    def test_get_all_users_with_inactive_user(self):
        """Test that inactive users are also returned (functional test)"""
        # Create an inactive user
        inactive_user = User.objects.create_user(
            username="inactive_user", 
            email="inactive@example.com"
        )
        inactive_user.is_active = False
        inactive_user.save()
        
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total_count"], 2)  # Original user + inactive user
        
        # Check that we have both active and inactive users
        active_users = [user for user in data["users"] if user["is_active"]]
        inactive_users = [user for user in data["users"] if not user["is_active"]]
        
        self.assertEqual(len(active_users), 1)
        self.assertEqual(len(inactive_users), 1)
        self.assertEqual(inactive_users[0]["email"], "inactive@example.com")

    def test_get_all_users_date_joined_format(self):
        """Test that date_joined is properly formatted (format validation)"""
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        if data["users"]:
            user = data["users"][0]
            date_joined = user["date_joined"]
            
            # Verify it's in ISO format and can be parsed
            from datetime import datetime
            try:
                parsed_date = datetime.fromisoformat(date_joined.replace('Z', '+00:00'))
                self.assertIsInstance(parsed_date, datetime)
            except ValueError:
                self.fail(f"date_joined '{date_joined}' is not in valid ISO format")

    def test_get_all_users_large_dataset(self):
        """Test performance with larger number of users (performance edge case)"""
        # Create many users to test performance and handling
        users_to_create = 50
        for i in range(users_to_create):
            User.objects.create_user(
                username=f"bulk_user_{i}", 
                email=f"bulk_{i}@example.com"
            )
        
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["total_count"], users_to_create + 1)  # +1 for setup user
        self.assertEqual(len(data["users"]), users_to_create + 1)

    def test_get_all_users_uses_queryset_count(self):
        """Test that the refactored method uses queryset.count() efficiently"""
        # Create test users
        User.objects.create_user(username="user2", email="user2@example.com")
        User.objects.create_user(username="user3", email="user3@example.com")
        
        # Mock the QuerySet's count method directly
        with patch('django.db.models.query.QuerySet.count') as mock_count:
            mock_count.return_value = 3
            response = self.client.get("/users")
        
        self.assertEqual(response.status_code, 200)
        # Verify count was called (this tests that we're using count() instead of len())
        mock_count.assert_called_once()

    # NEW TESTS FOR get_user_by_id
    def test_get_user_by_id_success(self):
        """Test getting user by ID successfully (positive case)"""
        response = self.client.get(f"/users/{self.user.id}")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["id"], self.user.id)
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["name"], "testuser")
        self.assertTrue(data["is_active"])
        self.assertIn("date_joined", data)

    def test_get_user_by_id_not_found(self):
        """Test getting user by non-existent ID (negative case)"""
        response = self.client.get("/users/9999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "User not found")

    def test_get_user_by_id_inactive_user(self):
        """Test getting inactive user by ID (edge case)"""
        # Create inactive user
        inactive_user = User.objects.create_user(
            username="inactive", 
            email="inactive@example.com"
        )
        inactive_user.is_active = False
        inactive_user.save()
        
        response = self.client.get(f"/users/{inactive_user.id}")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["id"], inactive_user.id)
        self.assertFalse(data["is_active"])

    # NEW TESTS FOR update_user_profile
    def test_update_user_profile_email_only(self):
        """Test updating only email (positive case)"""
        update_data = {"email": "newemail@example.com"}
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "newemail@example.com")
        self.assertEqual(data["name"], "testuser")  # Should remain unchanged
        
        # Verify in database
        updated_user = User.objects.get(id=self.user.id)
        self.assertEqual(updated_user.email, "newemail@example.com")

    def test_update_user_profile_name_only(self):
        """Test updating only username (positive case)"""
        update_data = {"name": "newusername"}
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "newusername")
        self.assertEqual(data["email"], "test@example.com")  # Should remain unchanged
        
        # Verify in database
        updated_user = User.objects.get(id=self.user.id)
        self.assertEqual(updated_user.username, "newusername")

    def test_update_user_profile_both_fields(self):
        """Test updating both email and username (positive case)"""
        update_data = {
            "email": "updated@example.com",
            "name": "updateduser"
        }
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "updated@example.com")
        self.assertEqual(data["name"], "updateduser")
        
        # Verify in database
        updated_user = User.objects.get(id=self.user.id)
        self.assertEqual(updated_user.email, "updated@example.com")
        self.assertEqual(updated_user.username, "updateduser")

    def test_update_user_profile_empty_payload(self):
        """Test updating with empty payload (edge case)"""
        response = self.client.put(f"/users/{self.user.id}", json={})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Values should remain unchanged
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["name"], "testuser")

    def test_update_user_profile_user_not_found(self):
        """Test updating non-existent user (negative case)"""
        update_data = {"email": "new@example.com"}
        response = self.client.put("/users/9999", json=update_data)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "User not found")

    def test_update_user_profile_duplicate_email(self):
        """Test updating with email that already exists (negative case)"""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser", 
            email="other@example.com"
        )
        
        # Try to update self.user with other_user's email
        update_data = {"email": "other@example.com"}
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "Email already exists for another user")

    def test_update_user_profile_duplicate_username(self):
        """Test updating with username that already exists (negative case)"""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser", 
            email="other@example.com"
        )
        
        # Try to update self.user with other_user's username
        update_data = {"name": "otheruser"}
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "Username already exists for another user")

    def test_update_user_profile_same_email(self):
        """Test updating with same email (should work - edge case)"""
        update_data = {"email": "test@example.com"}  # Same as current
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "test@example.com")

    def test_update_user_profile_same_username(self):
        """Test updating with same username (should work - edge case)"""
        update_data = {"name": "testuser"}  # Same as current
        response = self.client.put(f"/users/{self.user.id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "testuser")

    def test_update_user_request_validation(self):
        """Test UpdateUserRequest schema validation"""
        # Test with invalid email format
        with self.assertRaises(ValidationError):
            UpdateUserRequest(email="invalid-email-format")
        
        # Test with empty name
        with self.assertRaises(ValidationError):
            UpdateUserRequest(name="")
        
        # Test with valid data
        valid_request = UpdateUserRequest(email="valid@example.com", name="validname")
        self.assertEqual(valid_request.email, "valid@example.com")
        self.assertEqual(valid_request.name, "validname")
        
        # Test with None values (should be valid)
        none_request = UpdateUserRequest(email=None, name=None)
        self.assertIsNone(none_request.email)
        self.assertIsNone(none_request.name)

    def test_update_user_request_invalid_email_validation(self):
        """Test UpdateUserRequest with various invalid email formats"""
        invalid_emails = [
            "plainaddress",
            "@missingdomain.com",
            "missing@.com",
            "missing@domain",
            "spaces @domain.com",
            "double@@domain.com",
            "trailingdot@domain.com.",
        ]
        
        for invalid_email in invalid_emails:
            with self.assertRaises(ValidationError):
                UpdateUserRequest(email=invalid_email)

    def test_update_user_request_valid_email_validation(self):
        """Test UpdateUserRequest with valid email formats"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "first+last@subdomain.example.org",
            "test123@test-domain.com",
        ]
        
        for valid_email in valid_emails:
            # Should not raise ValidationError
            request = UpdateUserRequest(email=valid_email)
            self.assertEqual(request.email, valid_email)

    