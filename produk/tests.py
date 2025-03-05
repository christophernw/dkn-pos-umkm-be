from django.test import TestCase, Client
from produk.models import Produk, KategoriProduk

class DeleteAPITest(TestCase):
    def setUp(self):
        self.client = Client()

        self.kategori_makanan = KategoriProduk.objects.create(nama="Makanan")
        self.kategori_minuman = KategoriProduk.objects.create(nama="Minuman")

        self.burger = Produk.objects.create(
            nama="Burger Keju",
            foto="burger_keju.png",
            harga_modal=18000,
            harga_jual=25000,
            stok=40,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        self.jus = Produk.objects.create(
            nama="Jus Alpukat",
            foto="jus_alpukat.png",
            harga_modal=5000,
            harga_jual=10000,
            stok=80,
            satuan="gelas",
            kategori=self.kategori_minuman,
        )
        self.pizza = Produk.objects.create(
            nama="Pizza Pepperoni",
            foto="pizza_pepperoni.png",
            harga_modal=30000,
            harga_jual=45000,
            stok=15,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        
    def test_produk_str(self):
        self.assertEqual(str(self.jus), "Jus Alpukat")

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori_minuman), "Minuman")
    
    def test_delete_produk_success(self):
        response = self.client.delete(f"/api/produk/delete/{1}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Produk berhasil dihapus"})
        self.assertFalse(Produk.objects.filter(id=1).exists())

    def test_delete_produk_not_found(self):
        response = self.client.delete(f"/api/produk/delete/{20}")
        self.assertEqual(response.status_code, 404)
    
    def test_delete_produk_invalid_id(self):
        response = self.client.delete("/api/produk/delete/invalid") # ID bukan angka
        self.assertEqual(response.status_code, 422)