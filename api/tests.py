from django.test import TestCase, Client
from api.models import Produk, KategoriProduk

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

    def test_get_produk_success(self):
        response = self.client.get("/api/produk")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)

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
