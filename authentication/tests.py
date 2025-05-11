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
    
    def test_accept_invitation_success(self):
        # Create an invitation for the user
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email=self.user.email,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.post("/accept-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("accepted", response.json()["message"])
        
        # Check that the invitation was updated in the database
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, StoreInvitation.ACCEPTED)
        self.assertEqual(invitation.invitee, self.user)
    
    def test_accept_invitation_not_found(self):
        response = self.client.post("/accept-invitation", auth=self.user.id, json={"token": "non-existent-token"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["error"])
    
    def test_accept_invitation_wrong_email(self):
        # Create an invitation for a different email
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email="different@example.com",
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.post("/accept-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 400)
        self.assertIn("not for your email", response.json()["error"])
    
    def test_accept_invitation_already_accepted(self):
        # Create an invitation that's already accepted
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email=self.user.email,
            invitee=self.user,
            token=str(uuid.uuid4()),
            status=StoreInvitation.ACCEPTED,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.post("/accept-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 400)
        self.assertIn("is accepted", response.json()["error"])
    
    def test_accept_invitation_expired(self):
        # Create an expired invitation
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email=self.user.email,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        response = self.client.post("/accept-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 400)
        self.assertIn("expired", response.json()["error"])
        
        # Check that invitation was marked as expired
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, StoreInvitation.EXPIRED)
    
    def test_decline_invitation_success(self):
        # Create an invitation for the user
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email=self.user.email,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.post("/decline-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("declined", response.json()["message"])
        
        # Check that the invitation was updated in the database
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, StoreInvitation.DECLINED)
        self.assertEqual(invitation.invitee, self.user)
    
    def test_decline_invitation_not_found(self):
        response = self.client.post("/decline-invitation", auth=self.user.id, json={"token": "non-existent-token"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["error"])
    
    def test_decline_invitation_wrong_email(self):
        # Create an invitation for a different email
        invitation = StoreInvitation.objects.create(
            inviter=self.user2,
            invitee_email="different@example.com",
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        response = self.client.post("/decline-invitation", auth=self.user.id, json={"token": invitation.token})
        self.assertEqual(response.status_code, 400)
        self.assertIn("not for your email", response.json()["error"])
    
    def test_user_not_found_accept_invitation(self):
        response = self.client.post("/accept-invitation", auth=999, json={"token": "some-token"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("User not found", response.json()["error"])
    
    def test_user_not_found_decline_invitation(self):
        response = self.client.post("/decline-invitation", auth=999, json={"token": "some-token"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("User not found", response.json()["error"])