# import jwt
# from django.test import TestCase
# from django.utils.timezone import now
# from django.conf import settings
# from ninja.testing import TestClient
# from datetime import timedelta

# from authentication.models import Invitation, Toko, User
# from authentication.api import router 

# class GetUsersTests(TestCase):
#     def setUp(self):
#         self.client = TestClient(router)
#         self.toko = Toko.objects.create()

#         self.owner = User.objects.create_user(
#             username="owner",
#             email="owner@example.com",
#             password="password",
#             role="Pemilik",
#             toko=self.toko
#         )

#         self.karyawan = User.objects.create_user(
#             username="karyawan",
#             email="karyawan@example.com",
#             password="password",
#             role="Karyawan",
#             toko=self.toko
#         )

#         self.owner_token = self.generate_token(self.owner)
#         self.karyawan_token = self.generate_token(self.karyawan)

#     def generate_token(self, user):
#         return jwt.encode(
#             {"user_id": user.id},
#             settings.SECRET_KEY,
#             algorithm="HS256"
#         )

#     def auth_headers(self, token):
#         return {"Authorization": f"Bearer {token}"}

#     def test_get_users_as_owner(self):
#         response = self.client.get(
#             "/get-users",
#             headers=self.auth_headers(self.owner_token)
#         )
#         assert response.status_code == 200

#         users = response.json()
#         assert len(users) == 2

#         roles = [user["role"] for user in users]
#         assert "Pemilik" in roles
#         assert "Karyawan" in roles

#     def test_get_users_as_karyawan(self):
#         response = self.client.get(
#             "/get-users",
#             headers=self.auth_headers(self.karyawan_token)
#         )
#         assert response.status_code == 200

#         users = response.json()
#         assert len(users) == 2

#         roles = [user["role"] for user in users]
#         assert "Pemilik" in roles
#         assert "Karyawan" in roles

#     def test_get_users_as_administrator(self):
#         admin = User.objects.create_user(
#             username="admin",
#             email="admin@example.com",
#             password="password",
#             role="Administrator",
#             toko=self.toko
#         )

#         admin_token = self.generate_token(admin)

#         response = self.client.get(
#             "/get-users",
#             headers=self.auth_headers(admin_token)
#         )
#         assert response.status_code == 200

#         users = response.json()
#         assert len(users) == 3

#         roles = [user["role"] for user in users]
#         assert set(roles) == {"Pemilik", "Administrator", "Karyawan"}

#     def test_get_users_without_toko(self):
#         no_toko_user = User.objects.create_user(
#             username="no_toko",
#             email="no_toko@example.com",
#             password="password"
#         )

#         no_toko_token = self.generate_token(no_toko_user)

#         response = self.client.get(
#             "/get-users",
#             headers=self.auth_headers(no_toko_token)
#         )
#         assert response.status_code == 200

#         users = response.json()
#         assert len(users) == 1

#         user = users[0]
#         assert user["id"] == no_toko_user.id
#         assert user["toko_id"] is None
#         assert user["role"] == no_toko_user.role
#         assert user["status"] == "active"  # default aktif user biasa

#     def test_get_users_with_pending_invitation(self):
#         expiration = now() + timedelta(days=1)
#         invitation_payload = {
#             "email": "pending@example.com",
#             "name": "Pending User",
#             "role": "Karyawan",
#             "toko_id": self.toko.id,
#             "exp": expiration,
#         }

#         invitation_token = jwt.encode(
#             invitation_payload,
#             settings.SECRET_KEY,
#             algorithm="HS256"
#         )

#         Invitation.objects.create(
#             email="pending@example.com",
#             name="Pending User",
#             role="Karyawan",
#             toko=self.toko,
#             created_by=self.owner,
#             token=invitation_token,
#             expires_at=expiration
#         )

#         response = self.client.get(
#             "/get-users",
#             headers=self.auth_headers(self.owner_token)
#         )
#         assert response.status_code == 200

#         users = response.json()
#         assert len(users) == 3  # 2 user + 1 invitation

#         pending_user = next((u for u in users if u.get("status") == "pending"), None)
#         assert pending_user is not None
#         assert pending_user["email"] == "pending@example.com"
#         assert pending_user["role"] == "Karyawan"

#         # Pastikan yang pending ada di urutan terakhir (sorting)
#         assert users[-1]["status"] == "pending"
