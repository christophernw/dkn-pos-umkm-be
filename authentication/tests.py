from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.api import router  
from ninja.testing import TestClient
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import StoreInvitation

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
        self.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="password")
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
        
    # New tests for store invitations
    def test_send_invitation_success(self):
        response = self.client.post("/invite", auth=self.user.id, json={"invitee_email": "invitee@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["invitee_email"], "invitee@example.com")
        self.assertEqual(response.json()["status"], "pending")
        
        # Check that invitation was created in the database
        invitation = StoreInvitation.objects.filter(inviter=self.user, invitee_email="invitee@example.com").first()
        self.assertIsNotNone(invitation)
        self.assertEqual(invitation.status, StoreInvitation.PENDING)

    def test_send_invitation_user_not_found(self):
        response = self.client.post("/invite", auth=999, json={"invitee_email": "invitee@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("User not found", response.json()["error"])
    
    def test_send_invitation_duplicate(self):
        # Create an existing invitation
        StoreInvitation.objects.create(
            inviter=self.user,
            invitee_email="invitee@example.com",
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Try to create another invitation for the same email
        response = self.client.post("/invite", auth=self.user.id, json={"invitee_email": "invitee@example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.json()["error"])
    
    def test_list_invitations_empty(self):
        response = self.client.get("/invitations", auth=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
    
    def test_list_invitations_with_data(self):
        # Create a couple of invitations
        StoreInvitation.objects.create(
            inviter=self.user,
            invitee_email="invitee1@example.com",
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        StoreInvitation.objects.create(
            inviter=self.user,
            invitee_email="invitee2@example.com",
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.get("/invitations", auth=self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["inviter_name"], "testuser")
    
    