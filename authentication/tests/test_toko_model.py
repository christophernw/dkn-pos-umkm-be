from unittest import TestCase
from authentication.models import Toko, User

class TokoModelTests(TestCase):
    def test_str_toko_with_owner(self):
        # Create Toko and User with 'Pemilik' role
        toko = Toko.objects.create()
        owner = User.objects.create_user(
            email="owner@example.com",
            password="password",
            role="Pemilik",
            toko=toko,
        )
        self.assertEqual(str(toko), f"Toko {toko.id} - {owner.username}")

    def test_str_toko_without_owner(self):
        # Create Toko without a 'Pemilik' user
        toko = Toko.objects.create()
        self.assertEqual(str(toko), f"Toko {toko.id} - No owner")
