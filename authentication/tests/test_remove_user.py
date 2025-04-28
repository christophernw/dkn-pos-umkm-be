<<<<<<< HEAD
from authentication.tests.test import *
=======
from django.test import TestCase

from rest_framework_simplejwt.tokens import RefreshToken
from ninja.testing import TestClient

from authentication.models import Toko, User
from authentication.api import router 
>>>>>>> dddc204e6a50c65ce56a16a5b5772c5c4be7e64a

class RemoveUserFromTokoTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password", role="Pemilik", toko=self.toko
        )
        self.karyawan = User.objects.create_user(
            username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", toko=self.toko
        )
        self.other_toko = Toko.objects.create()
        self.external_user = User.objects.create_user(
            username="external", email="external@example.com", password="password", role="Karyawan", toko=self.other_toko
        )

    def test_remove_user_successfully(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.karyawan.id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["user"]["role"], "Pemilik")
        self.assertNotEqual(result["user"]["new_toko_id"], self.toko.id)

    def test_remove_self_should_fail(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.owner.id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Cannot remove yourself from your own toko")

    def test_remove_user_from_other_toko_should_fail(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.external_user.id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User is not in your toko")

    def test_non_pemilik_cannot_remove_user(self):
        refresh = RefreshToken.for_user(self.karyawan)
        access_token = str(refresh.access_token)

        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.owner.id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Only Pemilik can remove users from toko")

    def test_remove_nonexistent_user(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        non_existent_user_id = 99999 
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": non_existent_user_id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User not found")