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
        self.user1 = User.objects.create_user(
            username="testuser1", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", password="password123"
        )

        # Create categories
        self.kategori1 = KategoriProduk.objects.create(nama="Minuman")
        self.kategori2 = KategoriProduk.objects.create(nama="Makanan")

        self.produk_list = []
        for i in range(1, 4):
            stok = i * 10
            produk = Produk.objects.create(
                nama=f"User1 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f"{i}000"),
                harga_jual=Decimal(f"{i+2}000"),
                stok=Decimal(stok),
                satuan="Pcs",
                kategori=self.kategori1 if i % 2 == 0 else self.kategori2,
                user=self.user1,
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
        pengeluaran_id = response.json()["id"]
        transaction_id = response.json()["transaksi"]["id"]

        delete_response = client.delete(
            f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete"
        )
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

        delete_response = client.delete(
            f"/api/transaksi/pengeluaran/{non_existent_id}/delete"
        )
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
        pengeluaran_id = response.json()["id"]

        delete_response = client.delete(
            f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete"
        )
        self.assertEqual(delete_response.status_code, 200)

        second_delete_response = client.delete(
            f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete"
        )
        self.assertEqual(second_delete_response.status_code, 404)

    def test_delete_pemasukan_success(self):
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
        pemasukan_id = response.json()["id"]
        transaction_id = response.json()["transaksi"]["id"]

        delete_response = client.delete(
            f"/api/transaksi/pemasukan/{pemasukan_id}/delete"
        )
        self.assertEqual(delete_response.status_code, 200)

        get_response = client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        self.assertEqual(get_response.status_code, 404)

        from .models import Transaksi

        transaction = Transaksi.objects.get(id=transaction_id)
        self.assertTrue(transaction.isDeleted)

    def test_delete_pemasukan_not_found(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        non_existent_id = 9999

        delete_response = client.delete(
            f"/api/transaksi/pemasukan/{non_existent_id}/delete"
        )
        self.assertEqual(delete_response.status_code, 404)

    def test_delete_pemasukan_already_deleted(self):
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
        pemasukan_id = response.json()["id"]

        delete_response = client.delete(
            f"/api/transaksi/pemasukan/{pemasukan_id}/delete"
        )
        self.assertEqual(delete_response.status_code, 200)

        second_delete_response = client.delete(
            f"/api/transaksi/pemasukan/{pemasukan_id}/delete"
        )
        self.assertEqual(second_delete_response.status_code, 404)


    def test_update_transaksi_success(self):
        # Create a transaction first
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create test transaction
        create_data = {
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

        response = client.post(
            "/api/transaksi/pemasukan/create", create_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        transaction_id = response.json()["transaksi"]["id"]
        pemasukan_id = response.json()["id"]

        # Update data
        update_data = {
            "status": "BELUM_LUNAS",
            "catatan": "Updated notes",
            "namaPelanggan": "Updated customer",
            "nomorTeleponPelanggan": "087654321",
            "daftarProduk": [self.produk_list[0].id],  # Only one product
        }

        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self.assertEqual(update_response.status_code, 200)

        # Verify changes
        get_response = client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(updated_transaction["status"], "BELUM_LUNAS")
        self.assertEqual(updated_transaction["catatan"], "Updated notes")
        self.assertEqual(len(updated_transaction["daftarProduk"]), 1)


    def test_update_nonexistent_transaksi(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        non_existent_id = 9999
        update_data = {"status": "BELUM_LUNAS"}

        update_response = client.put(
            f"/api/transaksi/transaksi/{non_existent_id}/update", update_data, format="json"
        )
        self.assertEqual(update_response.status_code, 404)


    def test_update_deleted_transaksi(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create and delete a transaction
        create_data = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }

        response = client.post(
            "/api/transaksi/pemasukan/create", create_data, format="json"
        )
        pemasukan_id = response.json()["id"]
        transaction_id = response.json()["transaksi"]["id"]

        # Delete the transaction
        client.delete(f"/api/transaksi/pemasukan/{pemasukan_id}/delete")

        # Try to update the deleted transaction
        update_data = {"status": "BELUM_LUNAS"}
        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self.assertEqual(update_response.status_code, 404)


    def test_update_transaksi_invalid_data(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create a transaction first
        create_data = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }

        response = client.post(
            "/api/transaksi/pemasukan/create", create_data, format="json"
        )
        transaction_id = response.json()["transaksi"]["id"]

        # Update with invalid status
        update_data = {"status": "INVALID_STATUS"}
        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self.assertEqual(update_response.status_code, 422)


    def test_update_transaksi_empty_payload(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create a transaction first
        create_data = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }

        response = client.post(
            "/api/transaksi/pemasukan/create", create_data, format="json"
        )
        transaction_id = response.json()["transaksi"]["id"]

        # Update with empty payload (should do nothing but succeed)
        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", {}, format="json"
        )
        self.assertEqual(update_response.status_code, 200)


    def test_update_transaksi_nonexistent_products(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Create a transaction first
        create_data = {
            "status": "LUNAS",
            "daftarProduk": [p.id for p in self.produk_list],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }

        response = client.post(
            "/api/transaksi/pemasukan/create", create_data, format="json"
        )
        transaction_id = response.json()["transaksi"]["id"]
        pemasukan_id = response.json()["id"]

        # Update with non-existent product ID
        update_data = {"daftarProduk": [9999]}
        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )

        # Should succeed but with empty product list
        self.assertEqual(update_response.status_code, 200)

        # Verify product list is empty
        get_response = client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(len(updated_transaction["daftarProduk"]), 0)
        
    def test_get_pemasukan_by_id_success(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create a pemasukan first
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
        
        create_response = client.post("/api/transaksi/pemasukan/create", data, format="json")
        self.assertEqual(create_response.status_code, 200)
        pemasukan_id = create_response.json()["id"]
        
        # Retrieve the pemasukan
        get_response = client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        self.assertEqual(get_response.status_code, 200)
        
        # Verify the retrieved data
        pemasukan_data = get_response.json()
        self.assertEqual(pemasukan_data["id"], pemasukan_id)
        self.assertEqual(pemasukan_data["kategori"], "PENJUALAN")
        self.assertEqual(pemasukan_data["totalPemasukan"], 50000.0)
        self.assertEqual(pemasukan_data["hargaModal"], 30000.0)
        
    def test_get_pengeluaran_by_id_success(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create a pengeluaran first
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
        
        create_response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
        self.assertEqual(create_response.status_code, 200)
        pengeluaran_id = create_response.json()["id"]
        
        # Retrieve the pengeluaran
        get_response = client.get(f"/api/transaksi/pengeluaran/{pengeluaran_id}")
        self.assertEqual(get_response.status_code, 200)
        
        # Verify the retrieved data
        pengeluaran_data = get_response.json()
        self.assertEqual(pengeluaran_data["id"], pengeluaran_id)
        self.assertEqual(pengeluaran_data["kategori"], "PEMBELIAN_STOK")
        self.assertEqual(pengeluaran_data["totalPengeluaran"], 10000)

    def test_update_transaksi_with_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create a transaction first
        create_data = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 50000.0,
            "hargaModal": 30000.0,
        }
        
        response = client.post("/api/transaksi/pemasukan/create", create_data, format="json")
        transaction_id = response.json()["transaksi"]["id"]
        pemasukan_id = response.json()["id"]
        
        # Create a test file
        SimpleUploadedFile(
            "test_image.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        # Update with a file - using a string representation as the API seems to accept strings
        update_data = {
            "foto": "updated_image.jpg"
        }
        
        update_response = client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", 
            update_data, 
            format="json"
        )
        
        self.assertEqual(update_response.status_code, 200)
        
        # Verify the file path was updated
        get_response = client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(updated_transaction["foto"], "/api/media/updated_image.jpg")
        
    def test_get_pemasukan_paginated(self):
        """Test paginated income list"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create 5 test income records
        for i in range(5):
            data = {
                "status": "LUNAS",
                "catatan": f"Test payment {i}",
                "daftarProduk": [self.produk_list[0].id],
                "kategori": "PENJUALAN",
                "totalPemasukan": 1000 * (i + 1),
                "hargaModal": 500 * (i + 1),
            }
            response = client.post("/api/transaksi/pemasukan/create", data, format="json")
            self.assertEqual(response.status_code, 200)
        
        # Test basic pagination - first page
        response = client.get("/api/transaksi/pemasukan/page/1?per_page=3")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify structure and counts
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["items"]), 3)
        
        # Test second page
        response = client.get("/api/transaksi/pemasukan/page/2?per_page=3")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"]), 2)  # 2 items on second page
        
        # Test sorting (ascending)
        response = client.get("/api/transaksi/pemasukan/page/1?sort=asc")
        self.assertEqual(response.status_code, 200)
        
        # Test search filter
        client.post("/api/transaksi/pemasukan/create", {
            "status": "LUNAS",
            "catatan": "Unique searchable text",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 9999,
            "hargaModal": 5000,
        }, format="json")
        
        response = client.get("/api/transaksi/pemasukan/page/1?q=Unique")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertIn("Unique", data["items"][0]["transaksi"]["catatan"])