from django.test import TestCase
from django.conf import settings
from ninja.testing import TestClient
from django.core.files.uploadedfile import SimpleUploadedFile
import jwt

from authentication.models import User
from produk.api import router
from produk.models import Produk, KategoriProduk


class ProdukAPITestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        # create owner user
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass"
        )
        self.owner.role = "Pemilik"
        self.owner.save()
        token = jwt.encode(
            {"user_id": self.owner.id}, settings.SECRET_KEY, algorithm="HS256"
        )
        self.owner_headers = {"Authorization": f"Bearer {token}"}

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
        r = self.client.get("/page/1?sort=desc", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"][0]["nama"], "Prod2")
        r = self.client.get("/page/1?sort=asc", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"][0]["nama"], "Prod1")

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
        r2 = self.client.get("/9999", headers=self.owner_headers)
        self.assertEqual(r2.status_code, 404)

    def test_delete_produk(self):
        r = self.client.delete(f"/delete/{self.prod1.id}", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get(f"/{self.prod1.id}", headers=self.owner_headers)
        self.assertEqual(r2.status_code, 404)

    def test_search_query_filters_results(self):
        r = self.client.get("/page/1?q=Prod1", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["nama"], "Prod1")

    def test_custom_per_page_and_page_not_found(self):
        r1 = self.client.get("/page/1?per_page=1", headers=self.owner_headers)
        self.assertEqual(r1.status_code, 200)
        json1 = r1.json()
        self.assertEqual(json1["per_page"], 1)
        self.assertEqual(len(json1["items"]), 1)
        self.assertEqual(json1["total_pages"], 2)

        r3 = self.client.get("/page/3?per_page=1", headers=self.owner_headers)
        self.assertEqual(r3.status_code, 404)

    def test_update_nonexistent_produk(self):
        payload = {"nama": "Nope"}
        r = self.client.post("/update/9999", json={"payload": payload}, headers=self.owner_headers)
        self.assertEqual(r.status_code, 422)

    def test_unauthorized_access(self):
        # no header → 401
        self.assertEqual(self.client.get("/").status_code, 401)
        self.assertEqual(
            self.client.post("/create", json={"payload": {}}, headers={}).status_code, 401
        )

    def test_default_sort_when_no_param(self):
        # create third product to test -id order
        p3 = Produk.objects.create(
            nama="Prod3",
            foto=SimpleUploadedFile("a.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
            harga_modal=1,
            harga_jual=1,
            stok=50,
            satuan="pcs",
            kategori=self.cat,
            user=self.owner,
        )
        r = self.client.get("/", headers=self.owner_headers)
        first = r.json()["items"][0]
        self.assertEqual(first["id"], p3.id)  # newest id first

    def test_delete_all_and_list_empty(self):
        # delete both then list
        self.client.delete(f"/delete/{self.prod1.id}", headers=self.owner_headers)
        self.client.delete(f"/delete/{self.prod2.id}", headers=self.owner_headers)
        r = self.client.get("/", headers=self.owner_headers)
        self.assertEqual(r.json()["total"], 0)
