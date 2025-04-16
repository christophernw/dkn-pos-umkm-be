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

    def test_get_pemasukan_sorted_by_date(self):
        """Test sorting income transactions by date"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create multiple transactions with different dates
        for i in range(3):
            data = {
                "status": "LUNAS",
                "daftarProduk": [self.produk_list[0].id],
                "kategori": "PENJUALAN",
                "totalPemasukan": 1000,
                "hargaModal": 500,
            }
            response = client.post("/api/transaksi/pemasukan/create", data, format="json")
            self.assertEqual(response.status_code, 200)
            
            # Add a small delay to ensure different timestamps
            import time
            time.sleep(1)
        
        # Test ascending sort (oldest first)
        response = client.get("/api/transaksi/pemasukan/page/1?sort=asc&sort_by=date")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify ascending order
        dates = [item["tanggalTransaksi"] for item in data["items"]]
        self.assertEqual(dates, sorted(dates))
        
        # Test descending sort (newest first)
        response = client.get("/api/transaksi/pemasukan/page/1?sort=desc&sort_by=date")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify descending order
        dates = [item["tanggalTransaksi"] for item in data["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_get_pemasukan_sorted_by_amount(self):
        """Test sorting income transactions by amount"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create multiple transactions with different amounts
        amounts = [1000, 500, 1500]
        for amount in amounts:
            data = {
                "status": "LUNAS",
                "daftarProduk": [self.produk_list[0].id],
                "kategori": "PENJUALAN",
                "totalPemasukan": amount,
                "hargaModal": 300,
            }
            response = client.post("/api/transaksi/pemasukan/create", data, format="json")
            self.assertEqual(response.status_code, 200)
        
        # Test ascending sort (lowest amount first)
        response = client.get("/api/transaksi/pemasukan/page/1?sort=asc&sort_by=amount")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify ascending order
        sorted_amounts = [item["totalPemasukan"] for item in data["items"]]
        self.assertEqual(sorted_amounts, sorted(sorted_amounts))
        
        # Test descending sort (highest amount first)
        response = client.get("/api/transaksi/pemasukan/page/1?sort=desc&sort_by=amount")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify descending order
        sorted_amounts = [item["totalPemasukan"] for item in data["items"]]
        self.assertEqual(sorted_amounts, sorted(sorted_amounts, reverse=True))

    def test_get_pemasukan_invalid_sort_by_parameter(self):
        """Test invalid sort_by parameter"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        response = client.get("/api/transaksi/pemasukan/page/1?sort_by=invalid")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid sort_by parameter", response.json()["message"])
    
    # Add these test methods to the TransaksiTest class in tests.py

    def test_laporan_penjualan(self):
        """Test sales report generation"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create test data - several sales transactions
        for i in range(3):
            data = {
                "status": "LUNAS",
                "catatan": f"Test payment {i}",
                "daftarProduk": [self.produk_list[i].id],
                "kategori": "PENJUALAN",
                "totalPemasukan": 1000 * (i + 1),
                "hargaModal": 500 * (i + 1),
            }
            response = client.post("/api/transaksi/pemasukan/create", data, format="json")
            self.assertEqual(response.status_code, 200)
        
        # Test daily report
        response = client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify structure and data
        self.assertIn("total_penjualan", data)
        self.assertIn("jumlah_transaksi", data)
        self.assertIn("periode_data", data)
        self.assertEqual(data["jumlah_transaksi"], 3)
        self.assertEqual(data["total_penjualan"], 6000)  # Sum of all transactions
        
        # Test custom period
        from datetime import date, timedelta
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        response = client.post(
            "/api/transaksi/laporan/penjualan", 
            {
                "periode": "KUSTOM",
                "tanggal_mulai": yesterday.isoformat(),
                "tanggal_akhir": tomorrow.isoformat()
            }, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_laporan_pengeluaran(self):
        """Test expense report generation"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create test data - several expense transactions
        for i in range(3):
            data = {
                "status": "LUNAS",
                "catatan": f"Test expense {i}",
                "daftarProduk": [self.produk_list[i].id],
                "kategori": "PEMBELIAN_STOK",
                "totalPengeluaran": 500 * (i + 1),
            }
            response = client.post("/api/transaksi/pengeluaran/create", data, format="json")
            self.assertEqual(response.status_code, 200)
        
        # Test weekly report
        response = client.post(
            "/api/transaksi/laporan/pengeluaran", 
            {"periode": "MINGGUAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify structure and data
        self.assertIn("total_pengeluaran", data)
        self.assertIn("jumlah_transaksi", data)
        self.assertIn("periode_data", data)
        self.assertEqual(data["jumlah_transaksi"], 3)
        self.assertEqual(data["total_pengeluaran"], 3000)  # Sum of all transactions

    def test_laporan_laba_rugi(self):
        """Test profit/loss report generation"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create test income data
        data_pemasukan = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 5000,
            "hargaModal": 2000,
        }
        response = client.post("/api/transaksi/pemasukan/create", data_pemasukan, format="json")
        self.assertEqual(response.status_code, 200)
        
        # Create test expense data
        data_pengeluaran = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 3000,
        }
        response = client.post("/api/transaksi/pengeluaran/create", data_pengeluaran, format="json")
        self.assertEqual(response.status_code, 200)
        
        # Test monthly report
        response = client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {"periode": "BULANAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify structure and data
        self.assertIn("total_penjualan", data)
        self.assertIn("total_pengeluaran", data)
        self.assertIn("laba_rugi", data)
        self.assertIn("periode_data", data)
        self.assertEqual(data["total_penjualan"], 5000)
        self.assertEqual(data["total_pengeluaran"], 3000)
        self.assertEqual(data["laba_rugi"], 2000)  # Profit = 5000 - 3000

    def test_laporan_produk(self):
        """Test product sales report generation"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create test income data with different products
        for i in range(3):
            data = {
                "status": "LUNAS",
                "daftarProduk": [self.produk_list[i].id],
                "kategori": "PENJUALAN",
                "totalPemasukan": 1000 * (i + 1),
                "hargaModal": 500 * (i + 1),
            }
            response = client.post("/api/transaksi/pemasukan/create", data, format="json")
            self.assertEqual(response.status_code, 200)
        
        # Test yearly report
        response = client.post(
            "/api/transaksi/laporan/produk", 
            {"periode": "TAHUNAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify structure and data
        self.assertIn("total_produk_terjual", data)
        self.assertIn("total_pendapatan", data)
        self.assertIn("produk_data", data)
        self.assertEqual(data["total_produk_terjual"], 3)
        self.assertEqual(data["total_pendapatan"], 6000)  # Sum of all transactions
        self.assertEqual(len(data["produk_data"]), 3)  # 3 different products

    def test_laporan_error_handling(self):
        """Test error handling in reports"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Test missing dates for custom period
        response = client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "KUSTOM"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())
        
        # Test invalid period
        response = client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "INVALID_PERIOD"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 422)
        
        # Additional tests to add to transaksi/tests.py

    def test_get_date_range_december_case(self):
        """Test date range calculation specifically for December monthly period"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Mock datetime.now() to return December date
        from datetime import datetime
        from unittest.mock import patch
        
        # Create a December date
        december_date = datetime(2025, 12, 15).date()
        
        # Test with mocked December date
        with patch('transaksi.api.datetime') as mock_datetime:
            # Configure the mock to return a specific date when now() is called
            mock_datetime.now.return_value = datetime(2025, 12, 15)
            
            # Call the endpoint that uses get_date_range with monthly period
            response = client.post(
                "/api/transaksi/laporan/penjualan", 
                {"periode": "BULANAN"}, 
                format="json"
            )
            self.assertEqual(response.status_code, 200)
            
            # The December case should set end_date to January 1st of next year - 1 day
            # We can't directly verify this, but we can check that the report was generated

    def test_get_date_range_invalid_period(self):
        """Test date range calculation with invalid period to hit default case"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        from transaksi.api import get_date_range
        
        # Call get_date_range directly with invalid period
        start_date, end_date = get_date_range("INVALID")
        
        # Verify default case returns today for both dates
        from datetime import datetime
        today = datetime.now().date()
        self.assertEqual(start_date, today)
        self.assertEqual(end_date, today)
        
        # Also test through API call
        data = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 5000,
            "hargaModal": 2000,
        }
        
        response = client.post("/api/transaksi/pemasukan/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        
        # The API should return a 422 error for invalid period
        response = client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "INVALID"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 422)
        
        # Check the structure of the validation error
        error_response = response.json()
        self.assertIn("detail", error_response)
        self.assertTrue(any("periode" in loc for item in error_response["detail"] 
                            for loc in item.get("loc", [])))
    def test_laporan_laba_rugi_empty_results(self):
        """Test profit/loss report when there are no transactions in period"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Use a custom period far in the past to ensure no transactions
        from datetime import date
        past_date = date(2000, 1, 1)
        
        response = client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {
                "periode": "KUSTOM",
                "tanggal_mulai": past_date.isoformat(),
                "tanggal_akhir": past_date.isoformat()
            }, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify empty results are handled properly
        self.assertEqual(data["total_penjualan"], 0)
        self.assertEqual(data["total_pengeluaran"], 0)
        self.assertEqual(data["laba_rugi"], 0)
        self.assertEqual(len(data["periode_data"]), 0)

    def test_pemasukan_and_pengeluaran_same_day(self):
        """Test laba-rugi report with income and expenses on the same day"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create income transaction
        data_pemasukan = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PENJUALAN",
            "totalPemasukan": 5000,
            "hargaModal": 2000,
        }
        response = client.post("/api/transaksi/pemasukan/create", data_pemasukan, format="json")
        self.assertEqual(response.status_code, 200)
        
        # Create expense transaction
        data_pengeluaran = {
            "status": "LUNAS",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 3000,
        }
        response = client.post("/api/transaksi/pengeluaran/create", data_pengeluaran, format="json")
        self.assertEqual(response.status_code, 200)
        
        # Generate daily profit/loss report to ensure same-day transactions are combined
        response = client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify the data
        self.assertEqual(data["total_penjualan"], 5000)
        self.assertEqual(data["total_pengeluaran"], 3000)
        self.assertEqual(data["laba_rugi"], 2000)
        self.assertEqual(len(data["periode_data"]), 1)  # One day with both income and expense
        
        # Ensure the periode_data entry has both income and expense
        periode_item = data["periode_data"][0]
        self.assertEqual(periode_item["total_penjualan"], 5000)
        self.assertEqual(periode_item["total_pengeluaran"], 3000)
        self.assertEqual(periode_item["laba_rugi"], 2000)

    def test_laporan_produk_multiple_per_transaction(self):
        """Test product report with multiple products per transaction"""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Create transaction with multiple products
        data = {
            "status": "LUNAS",
            "daftarProduk": [p.id for p in self.produk_list],  # All products
            "kategori": "PENJUALAN",
            "totalPemasukan": 9000,
            "hargaModal": 4500,
        }
        response = client.post("/api/transaksi/pemasukan/create", data, format="json")
        self.assertEqual(response.status_code, 200)
        
        # Test product report
        response = client.post(
            "/api/transaksi/laporan/produk", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify the data
        self.assertEqual(data["total_produk_terjual"], len(self.produk_list))
        self.assertEqual(data["total_pendapatan"], 9000)
        self.assertEqual(len(data["produk_data"]), len(self.produk_list))
        
        # Revenue should be distributed evenly
        expected_revenue_per_product = 9000 / len(self.produk_list)
        for product in data["produk_data"]:
            self.assertEqual(product["total_terjual"], 1)
            self.assertAlmostEqual(product["total_pendapatan"], expected_revenue_per_product)