from datetime import timedelta
from django.utils.timezone import now
from rest_framework_simplejwt.tokens import RefreshToken
from ninja.testing import TestClient
from django.test import TestCase

from authentication.models import Invitation, Toko, User
from authentication.api import router


class GetPendingInvitationsTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password", role="Pemilik", toko=self.toko
        )
        self.karyawan = User.objects.create_user(
            username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", toko=self.toko
        )
        self.invitation_1 = Invitation.objects.create(
            email="invite1@example.com",
            name="Invite User 1",
            role="Pengelola",
            toko=self.toko,
            created_by=self.owner,
            token="dummy_token_1",
            expires_at=now() + timedelta(days=1),
        )
        self.invitation_2 = Invitation.objects.create(
            email="invite2@example.com",
            name="Invite User 2",
            role="Karyawan",
            toko=self.toko,
            created_by=self.owner,
            token="dummy_token_2",
            expires_at=now() + timedelta(days=2),
        )

    def test_get_pending_invitations(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/pending-invitations", headers={"Authorization": f"Bearer {access_token}"}
        )

        self.assertEqual(response.status_code, 200)

        invitations = response.json()

        self.assertEqual(len(invitations), 2)

        invitation_1_data = next((i for i in invitations if i["email"] == "invite1@example.com"), None)
        invitation_2_data = next((i for i in invitations if i["email"] == "invite2@example.com"), None)

        self.assertIsNotNone(invitation_1_data)
        self.assertEqual(invitation_1_data["role"], "Pengelola")
        self.assertEqual(invitation_1_data["created_by"], self.owner.username)

        self.assertIsNotNone(invitation_2_data)
        self.assertEqual(invitation_2_data["role"], "Karyawan")
        self.assertEqual(invitation_2_data["created_by"], self.owner.username)

    def test_get_pending_invitations_without_toko(self):
        user_without_toko = User.objects.create_user(
            username="no_toko_user", email="no_toko@example.com", password="password", toko=None
        )

        refresh = RefreshToken.for_user(user_without_toko)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/pending-invitations", headers={"Authorization": f"Bearer {access_token}"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"message": "User doesn't have a toko"})