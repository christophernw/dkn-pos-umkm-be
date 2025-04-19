from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
from unittest.mock import patch

from produk.models import KategoriProduk, Produk
from .models import Pemasukan, Pengeluaran, Transaksi
from .api import get_date_range


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

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

        # Create test products
        self.produk_list = self._create_test_products()

    def _create_test_products(self, count=3):
        """Helper method to create test products"""
        products = []
        for i in range(1, count + 1):
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
            products.append(produk)
        return products

    def _create_pemasukan(self, **kwargs):
        """Helper method to create standard income transaction"""
        default_data = {
            "status": "LUNAS",
            "catatan": "Pembayaran sukses",
            "namaPelanggan": "Budi",
            "nomorTeleponPelanggan": "08123456789",
            "foto": "image.jpg",
            "daftarProduk": [p.id for p in self.produk_list],
            "kategori": "PENJUALAN",
            "totalPemasukan": 5000.0,
            "hargaModal": 2000.0,
        }
        # Override defaults with any provided values
        data = {**default_data, **kwargs}
        response = self.client.post("/api/transaksi/pemasukan/create", data, format="json")
        return response

    def _create_pengeluaran(self, **kwargs):
        """Helper method to create standard expense transaction"""
        default_data = {
            "status": "LUNAS",
            "catatan": "Pembelian stok",
            "namaPelanggan": "Supplier A",
            "nomorTeleponPelanggan": "08987654321",
            "foto": "invoice.jpg",
            "daftarProduk": [self.produk_list[0].id],
            "kategori": "PEMBELIAN_STOK",
            "totalPengeluaran": 3000,
        }
        # Override defaults with any provided values
        data = {**default_data, **kwargs}
        response = self.client.post("/api/transaksi/pengeluaran/create", data, format="json")
        return response

    def _assert_response_status(self, response, expected_status=200):
        """Helper method to assert response status"""
        self.assertEqual(response.status_code, expected_status)

    def _assert_object_count(self, model_class, expected_count):
        """Helper method to assert object count in database"""
        self.assertEqual(model_class.objects.count(), expected_count)

    # TESTS FOR PEMASUKAN (INCOME)
    def test_create_pemasukan_success(self):
        response = self._create_pemasukan()
        self._assert_response_status(response)
        self._assert_object_count(Pemasukan, 1)

    def test_create_pemasukan_invalid_data(self):
        # Create authenticated client for user2
        client2 = APIClient()
        client2.force_authenticate(user=self.user2)
        
        invalid_data = {
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
        response = client2.post("/api/transaksi/pemasukan/create", invalid_data, format="json")
        self._assert_response_status(response, 422)

    def test_get_pemasukan_list(self):
        response = self.client.get("/api/transaksi/pemasukan/daftar")
        self._assert_response_status(response)
        self.assertIsInstance(response.json(), list)

    def test_get_pemasukan_by_id_success(self):
        # Create a pemasukan first
        create_response = self._create_pemasukan()
        pemasukan_id = create_response.json()["id"]
        
        # Retrieve the pemasukan
        get_response = self.client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        self._assert_response_status(get_response)
        
        # Verify the retrieved data
        pemasukan_data = get_response.json()
        self.assertEqual(pemasukan_data["id"], pemasukan_id)
        self.assertEqual(pemasukan_data["kategori"], "PENJUALAN")
        self.assertEqual(pemasukan_data["totalPemasukan"], 5000.0)
        self.assertEqual(pemasukan_data["hargaModal"], 2000.0)
        
    def test_get_pemasukan_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pemasukan/999")
        self._assert_response_status(response, 404)

    def test_delete_pemasukan_success(self):
        # Create a pemasukan
        create_response = self._create_pemasukan()
        pemasukan_id = create_response.json()["id"]
        transaction_id = create_response.json()["transaksi"]["id"]

        # Delete the pemasukan
        delete_response = self.client.delete(f"/api/transaksi/pemasukan/{pemasukan_id}/delete")
        self._assert_response_status(delete_response)

        # Check that the pemasukan is not found
        get_response = self.client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        self._assert_response_status(get_response, 404)

        # Check that the transaction is marked as deleted
        transaction = Transaksi.objects.get(id=transaction_id)
        self.assertTrue(transaction.isDeleted)

    def test_delete_pemasukan_not_found(self):
        delete_response = self.client.delete("/api/transaksi/pemasukan/9999/delete")
        self._assert_response_status(delete_response, 404)

    def test_delete_pemasukan_already_deleted(self):
        # Create and delete a pemasukan
        create_response = self._create_pemasukan()
        pemasukan_id = create_response.json()["id"]
        
        first_delete = self.client.delete(f"/api/transaksi/pemasukan/{pemasukan_id}/delete")
        self._assert_response_status(first_delete)
        
        second_delete = self.client.delete(f"/api/transaksi/pemasukan/{pemasukan_id}/delete")
        self._assert_response_status(second_delete, 404)

    # TESTS FOR PENGELUARAN (EXPENSE)
    def test_create_pengeluaran_success(self):
        response = self._create_pengeluaran()
        self._assert_response_status(response)
        self._assert_object_count(Pengeluaran, 1)

    def test_get_pengeluaran_list(self):
        response = self.client.get("/api/transaksi/pengeluaran/daftar")
        self._assert_response_status(response)
        self.assertIsInstance(response.json(), list)

    def test_get_pengeluaran_by_id_success(self):
        # Create a pengeluaran first
        create_response = self._create_pengeluaran()
        pengeluaran_id = create_response.json()["id"]
        
        # Retrieve the pengeluaran
        get_response = self.client.get(f"/api/transaksi/pengeluaran/{pengeluaran_id}")
        self._assert_response_status(get_response)
        
        # Verify the retrieved data
        pengeluaran_data = get_response.json()
        self.assertEqual(pengeluaran_data["id"], pengeluaran_id)
        self.assertEqual(pengeluaran_data["kategori"], "PEMBELIAN_STOK")
        self.assertEqual(pengeluaran_data["totalPengeluaran"], 3000)

    def test_get_pengeluaran_by_id_not_found(self):
        response = self.client.get("/api/transaksi/pengeluaran/999")
        self._assert_response_status(response, 404)

    def test_delete_pengeluaran_success(self):
        # Create a pengeluaran
        create_response = self._create_pengeluaran()
        pengeluaran_id = create_response.json()["id"]
        transaction_id = create_response.json()["transaksi"]["id"]

        # Delete the pengeluaran
        delete_response = self.client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self._assert_response_status(delete_response)

        # Check that the pengeluaran is not found
        get_response = self.client.get(f"/api/transaksi/pengeluaran/{pengeluaran_id}")
        self._assert_response_status(get_response, 404)

        # Check that the transaction is marked as deleted
        transaction = Transaksi.objects.get(id=transaction_id)
        self.assertTrue(transaction.isDeleted)

    def test_delete_pengeluaran_not_found(self):
        delete_response = self.client.delete("/api/transaksi/pengeluaran/9999/delete")
        self._assert_response_status(delete_response, 404)

    def test_delete_pengeluaran_already_deleted(self):
        # Create and delete a pengeluaran
        create_response = self._create_pengeluaran()
        pengeluaran_id = create_response.json()["id"]
        
        first_delete = self.client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self._assert_response_status(first_delete)
        
        second_delete = self.client.delete(f"/api/transaksi/pengeluaran/{pengeluaran_id}/delete")
        self._assert_response_status(second_delete, 404)

    # TESTS FOR TRANSACTION UPDATES
    def test_update_transaksi_success(self):
        # Create a transaction
        create_response = self._create_pemasukan()
        transaction_id = create_response.json()["transaksi"]["id"]
        pemasukan_id = create_response.json()["id"]

        # Update the transaction
        update_data = {
            "status": "BELUM_LUNAS",
            "catatan": "Updated notes",
            "namaPelanggan": "Updated customer",
            "nomorTeleponPelanggan": "087654321",
            "daftarProduk": [self.produk_list[0].id],  # Only one product
        }
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self._assert_response_status(update_response)

        # Verify changes
        get_response = self.client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(updated_transaction["status"], "BELUM_LUNAS")
        self.assertEqual(updated_transaction["catatan"], "Updated notes")
        self.assertEqual(len(updated_transaction["daftarProduk"]), 1)

    def test_update_nonexistent_transaksi(self):
        update_data = {"status": "BELUM_LUNAS"}
        update_response = self.client.put(
            "/api/transaksi/transaksi/9999/update", update_data, format="json"
        )
        self._assert_response_status(update_response, 404)

    def test_update_deleted_transaksi(self):
        # Create and delete a transaction
        create_response = self._create_pemasukan()
        pemasukan_id = create_response.json()["id"]
        transaction_id = create_response.json()["transaksi"]["id"]

        # Delete the transaction
        self.client.delete(f"/api/transaksi/pemasukan/{pemasukan_id}/delete")

        # Try to update the deleted transaction
        update_data = {"status": "BELUM_LUNAS"}
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self._assert_response_status(update_response, 404)

    def test_update_transaksi_invalid_data(self):
        # Create a transaction
        create_response = self._create_pemasukan()
        transaction_id = create_response.json()["transaksi"]["id"]

        # Update with invalid status
        update_data = {"status": "INVALID_STATUS"}
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self._assert_response_status(update_response, 422)

    def test_update_transaksi_empty_payload(self):
        # Create a transaction
        create_response = self._create_pemasukan()
        transaction_id = create_response.json()["transaksi"]["id"]

        # Update with empty payload
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", {}, format="json"
        )
        self._assert_response_status(update_response)

    def test_update_transaksi_nonexistent_products(self):
        # Create a transaction
        create_response = self._create_pemasukan()
        transaction_id = create_response.json()["transaksi"]["id"]
        pemasukan_id = create_response.json()["id"]

        # Update with non-existent product ID
        update_data = {"daftarProduk": [9999]}
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", update_data, format="json"
        )
        self._assert_response_status(update_response)

        # Verify product list is empty
        get_response = self.client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(len(updated_transaction["daftarProduk"]), 0)

    def test_update_transaksi_with_file(self):
        # Create a transaction
        create_response = self._create_pemasukan()
        transaction_id = create_response.json()["transaksi"]["id"]
        pemasukan_id = create_response.json()["id"]
        
        # Update with a file
        update_data = {"foto": "updated_image.jpg"}
        update_response = self.client.put(
            f"/api/transaksi/transaksi/{transaction_id}/update", 
            update_data, 
            format="json"
        )
        self._assert_response_status(update_response)
        
        # Verify the file path was updated
        get_response = self.client.get(f"/api/transaksi/pemasukan/{pemasukan_id}")
        updated_transaction = get_response.json()["transaksi"]
        self.assertEqual(updated_transaction["foto"], "/api/media/updated_image.jpg")

    # PAGINATION TESTS
    def _create_multiple_pemasukan(self, count=5):
        """Helper to create multiple income transactions"""
        for i in range(count):
            self._create_pemasukan(
                catatan=f"Test payment {i}",
                totalPemasukan=1000 * (i + 1),
                hargaModal=500 * (i + 1),
            )

    def test_get_pemasukan_paginated(self):
        # Create 5 test income records
        self._create_multiple_pemasukan(5)
        
        # Test first page
        response = self.client.get("/api/transaksi/pemasukan/page/1?per_page=3")
        self._assert_response_status(response)
        data = response.json()
        
        # Verify structure and counts
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["items"]), 3)
        
        # Test second page
        response = self.client.get("/api/transaksi/pemasukan/page/2?per_page=3")
        self._assert_response_status(response)
        data = response.json()
        self.assertEqual(len(data["items"]), 2)

    def test_get_pemasukan_sorted_by_date(self):
        # Create multiple transactions with different dates
        for i in range(3):
            self._create_pemasukan()
            import time
            time.sleep(1)  # Ensure different timestamps
        
        # Test ascending sort
        response = self.client.get("/api/transaksi/pemasukan/page/1?sort=asc&sort_by=date")
        self._assert_response_status(response)
        data = response.json()
        
        # Verify ascending order
        dates = [item["tanggalTransaksi"] for item in data["items"]]
        self.assertEqual(dates, sorted(dates))
        
        # Test descending sort
        response = self.client.get("/api/transaksi/pemasukan/page/1?sort=desc&sort_by=date")
        self._assert_response_status(response)
        data = response.json()
        
        # Verify descending order
        dates = [item["tanggalTransaksi"] for item in data["items"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_get_pemasukan_sorted_by_amount(self):
        # Create multiple transactions with different amounts
        amounts = [1000, 500, 1500]
        for amount in amounts:
            self._create_pemasukan(totalPemasukan=amount, hargaModal=300)
        
        # Test ascending sort
        response = self.client.get("/api/transaksi/pemasukan/page/1?sort=asc&sort_by=amount")
        self._assert_response_status(response)
        data = response.json()
        
        # Verify ascending order
        sorted_amounts = [item["totalPemasukan"] for item in data["items"]]
        self.assertEqual(sorted_amounts, sorted(sorted_amounts))
        
        # Test descending sort
        response = self.client.get("/api/transaksi/pemasukan/page/1?sort=desc&sort_by=amount")
        self._assert_response_status(response)
        data = response.json()
        
        # Verify descending order
        sorted_amounts = [item["totalPemasukan"] for item in data["items"]]
        self.assertEqual(sorted_amounts, sorted(sorted_amounts, reverse=True))

    def test_get_pemasukan_invalid_sort_by_parameter(self):
        response = self.client.get("/api/transaksi/pemasukan/page/1?sort_by=invalid")
        self._assert_response_status(response, 400)
        self.assertIn("Invalid sort_by parameter", response.json()["message"])

    # LAPORAN (REPORT) TESTS
    def test_laporan_penjualan(self):
        # Create test data - several sales transactions
        for i in range(3):
            self._create_pemasukan(
                catatan=f"Test payment {i}",
                daftarProduk=[self.produk_list[i].id],
                totalPemasukan=1000 * (i + 1),
                hargaModal=500 * (i + 1),
            )
        
        # Test daily report
        response = self.client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertIn("total_penjualan", data)
        self.assertIn("jumlah_transaksi", data)
        self.assertIn("periode_data", data)
        self.assertEqual(data["jumlah_transaksi"], 3)
        self.assertEqual(data["total_penjualan"], 6000)
        
        # Test custom period
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        response = self.client.post(
            "/api/transaksi/laporan/penjualan", 
            {
                "periode": "KUSTOM",
                "tanggal_mulai": yesterday.isoformat(),
                "tanggal_akhir": tomorrow.isoformat()
            }, 
            format="json"
        )
        self._assert_response_status(response)

    def test_laporan_pengeluaran(self):
        # Create test data - several expense transactions
        for i in range(3):
            self._create_pengeluaran(
                catatan=f"Test expense {i}",
                daftarProduk=[self.produk_list[i].id],
                totalPengeluaran=500 * (i + 1),
            )
        
        # Test weekly report
        response = self.client.post(
            "/api/transaksi/laporan/pengeluaran", 
            {"periode": "MINGGUAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertIn("total_pengeluaran", data)
        self.assertIn("jumlah_transaksi", data)
        self.assertIn("periode_data", data)
        self.assertEqual(data["jumlah_transaksi"], 3)
        self.assertEqual(data["total_pengeluaran"], 3000)

    def test_laporan_laba_rugi(self):
        # Create test income and expense data
        self._create_pemasukan(totalPemasukan=5000, hargaModal=2000)
        self._create_pengeluaran(totalPengeluaran=3000)
        
        # Test monthly report
        response = self.client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {"periode": "BULANAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertEqual(data["total_penjualan"], 5000)
        self.assertEqual(data["total_pengeluaran"], 3000)
        self.assertEqual(data["laba_rugi"], 2000)

    def test_laporan_produk(self):
        # Create test income data with different products
        for i in range(3):
            self._create_pemasukan(
                daftarProduk=[self.produk_list[i].id],
                totalPemasukan=1000 * (i + 1),
                hargaModal=500 * (i + 1),
            )
        
        # Test yearly report
        response = self.client.post(
            "/api/transaksi/laporan/produk", 
            {"periode": "TAHUNAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertEqual(data["total_produk_terjual"], 3)
        self.assertEqual(data["total_pendapatan"], 6000)
        self.assertEqual(len(data["produk_data"]), 3)

    def test_laporan_error_handling(self):
        # Test missing dates for custom period
        response = self.client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "KUSTOM"}, 
            format="json"
        )
        self._assert_response_status(response, 422)
        self.assertIn("error", response.json())
        
        # Test invalid period
        response = self.client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "INVALID_PERIOD"}, 
            format="json"
        )
        self._assert_response_status(response, 422)
        
    def test_get_date_range_december_case(self):
        # Mock datetime.now() to return December date
        with patch('transaksi.api.datetime') as mock_datetime:
            # Configure the mock to return a specific date when now() is called
            mock_datetime.now.return_value = datetime(2025, 12, 15)
            
            # Call the endpoint that uses get_date_range with monthly period
            response = self.client.post(
                "/api/transaksi/laporan/penjualan", 
                {"periode": "BULANAN"}, 
                format="json"
            )
            self._assert_response_status(response)

    def test_get_date_range_invalid_period(self):
        # Call get_date_range directly with invalid period
        start_date, end_date = get_date_range("INVALID")
        
        # Verify default case returns today for both dates
        today = datetime.now().date()
        self.assertEqual(start_date, today)
        self.assertEqual(end_date, today)
        
        # Test through API call
        self._create_pemasukan()
        
        # The API should return a 422 error for invalid period
        response = self.client.post(
            "/api/transaksi/laporan/penjualan", 
            {"periode": "INVALID"}, 
            format="json"
        )
        self._assert_response_status(response, 422)
        
        # Check the structure of the validation error
        error_response = response.json()
        self.assertIn("detail", error_response)
        self.assertTrue(any("periode" in loc for item in error_response["detail"] 
                        for loc in item.get("loc", [])))

    def test_laporan_laba_rugi_empty_results(self):
        # Use a custom period far in the past to ensure no transactions
        past_date = date(2000, 1, 1)
        
        response = self.client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {
                "periode": "KUSTOM",
                "tanggal_mulai": past_date.isoformat(),
                "tanggal_akhir": past_date.isoformat()
            }, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify empty results are handled properly
        self.assertEqual(data["total_penjualan"], 0)
        self.assertEqual(data["total_pengeluaran"], 0)
        self.assertEqual(data["laba_rugi"], 0)
        self.assertEqual(len(data["periode_data"]), 0)

    def test_pemasukan_and_pengeluaran_same_day(self):
        # Create income and expense transactions on the same day
        self._create_pemasukan(totalPemasukan=5000, hargaModal=2000)
        self._create_pengeluaran(totalPengeluaran=3000)
        
        # Generate daily profit/loss report
        response = self.client.post(
            "/api/transaksi/laporan/laba-rugi", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertEqual(data["total_penjualan"], 5000)
        self.assertEqual(data["total_pengeluaran"], 3000)
        self.assertEqual(data["laba_rugi"], 2000)
        self.assertEqual(len(data["periode_data"]), 1)
        
        # Verify period item
        periode_item = data["periode_data"][0]
        self.assertEqual(periode_item["total_penjualan"], 5000)
        self.assertEqual(periode_item["total_pengeluaran"], 3000)
        self.assertEqual(periode_item["laba_rugi"], 2000)

    def test_laporan_produk_multiple_per_transaction(self):
        # Create transaction with multiple products
        self._create_pemasukan(
            daftarProduk=[p.id for p in self.produk_list],
            totalPemasukan=9000,
            hargaModal=4500,
        )
        
        # Test product report
        response = self.client.post(
            "/api/transaksi/laporan/produk", 
            {"periode": "HARIAN"}, 
            format="json"
        )
        self._assert_response_status(response)
        data = response.json()
        
        # Verify data
        self.assertEqual(data["total_produk_terjual"], len(self.produk_list))
        self.assertEqual(data["total_pendapatan"], 9000)
        self.assertEqual(len(data["produk_data"]), len(self.produk_list))
        
        # Check revenue distribution
        expected_revenue_per_product = 9000 / len(self.produk_list)
        for product in data["produk_data"]:
            self.assertEqual(product["total_terjual"], 1)
            self.assertAlmostEqual(product["total_pendapatan"], expected_revenue_per_product)