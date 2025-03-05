from django.test import TestCase, Client
from produk.models import Produk, KategoriProduk

class ProdukSearchAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Membuat kategori
        self.kategori = {
            "makanan": KategoriProduk.objects.create(nama="Makanan"),
            "minuman": KategoriProduk.objects.create(nama="Minuman")
        }
        
        # Data produk
        self.produk_data = [
            {"nama": "Nasi Goreng", "foto": "nasi_goreng.png", "harga_modal": 15000, "harga_jual": 20000, "stok": 50, "satuan": "porsi", "kategori": self.kategori["makanan"]},
            {"nama": "Es Teh Manis", "foto": "es_teh.png", "harga_modal": 3000, "harga_jual": 5000, "stok": 100, "satuan": "gelas", "kategori": self.kategori["minuman"]},
            {"nama": "Ayam Bakar", "foto": "ayam_bakar.png", "harga_modal": 25000, "harga_jual": 35000, "stok": 20, "satuan": "porsi", "kategori": self.kategori["makanan"]},
        ]
        
        # Membuat produk secara dinamis
        self.produk = {p["nama"]: Produk.objects.create(**p) for p in self.produk_data}
    
    def search_produk(self, query):
        return self.client.get(f"/api/search/produk?q={query}")
    
    def test_search_success(self):
        response = self.search_produk("nasi")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["nama"], "Nasi Goreng")

    def test_search_multiple_results(self):
        response = self.search_produk("a")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)

    def test_search_case_insensitive(self):
        response = self.search_produk("NASI")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["nama"], "Nasi Goreng")

    def test_search_no_results(self):
        response = self.search_produk("pizza")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_search_empty_query(self):
        response = self.search_produk("")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 3)  # Harusnya mengembalikan semua produk

    def test_search_special_characters(self):
        response = self.search_produk("@!#$$%")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_search_numeric_query(self):
        response = self.search_produk("123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
