from authentication.tests.test import *

class GetUsersTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.toko = Toko.objects.create()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password", role="Pemilik", toko=self.toko
        )
        self.karyawan = User.objects.create_user(
            username="karyawan", email="karyawan@example.com", password="password", role="Karyawan", toko=self.toko
        )

    def test_get_users_as_owner(self):
        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 2)
        roles = [user["role"] for user in users]
        self.assertIn("Pemilik", roles)
        self.assertIn("Karyawan", roles)

    def test_get_users_as_karyawan(self):
        refresh = RefreshToken.for_user(self.karyawan)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 2)
        roles = [user["role"] for user in users]
        self.assertIn("Pemilik", roles)
        self.assertIn("Karyawan", roles)

    def test_get_users_as_administrator(self):
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            role="Administrator",
            toko=self.toko
        )
        refresh = RefreshToken.for_user(admin)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 3)

        roles = [user["role"] for user in users]
        self.assertIn("Pemilik", roles)
        self.assertIn("Administrator", roles)
        self.assertIn("Karyawan", roles)

    def test_get_users_without_toko(self):
        user_without_toko = User.objects.create_user(
            username="no_toko_user", email="no_toko@example.com", password="password", toko=None
        )

        refresh = RefreshToken.for_user(user_without_toko)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )

        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["id"], user_without_toko.id)
        self.assertIsNone(users[0]["toko_id"])

    def test_get_users_with_pending_invitation(self):
        Invitation.objects.create(
            email="pending@example.com",
            name="Pending User",
            role="Karyawan",
            owner=self.owner,
            token="dummy_token",
            expires_at=now() + timedelta(days=1),
        )

        refresh = RefreshToken.for_user(self.owner)
        access_token = str(refresh.access_token)

        response = self.client.get(
            "/get-users", headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(response.status_code, 200)

        users = response.json()
        self.assertEqual(len(users), 3)  

        pending_user = next((u for u in users if u["status"] == "pending"), None)
        self.assertIsNotNone(pending_user)
        self.assertEqual(pending_user["email"], "pending@example.com")
        self.assertEqual(pending_user["role"], "Karyawan")

        self.assertEqual(users[-1]["status"], "pending")