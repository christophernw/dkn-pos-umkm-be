<<<<<<< HEAD
from authentication.tests.test import *
=======
from django.test import TestCase
from django.utils.timezone import now

from rest_framework_simplejwt.tokens import RefreshToken
from ninja.testing import TestClient
from datetime import timedelta

from authentication.models import Invitation, User
from authentication.api import router 
>>>>>>> dddc204e6a50c65ce56a16a5b5772c5c4be7e64a

class CancelInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password", role="Pemilik"
        )
        self.refresh = RefreshToken.for_user(self.owner)

        self.invitation = Invitation.objects.create(
            email="invited@example.com",
            name="Invited User",
            role="Karyawan",
            owner=self.owner,
            token="dummy_token",
            expires_at=now() + timedelta(days=1),
        )

    def test_cancel_invitation_success(self):
        response = self.client.post(
            "/cancel-invitation",
            json={"user_id": self.invitation.id},
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            f"Invitation to {self.invitation.email} canceled successfully",
        )
        self.assertEqual(response.json()["invitation_id"], self.invitation.id)
        self.assertFalse(Invitation.objects.filter(id=self.invitation.id).exists())

    def test_cancel_invitation_not_found(self):
        non_existent_invitation_id = 99999  

        response = self.client.post(
            "/cancel-invitation",
            json={"user_id": non_existent_invitation_id},
            headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invitation not found")

    def test_cancel_invitation_not_owner(self):
        non_owner = User.objects.create_user(
            username="non_owner", email="nonowner@example.com", password="password", role="Karyawan"
        )
        refresh = RefreshToken.for_user(non_owner)

        response = self.client.post(
            "/cancel-invitation",
            json={"user_id": self.invitation.id},
            headers={"Authorization": f"Bearer {str(refresh.access_token)}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Only Pemilik can cancel invitations")