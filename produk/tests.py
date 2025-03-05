from django.test import TestCase, Client
from produk.models import Produk, KategoriProduk

class DeleteAPITest(TestCase):
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
    
    def test_produk_str(self):
        self.assertEqual(str(self.produk["Es Teh Manis"]), "Es Teh Manis")

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori["minuman"]), "Minuman")
    
    def test_delete_produk_success(self):
        response = self.client.delete(f"/api/produk/delete/{self.produk['Nasi Goreng'].id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Produk berhasil dihapus"})
        self.assertFalse(Produk.objects.filter(id=self.produk['Nasi Goreng'].id).exists())

    def test_delete_produk_not_found(self):
        response = self.client.delete(f"/api/produk/delete/{20}")  # ID yang tidak ada
        self.assertEqual(response.status_code, 404)
    
    def test_delete_produk_invalid_id(self):
        response = self.client.delete("/api/produk/delete/invalid")  # ID bukan angka
        self.assertEqual(response.status_code, 422)
