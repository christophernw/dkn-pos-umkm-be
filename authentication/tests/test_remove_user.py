import jwt
from django.test import TestCase
from django.conf import settings
from ninja.testing import TestClient

from authentication.models import Toko, User
from authentication.api import router 

class RemoveUserFromTokoTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        
        # Create owner user with toko
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password"
        )
        self.owner.role = "Pemilik"
        self.owner.toko = self.toko
        self.owner.save()
        
        # Create karyawan user with same toko
        self.karyawan = User.objects.create_user(
            username="karyawan", email="karyawan@example.com", password="password"
        )
        self.karyawan.role = "Karyawan"
        self.karyawan.toko = self.toko
        self.karyawan.save()
        
        # Create another toko and user
        self.other_toko = Toko.objects.create()
        self.external_user = User.objects.create_user(
            username="external", email="external@example.com", password="password"
        )
        self.external_user.role = "Karyawan"
        self.external_user.toko = self.other_toko
        self.external_user.save()
        
        # Create JWT tokens for authentication
        self.owner_token = jwt.encode(
            {"user_id": self.owner.id}, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )
        
        self.karyawan_token = jwt.encode(
            {"user_id": self.karyawan.id}, 
            settings.SECRET_KEY, 
            algorithm="HS256"
        )

    def test_remove_user_successfully(self):
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.karyawan.id},
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["user"]["role"], "Pemilik")  # Role is reset to Pemilik
        
        # Need to refresh karyawan from database
        self.karyawan.refresh_from_db()
        self.assertNotEqual(self.karyawan.toko.id, self.toko.id)  # User has a new toko

    def test_remove_self_should_fail(self):
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.owner.id},
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Cannot remove yourself from your own toko")

    def test_remove_user_from_other_toko_should_fail(self):
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.external_user.id},
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User is not in your toko")

    def test_non_pemilik_cannot_remove_user(self):
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": self.owner.id},
            headers={"Authorization": f"Bearer {self.karyawan_token}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Only Pemilik can remove users from toko")

    def test_remove_nonexistent_user(self):
        non_existent_user_id = 99999 
        response = self.client.post(
            "/remove-user-from-toko",
            json={"user_id": non_existent_user_id},
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "User not found")