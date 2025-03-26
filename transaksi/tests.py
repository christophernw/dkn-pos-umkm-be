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
            
        self.transaksi1 = Transaksi.objects.create(
            status="LUNAS",
            catatan="Pembayaran sukses",
            namaPelanggan="Budi",
            nomorTeleponPelanggan="08123456789"
        )
        self.transaksi1.daftarProduk.set(self.produk_list)  
        
        self.pemasukan = Pemasukan.objects.create(
            transaksi=self.transaksi1,
            kategori="PENJUALAN",
            totalPemasukan=50000.0,
            hargaModal=30000.0,
        )
        
        self.transaksi2 = Transaksi.objects.create(
            status="LUNAS",
            catatan="Pembayaran sukses",
            namaPelanggan="Budi",
            nomorTeleponPelanggan="08123456789"
        )
        self.transaksi2.daftarProduk.set(self.produk_list)  
        
        self.pengeluaran = Pengeluaran.objects.create(
            transaksi=self.transaksi2,
            kategori="PENGELUARAN_DI_LUAR_USAHA",
            totalPengeluaran=50000.0,
        )

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
        self.assertEqual(Pemasukan.objects.count(), 2) # 2 soalnya ada 1 pemasukan yang sudah ada di setup

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
            "harga_modal": -30000,
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
            "kategori": "BIAYA_OPERASIONAL",
            "totalPengeluaran": 10000,
        }
        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pengeluaran.objects.count(), 2) # 2 soalnya ada 1 pengeluaran yang sudah ada di setup
        
    def test_create_pengeluaran_pembelian_stok(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        data = {
            "status": "LUNAS",
            "catatan": "PEMBELIAN_STOK",
            "namaPelanggan": "Supplier B",
            "nomorTeleponPelanggan": "08234567890",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id, self.produk_list[1].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 99999
        }

        expected_total = sum([self.produk_list[0].harga_modal, self.produk_list[1].harga_modal])

        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        
        pengeluaran = Pengeluaran.objects.last()
        self.assertIsNotNone(pengeluaran)
        self.assertEqual(pengeluaran.totalPengeluaran, expected_total)

    def test_create_pengeluaran_empty_produk_list(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        data = {
            "status": "LUNAS",
            "catatan": "Pembelian stok kosong",
            "namaPelanggan": "Supplier D",
            "nomorTeleponPelanggan": "08456789012",
            "foto": "invoice.jpg",
            "daftarProduk": [],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 0
        }

        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        
        pengeluaran = Pengeluaran.objects.last()
        self.assertIsNotNone(pengeluaran)
        self.assertEqual(pengeluaran.totalPengeluaran, 0)

    def test_create_pengeluaran_negative_amount(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        data = {
            "status": "LUNAS",
            "catatan": "Pengeluaran negatif",
            "namaPelanggan": "Supplier E",
            "nomorTeleponPelanggan": "08567890123",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "BIAYA_OPERASIONAL",
            "totalPengeluaran": -5000
        }

        response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(response.status_code, 422)

    def test_get_pemasukan_list(self):
        response = self.client.get("/api/transaksi/pemasukan/daftar")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_pengeluaran_list(self):
        response = self.client.get("/api/transaksi/pengeluaran/daftar")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_pemasukan_by_id(self):
        response = self.client.get("/api/transaksi/pemasukan/1")
        self.assertEqual(response.status_code, 200)
        
    def test_get_pemasukan_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pemasukan/999")
        self.assertEqual(response.status_code, 404)
        
    def test_get_pengeluaran_by_id(self):
        response = self.client.get("/api/transaksi/pengeluaran/1")
        self.assertEqual(response.status_code, 200)

    def test_get_pengeluaran_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pengeluaran/999")
        self.assertEqual(response.status_code, 404)
