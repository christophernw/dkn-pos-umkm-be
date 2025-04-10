# produk/tests.py
from django.test import TestCase
from django.conf import settings
from ninja.testing import TestClient
from django.core.files.uploadedfile import SimpleUploadedFile
import jwt

from authentication.models import User
from produk.api import router, MAX_FILE_SIZE_MB
from produk.models import Produk, KategoriProduk


class ProdukAPITestCase(TestCase):
    def setUp(self):
        # test client for our router
        self.client = TestClient(router)

        # create owner user
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass"
        )
        self.owner.role = "Pemilik"
        self.owner.save()
        owner_token = jwt.encode(
            {"user_id": self.owner.id}, settings.SECRET_KEY, algorithm="HS256"
        )
        self.owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # create employee user
        self.employee = User.objects.create_user(
            username="empl", email="empl@example.com", password="pass", owner=self.owner
        )
        self.employee.role = "Karyawan"
        self.employee.save()
        emp_token = jwt.encode(
            {"user_id": self.employee.id}, settings.SECRET_KEY, algorithm="HS256"
        )
        self.emp_headers = {"Authorization": f"Bearer {emp_token}"}

        # a category
        self.cat = KategoriProduk.objects.create(nama="Cat1")

        # two products under owner
        image_content = b"\x89PNG\r\n\x1a\n"  # minimal PNG header
        img1 = SimpleUploadedFile("img1.png", image_content, content_type="image/png")
        img2 = SimpleUploadedFile("img2.png", image_content, content_type="image/png")

        self.prod1 = Produk.objects.create(
            nama="Prod1",
            foto=img1,
            harga_modal=10,
            harga_jual=15,
            stok=5,
            satuan="pcs",
            kategori=self.cat,
            user=self.owner,
        )
        self.prod2 = Produk.objects.create(
            nama="Prod2",
            foto=img2,
            harga_modal=20,
            harga_jual=30,
            stok=20,
            satuan="pcs",
            kategori=self.cat,
            user=self.owner,
        )

    def test_get_default_returns_all(self):
        r = self.client.get("/", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 2)
        names = [item["nama"] for item in data["items"]]
        self.assertCountEqual(names, ["Prod1", "Prod2"])

    def test_pagination_and_sorting(self):
        # descending stok: Prod2 first
        r = self.client.get("/page/1?sort=desc", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        items = r.json()["items"]
        self.assertEqual(items[0]["nama"], "Prod2")

        # ascending stok: Prod1 first
        r = self.client.get("/page/1?sort=asc", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        items = r.json()["items"]
        self.assertEqual(items[0]["nama"], "Prod1")

    def test_invalid_sort_parameter(self):
        r = self.client.get("/page/1?sort=foo", headers=self.owner_headers)
        self.assertEqual(r.status_code, 400)

    def test_karyawan_sees_owner_products(self):
        r = self.client.get("/", headers=self.emp_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 2)

    def test_get_produk_by_id(self):
        r = self.client.get(f"/{self.prod1.id}", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], self.prod1.id)

        # unknown id
        r2 = self.client.get("/9999", headers=self.owner_headers)
        self.assertEqual(r2.status_code, 404)

    def test_delete_produk(self):
        r = self.client.delete(f"/delete/{self.prod1.id}", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        # now fetching it fails
        r2 = self.client.get(f"/{self.prod1.id}", headers=self.owner_headers)
        self.assertEqual(r2.status_code, 404)
