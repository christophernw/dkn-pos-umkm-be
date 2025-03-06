from django.test import TestCase

from django.test import TestCase, Client
from produk.models import Produk, KategoriProduk
import json

class ProdukAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")

        self.produk_dengan_foto = Produk.objects.create(
            nama="Laptop",
            foto="https://example.com/laptop.jpg",
            harga_modal=5000000,
            harga_jual=7000000,
            stok=10,
            satuan="Pcs",
            kategori=self.kategori
        )

        self.produk_tanpa_foto = Produk.objects.create(
            nama="Keyboard",
            foto=None,
            harga_modal=300000,
            harga_jual=500000,
            stok=20,
            satuan="Pcs",
            kategori=self.kategori
        )

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori), "Elektronik")

    def test_produk_str(self):
        self.assertEqual(str(self.produk_dengan_foto), "Laptop")
        self.assertEqual(str(self.produk_tanpa_foto), "Keyboard")

    def test_get_produk_success(self):
        response = self.client.get("/api/produk")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)

        data = sorted(data, key=lambda x: x["id"])

        self.assertEqual(data[0]["id"], self.produk_dengan_foto.id)
        self.assertEqual(data[0]["nama"], "Laptop")
        self.assertEqual(data[0]["foto"], "https://example.com/laptop.jpg")
        self.assertEqual(data[0]["harga_modal"], float(self.produk_dengan_foto.harga_modal))
        self.assertEqual(data[0]["harga_jual"], float(self.produk_dengan_foto.harga_jual))
        self.assertEqual(data[0]["stok"], float(self.produk_dengan_foto.stok))
        self.assertEqual(data[0]["satuan"], self.produk_dengan_foto.satuan)
        self.assertEqual(data[0]["kategori"], "Elektronik")

        self.assertEqual(data[1]["id"], self.produk_tanpa_foto.id)
        self.assertEqual(data[1]["nama"], "Keyboard")
        self.assertIsNone(data[1]["foto"])
        self.assertEqual(data[1]["harga_modal"], float(self.produk_tanpa_foto.harga_modal))
        self.assertEqual(data[1]["harga_jual"], float(self.produk_tanpa_foto.harga_jual))
        self.assertEqual(data[1]["stok"], float(self.produk_tanpa_foto.stok))
        self.assertEqual(data[1]["satuan"], self.produk_tanpa_foto.satuan)
        self.assertEqual(data[1]["kategori"], "Elektronik")

    def test_get_produk_not_found(self):
        Produk.objects.all().delete()
        response = self.client.get("/api/produk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_produk_invalid_url(self):
        response = self.client.get("/api/produk-salah")
        self.assertEqual(response.status_code, 404)

class ProdukSortingAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")

        self.produk_1 = Produk.objects.create(nama="Laptop", foto=None, harga_modal=5000000, harga_jual=7000000, stok=5, satuan="PCS", kategori=self.kategori)
        self.produk_2 = Produk.objects.create(nama="Keyboard", foto=None, harga_modal=300000, harga_jual=500000, stok=20, satuan="PCS", kategori=self.kategori)
        self.produk_3 = Produk.objects.create(nama="Mouse", foto=None, harga_modal=150000, harga_jual=250000, stok=10, satuan="PCS", kategori=self.kategori)

    def test_get_produk_sorted_ascending(self):
        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["nama"], "Laptop")
        self.assertEqual(data[1]["nama"], "Mouse")
        self.assertEqual(data[2]["nama"], "Keyboard")

    def test_get_produk_sorted_descending(self):
        response = self.client.get("/api/produk?sort=desc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["nama"], "Keyboard")
        self.assertEqual(data[1]["nama"], "Mouse")
        self.assertEqual(data[2]["nama"], "Laptop")

    def test_get_produk_invalid_sort_param(self):
        response = self.client.get("/api/produk?sort=invalid")
        self.assertEqual(response.status_code, 400)

    def test_get_produk_no_data(self):
        Produk.objects.all().delete()
        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_produk_same_stock(self):
        Produk.objects.all().delete()
        Produk.objects.create(nama="Item A", stok=10, harga_modal=100, harga_jual=200, satuan="PCS", kategori=self.kategori)
        Produk.objects.create(nama="Item B", stok=10, harga_modal=150, harga_jual=250, satuan="PCS", kategori=self.kategori)

        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]["id"] < data[1]["id"])

class ProdukCreateAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")
        self.url = "/api/produk/create"  

    # def test_create_produk_success(self):
    #     payload = {
    #         "nama": "Monitor",
    #         "foto": "https://example.com/monitor.jpg",
    #         "harga_modal": 1200000,
    #         "harga_jual": 1500000,
    #         "stok": 15,
    #         "satuan": "PCS",
    #         "kategori": "Elektronik"  
    #     }
    #     response = self.client.post(
    #         self.url,
    #         data=json.dumps(payload), 
    #         content_type="application/json" 
    #     )
    #     self.assertEqual(response.status_code, 201, "Seharusnya berhasil membuat produk")

    #     data = response.json()
    #     self.assertEqual(data["nama"], "Monitor")
    #     self.assertEqual(data["kategori"], "Elektronik")
    #     self.assertTrue(Produk.objects.filter(nama="Monitor").exists())

    def test_create_produk_missing_required_field(self):
        payload = {
            "foto": "https://example.com/item.jpg",
            "harga_modal": 50000,
            "harga_jual": 80000,
            "stok": 5,
            "satuan": "PCS"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Seharusnya gagal karena field wajib hilang")

    # def test_create_produk_new_category(self):

    #     payload = {
    #         "nama": "Smartphone",
    #         "foto": None,
    #         "harga_modal": 3000000,
    #         "harga_jual": 4500000,
    #         "stok": 8,
    #         "satuan": "PCS",
    #         "kategori": "Gadget" 
    #     }
    #     response = self.client.post(self.url, data=payload, content_type="application/json")
    #     self.assertEqual(response.status_code, 201)

    #     data = response.json()
    #     self.assertEqual(data["kategori"], "Gadget")
    #     self.assertTrue(KategoriProduk.objects.filter(nama="Gadget").exists())

    def test_create_produk_negative_price(self):
        payload = {
            "nama": "Test Negative Price",
            "foto": None,
            "harga_modal": -100000,
            "harga_jual": -150000,
            "stok": 10,
            "satuan": "PCS",
            "kategori": "Elektronik"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Harga minus seharusnya invalid")

    def test_create_produk_invalid_stock(self):
        payload = {
            "nama": "Test Negative Stock",
            "foto": None,
            "harga_modal": 100000,
            "harga_jual": 150000,
            "stok": -5, 
            "satuan": "PCS",
            "kategori": "Elektronik"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Stok minus seharusnya invalid")
