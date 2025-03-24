from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User

from produk.models import KategoriProduk, Produk
from .models import Pemasukan, Pengeluaran, Transaksi
from .schemas import PemasukanCreate, PengeluaranCreate

class TransaksiTest(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", password="password123")
        self.user2 = User.objects.create_user(username="testuser2", password="password123")
        
        # Create categories
        self.kategori1 = KategoriProduk.objects.create(nama="Minuman")
        self.kategori2 = KategoriProduk.objects.create(nama="Makanan")
        
        self.produk_list = []
        for i in range(1, 4):
            stok = i * 10
            produk = Produk.objects.create(
                nama=f"User1 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f'{i}000'),
                harga_jual=Decimal(f'{i+2}000'),
                stok=Decimal(stok),
                satuan="Pcs",
                kategori=self.kategori1 if i % 2 == 0 else self.kategori2,
                user=self.user1
            )
            self.produk_list.append(produk)

    def test_create_pemasukan_success(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        data = {
            "status": "LUNAS",
            "catatan": "Pembayaran sukses",
            "namaPelanggan": "Budi",
            "nomorTeleponPelanggan": "08123456789",
            "foto": "image.jpg",
            "daftarProduk": [p.id for p in self.produk_list],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }
        
        response = client.post("/api/transaksi/pemasukan/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pemasukan.objects.count(), 1)

    def test_create_pemasukan_invalid_data(self):
        client = APIClient()
        client.force_authenticate(user=self.user2)
        
        data = {
            "status": "",
            "catatan": "",
            "namaPelanggan": "",
            "nomorTeleponPelanggan": "",
            "foto": "",
            "daftarProduk": [],
            "kategori": "",
            "totalPemasukan": -50000,
            "hargaModal": -30000,
        }
        response = client.post("/api/transaksi/pemasukan/create", data, format="json")
        self.assertEqual(response.status_code, 422)

    def test_create_pengeluaran_success(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        data = {
            "status": "LUNAS",
            "catatan": "Pembelian stok",
            "namaPelanggan": "Supplier A",
            "nomorTeleponPelanggan": "08987654321",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 10000,
        }
        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pengeluaran.objects.count(), 1)

    def test_get_pemasukan_list(self):
        response = self.client.get("/api/transaksi/pemasukan/daftar")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_pengeluaran_list(self):
        response = self.client.get("/api/transaksi/pengeluaran/daftar")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_pemasukan_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pemasukan/999")
        self.assertEqual(response.status_code, 404)

    def test_get_pengeluaran_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pengeluaran/999")
        self.assertEqual(response.status_code, 404)

    def test_delete_pengeluaran_success(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        data = {
            "status": "LUNAS",
            "catatan": "Pembelian stok",
            "namaPelanggan": "Supplier A",
            "nomorTeleponPelanggan": "08987654321",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 10000,
        }
        
        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        pengeluaran_id = response.json()['id']
        transaction_id = response.json()['transaksi']['id']
        
        delete_response = client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self.assertEqual(delete_response.status_code, 200)
        
        get_response = client.get(f"/api/transaksi/pengeluaran/{pengeluaran_id}")
        self.assertEqual(get_response.status_code, 404)
        
        from .models import Transaksi
        transaction = Transaksi.objects.get(id=transaction_id)
        self.assertTrue(transaction.isDeleted)

    def test_delete_pengeluaran_not_found(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        non_existent_id = 9999
        
        delete_response = client.delete(f"/api/transaksi/pengeluaran/{non_existent_id}/delete")
        self.assertEqual(delete_response.status_code, 404)

    def test_delete_pengeluaran_already_deleted(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        data = {
            "status": "LUNAS",
            "catatan": "Pembelian stok",
            "namaPelanggan": "Supplier A",
            "nomorTeleponPelanggan": "08987654321",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 10000,
        }
        
        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        pengeluaran_id = response.json()['id']
        
        delete_response = client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self.assertEqual(delete_response.status_code, 200)
        
        second_delete_response = client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self.assertEqual(second_delete_response.status_code, 404)