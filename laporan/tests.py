# laporan/tests.py (fixed)
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.test.client import RequestFactory
from authentication.models import User, Toko
from transaksi.models import Transaksi
from .models import HutangPiutangReport, DetailHutangPiutang
from .api import get_hutang_piutang_summary, get_hutang_piutang_detail, generate_hutang_piutang_report, get_hutang_piutang_reports
import json
from decimal import Decimal
from datetime import datetime, date, timedelta
import jwt
from django.conf import settings
from unittest.mock import patch, MagicMock

class HutangPiutangAPITestCase(TestCase):
    def setUp(self):
        # Buat toko tanpa parameter (sesuai dengan model)
        self.toko = Toko.objects.create()
        
        # Buat user dan hubungkan dengan toko
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            toko=self.toko,
            role="Pemilik"
        )
        
        # Setup RequestFactory untuk menguji fungsi API langsung
        self.factory = RequestFactory()
        
        # Buat beberapa transaksi contoh
        # 1. Hutang (pengeluaran belum lunas)
        self.hutang1 = Transaksi.objects.create(
            id="HUTANG001",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pengeluaran",
            category="Pembelian Stok",
            total_amount=Decimal("100000"),
            amount=Decimal("100000"),
            status="Belum Lunas"
        )
        # Ubah created_at secara langsung setelah dibuat
        Transaksi.objects.filter(id="HUTANG001").update(
            created_at=timezone.now() - timedelta(days=5)
        )
        
        self.hutang2 = Transaksi.objects.create(
            id="HUTANG002",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pengeluaran",
            category="Biaya Operasional",
            total_amount=Decimal("50000"),
            amount=Decimal("50000"),
            status="Belum Lunas"
        )
        # Ubah created_at secara langsung setelah dibuat
        Transaksi.objects.filter(id="HUTANG002").update(
            created_at=timezone.now() - timedelta(days=3)
        )
        
        # 2. Piutang (pemasukan belum lunas) - Menambahkan ini untuk memperbaiki test
        self.piutang1 = Transaksi.objects.create(
            id="PIUTANG001",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pemasukan",
            category="Penjualan Barang",
            total_amount=Decimal("200000"),
            amount=Decimal("200000"),
            status="Belum Lunas"
        )
        # Ubah created_at secara langsung setelah dibuat
        Transaksi.objects.filter(id="PIUTANG001").update(
            created_at=timezone.now() - timedelta(days=2)
        )
        
        # 3. Transaksi lunas (tidak seharusnya dihitung)
        self.lunas = Transaksi.objects.create(
            id="LUNAS001",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pemasukan",
            category="Penjualan Barang",
            total_amount=Decimal("75000"),
            amount=Decimal("75000"),
            status="Lunas"
        )
        # Ubah created_at secara langsung setelah dibuat
        Transaksi.objects.filter(id="LUNAS001").update(
            created_at=timezone.now() - timedelta(days=2)
        )
    
    def _get_mocked_request(self, user_id=None):
        """Helper method untuk membuat request dengan autentikasi"""
        request = self.factory.get('/')
        request.auth = user_id or self.user.id
        return request
    
    def test_get_hutang_piutang_summary(self):
        """
        Test mendapatkan ringkasan hutang dan piutang
        """
        request = self._get_mocked_request()
        response = get_hutang_piutang_summary(request)
        
        # Objek response sudah berupa HutangPiutangSummaryResponse, tidak perlu json()
        self.assertEqual(response.total_hutang, 150000.0)  # 100000 + 50000
        self.assertEqual(response.total_piutang, 200000.0)  # Dari PIUTANG001
        self.assertEqual(response.jumlah_transaksi_hutang, 2)
        self.assertEqual(response.jumlah_transaksi_piutang, 1)
    
    def test_get_hutang_piutang_summary_no_toko(self):
        """
        Test mendapatkan ringkasan hutang dan piutang ketika user tidak memiliki toko
        """
        # Buat user baru tanpa toko
        user_no_toko = User.objects.create_user(
            username="notoko",
            email="notoko@example.com",
            password="testpassword",
            toko=None
        )
        
        request = self._get_mocked_request(user_no_toko.id)
        response = get_hutang_piutang_summary(request)
        
        self.assertEqual(response.total_hutang, 0)
        self.assertEqual(response.total_piutang, 0)
        self.assertEqual(response.jumlah_transaksi_hutang, 0)
        self.assertEqual(response.jumlah_transaksi_piutang, 0)
    
    def test_get_hutang_piutang_detail(self):
        """
        Test mendapatkan detail transaksi hutang dan piutang
        """
        request = self._get_mocked_request()
        response = get_hutang_piutang_detail(request)
        
        self.assertEqual(len(response.hutang), 2)
        self.assertEqual(len(response.piutang), 1)
        
        # Verifikasi data hutang
        hutang_ids = [h.id for h in response.hutang]
        self.assertIn('HUTANG001', hutang_ids)
        self.assertIn('HUTANG002', hutang_ids)
        
        # Verifikasi data piutang
        piutang_ids = [p.id for p in response.piutang]
        self.assertIn('PIUTANG001', piutang_ids)
    
    def test_generate_hutang_piutang_report(self):
        """
        Test membuat laporan hutang piutang untuk rentang tanggal
        """
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Buat payload request
        class MockPayload:
            def __init__(self, start_date, end_date):
                self.start_date = start_date
                self.end_date = end_date
        
        payload = MockPayload(yesterday, today)
        
        request = self._get_mocked_request()
        response = generate_hutang_piutang_report(request, payload)
        
        # Response adalah dict, bukan HttpResponse
        self.assertIn("message", response)
        self.assertIn("Berhasil membuat", response["message"])
        
        # Verifikasi bahwa laporan dibuat
        self.assertEqual(HutangPiutangReport.objects.count(), 2)  # 2 hari
        
        # Verifikasi laporan hari ini
        today_report = HutangPiutangReport.objects.get(tanggal=today)
        self.assertEqual(today_report.toko, self.toko)
        
        # Verifikasi detail laporan
        today_hutang_count = Transaksi.objects.filter(
            toko=self.toko,
            transaction_type="pengeluaran",
            status="Belum Lunas",
            is_deleted=False,
            created_at__date=today
        ).count()
        
        self.assertEqual(today_report.jumlah_transaksi_hutang, today_hutang_count)
        
        # Verifikasi detail transaksi disimpan
        detail_count = DetailHutangPiutang.objects.filter(report=today_report).count()
        self.assertEqual(detail_count, today_hutang_count + Transaksi.objects.filter(
            toko=self.toko,
            transaction_type="pemasukan",
            status="Belum Lunas",
            is_deleted=False,
            created_at__date=today
        ).count())
    
    def test_generate_hutang_piutang_report_no_toko(self):
        """
        Test membuat laporan hutang piutang ketika user tidak memiliki toko
        """
        # Buat user baru tanpa toko
        user_no_toko = User.objects.create_user(
            username="notoko2",
            email="notoko2@example.com",
            password="testpassword",
            toko=None
        )
        
        # Buat payload request
        class MockPayload:
            def __init__(self, start_date, end_date):
                self.start_date = start_date
                self.end_date = end_date
        
        payload = MockPayload(timezone.now().date(), timezone.now().date())
        
        request = self._get_mocked_request(user_no_toko.id)
        response = generate_hutang_piutang_report(request, payload)
        
        # Response adalah dict, bukan HttpResponse
        self.assertIn("message", response)
        self.assertIn("User tidak memiliki toko", response["message"])
    
    def test_get_hutang_piutang_reports(self):
        """
        Test mendapatkan daftar laporan hutang piutang dengan paginasi
        """
        # Buat beberapa laporan untuk pengujian
        today = timezone.now().date()
        
        for i in range(5):
            date = today - timedelta(days=i)
            HutangPiutangReport.objects.create(
                toko=self.toko,
                tanggal=date,
                total_hutang=Decimal(str(100 * (i + 1))),
                total_piutang=Decimal(str(200 * (i + 1))),
                jumlah_transaksi_hutang=i + 1,
                jumlah_transaksi_piutang=i + 2
            )
        
        # Test paginasi halaman pertama dengan 2 item per halaman
        request = self._get_mocked_request()
        response = get_hutang_piutang_reports(request, page=1, per_page=2)
        
        self.assertEqual(len(response.items), 2)
        self.assertEqual(response.total, 5)
        self.assertEqual(response.page, 1)
        self.assertEqual(response.per_page, 2)
        self.assertEqual(response.total_pages, 3)
        
        # Verifikasi urutan (tanggal terbaru dulu)
        self.assertEqual(response.items[0].tanggal, today)
        
        # Test paginasi halaman kedua
        request = self._get_mocked_request()
        response = get_hutang_piutang_reports(request, page=2, per_page=2)
        
        self.assertEqual(len(response.items), 2)
        self.assertEqual(response.page, 2)
        
        # Test filter tanggal
        three_days_ago = today - timedelta(days=3)
        request = self._get_mocked_request()
        response = get_hutang_piutang_reports(request, page=1, per_page=10, start_date=three_days_ago, end_date=today)
        
        self.assertEqual(len(response.items), 4)  # Hari ini + 3 hari sebelumnya
    
    def test_get_hutang_piutang_reports_no_toko(self):
        """
        Test mendapatkan daftar laporan hutang piutang ketika user tidak memiliki toko
        """
        # Buat user baru tanpa toko
        user_no_toko = User.objects.create_user(
            username="notoko3",
            email="notoko3@example.com",
            password="testpassword",
            toko=None
        )
        
        request = self._get_mocked_request(user_no_toko.id)
        response = get_hutang_piutang_reports(request)
        
        self.assertEqual(len(response.items), 0)
        self.assertEqual(response.total, 0)
    
    def test_edge_cases(self):
        """
        Test berbagai edge case dan corner case
        """
        # 1. Halaman yang tidak valid (melebihi total halaman)
        request = self._get_mocked_request()
        response = get_hutang_piutang_reports(request, page=9999)
        
        # Response adalah PaginatedHutangPiutangReportResponse, bukan HttpResponse
        self.assertEqual(response.page, 1)  # Harusnya kembali ke halaman 1 jika melebihi total
        
        # 2. Generate report dengan tanggal akhir lebih awal dari tanggal mulai
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        class MockPayload:
            def __init__(self, start_date, end_date):
                self.start_date = start_date
                self.end_date = end_date
        
        payload = MockPayload(today, yesterday)
        
        request = self._get_mocked_request()
        # Note: We removed the unused response variable here
        generate_hutang_piutang_report(request, payload)
        
        # Harusnya tetap berhasil (API akan menangani kasus ini)
        # We're not asserting anything here as we just want to make sure it runs without errors

    def test_get_hutang_piutang_detail_with_date_filter(self):
        """
        Test mendapatkan detail transaksi hutang dan piutang dengan filter tanggal
        """
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Create transactions but don't store references we don't need
        Transaksi.objects.create(
            id="TODAY001",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pengeluaran",
            category="Biaya Lain",
            total_amount=Decimal("25000"),
            amount=Decimal("25000"),
            status="Belum Lunas",
            created_at=timezone.now()
        )
        
        Transaksi.objects.create(
            id="TODAYPIUTANG",
            toko=self.toko,
            created_by=self.user,
            transaction_type="pemasukan",
            category="Penjualan Hari ini",
            total_amount=Decimal("35000"),
            amount=Decimal("35000"),
            status="Belum Lunas",
            created_at=timezone.now()
        )
        
        # Jangan filter tanggal dulu - verifikasi semua transaksi ada
        request = self._get_mocked_request()
        response = get_hutang_piutang_detail(request)
        
        # Verifikasi semua transaksi muncul
        hutang_ids = [h.id for h in response.hutang]
        self.assertIn('HUTANG001', hutang_ids)
        self.assertIn('HUTANG002', hutang_ids)
        self.assertIn('TODAY001', hutang_ids)
        
        piutang_ids = [p.id for p in response.piutang]
        self.assertIn('PIUTANG001', piutang_ids)
        self.assertIn('TODAYPIUTANG', piutang_ids)
        
        # Test filter dari seminggu lalu sampai kemarin (tidak termasuk hari ini)
        request = self._get_mocked_request()
        response = get_hutang_piutang_detail(request, start_date=week_ago, end_date=yesterday)

        # Seharusnya transaksi hari ini tidak termasuk
        hutang_ids = [h.id for h in response.hutang]
        self.assertNotIn('TODAY001', hutang_ids)
        self.assertIn('HUTANG001', hutang_ids)
        self.assertIn('HUTANG002', hutang_ids)
        
        piutang_ids = [p.id for p in response.piutang]
        self.assertNotIn('TODAYPIUTANG', piutang_ids)
        self.assertIn('PIUTANG001', piutang_ids)
        
        # Test filter hanya hari ini
        request = self._get_mocked_request()
        response = get_hutang_piutang_detail(request, start_date=today, end_date=today)
        
        # Seharusnya hanya transaksi hari ini yang termasuk
        hutang_ids = [h.id for h in response.hutang]
        self.assertIn('TODAY001', hutang_ids)
        self.assertNotIn('HUTANG001', hutang_ids)
        self.assertNotIn('HUTANG002', hutang_ids)
        
        piutang_ids = [p.id for p in response.piutang]
        self.assertIn('TODAYPIUTANG', piutang_ids)
        self.assertNotIn('PIUTANG001', piutang_ids)
    
    def test_additional_coverage(self):
        """
        Test untuk meningkatkan code coverage pada beberapa kasus yang belum diuji
        """
        # Test get_hutang_piutang_detail for user without toko
        user_no_toko = User.objects.create_user(
            username="notoko_detail",
            email="notoko_detail@example.com",
            password="testpassword",
            toko=None
        )
        
        request = self._get_mocked_request(user_no_toko.id)
        response = get_hutang_piutang_detail(request)
        
        # Should return empty lists
        self.assertEqual(len(response.hutang), 0)
        self.assertEqual(len(response.piutang), 0)
        
        # Test deleting old details when report is updated
        today = timezone.now().date()
        
        # Create initial report
        report = HutangPiutangReport.objects.create(
            toko=self.toko,
            tanggal=today,
            total_hutang=Decimal("1000"),
            total_piutang=Decimal("2000"),
            jumlah_transaksi_hutang=1,
            jumlah_transaksi_piutang=1
        )
        
        # Add some details
        DetailHutangPiutang.objects.create(
            report=report,
            transaksi_id="TEST001",
            jenis='hutang',
            jumlah=Decimal("1000"),
            tanggal_transaksi=timezone.now(),
            keterangan="Test"
        )
        
        # Verify detail exists
        self.assertEqual(DetailHutangPiutang.objects.filter(report=report).count(), 1)
        
        # Generate report for today (should update existing report)
        class MockPayload:
            def __init__(self, start_date, end_date):
                self.start_date = start_date
                self.end_date = end_date
        
        payload = MockPayload(today, today)
        
        request = self._get_mocked_request()
        # Note: we removed the unused response variable here
        generate_hutang_piutang_report(request, payload)
        
        # Old details should be deleted and new ones (if any) created
        updated_details = DetailHutangPiutang.objects.filter(report__tanggal=today)
        # This will be 0 if there are no transactions for today
        self.assertNotEqual(updated_details.count(), 1)  # Should not be the initial value
        
        # Test per_page <= 0 case
        request = self._get_mocked_request()
        response = get_hutang_piutang_reports(request, page=1, per_page=0)
        
        # Should default to 10
        self.assertEqual(response.per_page, 10)