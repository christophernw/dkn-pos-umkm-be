<<<<<<< HEAD
from authentication.tests.test import * 
=======
from django.db import IntegrityError
from django.test import TestCase
from django.utils.timezone import now

from rest_framework_simplejwt.tokens import RefreshToken
from ninja.testing import TestClient
from datetime import timedelta
from unittest.mock import patch

from authentication.models import Invitation, User
from authentication.api import router 
>>>>>>> dddc204e6a50c65ce56a16a5b5772c5c4be7e64a

class SendInvitationTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="password", role="Pemilik")
        self.refresh = RefreshToken.for_user(self.owner)

    def test_send_invitation_success(self):
        response = self.client.post("/send-invitation", json={
            "name": "New User",
            "email": "newuser@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Invitation sent")

    def test_send_invitation_existing_user(self):
        User.objects.create_user(username="existing", email="existing@example.com", password="password", role="Karyawan")

        response = self.client.post("/send-invitation", json={
            "name": "Existing User",
            "email": "existing@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User sudah ada di toko ini.")

    def test_send_invitation_already_invited(self):
        Invitation.objects.create(
            email="invited@example.com", name="Invited User", role="Karyawan",
            owner=self.owner, token="dummy", expires_at=now() + timedelta(days=1)
        )

        response = self.client.post("/send-invitation", json={
            "name": "Invited User",
            "email": "invited@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Undangan sudah dikirim ke email ini.")

    @patch("authentication.models.Invitation.objects.create", side_effect=IntegrityError)
    def test_send_invitation_integrity_error(self, mock_create):
        response = self.client.post("/send-invitation", json={
            "name": "Error User",
            "email": "error@example.com",
            "role": "Karyawan"
        }, headers={"Authorization": f"Bearer {str(self.refresh.access_token)}"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invitation already exists.")