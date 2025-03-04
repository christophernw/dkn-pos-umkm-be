from django.test import TestCase, Client
from .models import Produk, KategoriProduk

class ProdukSearchAPITest(TestCase):
    def setUp(self):
        self.client = Client()

        self.kategori_makanan = KategoriProduk.objects.create(nama="Makanan")
        self.kategori_minuman = KategoriProduk.objects.create(nama="Minuman")

        self.nasi = Produk.objects.create(
            nama="Nasi Goreng",
            foto="nasi_goreng.png",
            harga_modal=15000,
            harga_jual=20000,
            stok=50,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        self.teh = Produk.objects.create(
            nama="Es Teh Manis",
            foto="es_teh.png",
            harga_modal=3000,
            harga_jual=5000,
            stok=100,
            satuan="gelas",
            kategori=self.kategori_minuman,
        )
        self.ayam = Produk.objects.create(
            nama="Ayam Bakar",
            foto="ayam_bakar.png",
            harga_modal=25000,
            harga_jual=35000,
            stok=20,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        
    def test_produk_str(self):
        self.assertEqual(str(self.teh), "Es Teh Manis")

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori_minuman), "Minuman")
    
    def test_search_success(self):
        response = self.client.get("/api/produk/search?q=nasi")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["nama"], "Nasi Goreng")

    def test_search_multiple_results(self):
        response = self.client.get("/api/produk/search?q=a")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)

    def test_search_case_insensitive(self):
        response = self.client.get("/api/produk/search?q=NASI")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["nama"], "Nasi Goreng")

    def test_search_no_results(self):
        response = self.client.get("/api/produk/search?q=pizza")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_search_empty_query(self):
        response = self.client.get("/api/produk/search?q=")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 3)  # Harusnya mengembalikan semua produk

    def test_search_special_characters(self):
        response = self.client.get("/api/produk/search?q=@!#$$%")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_search_numeric_query(self):
        response = self.client.get("/api/produk/search?q=123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
