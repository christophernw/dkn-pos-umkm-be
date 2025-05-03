from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from datetime import date, datetime
from django.utils import timezone
from decimal import Decimal
from django.http import StreamingHttpResponse
import json

from authentication.models import Toko, User 
from laporan.models import ArusKasReport, DetailArusKas, DetailHutangPiutang, HutangPiutangReport
from laporan.schemas import IncomeStatementLine
from transaksi.models import Transaksi
from laporan.api import aruskas_report, available_months, income_statement, download_income_statement, _aggregate
from laporan.utils import _format_parentheses, build_csv
from io import StringIO
from rest_framework.test import APIClient


class IncomeStatementTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.toko = Toko.objects.create()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            toko=self.toko,
            role="Pemilik"
        )

        # Income
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pemasukan",
            category="Penjualan Barang",
            total_amount=Decimal("1000.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("1000.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 15, 10, 0),
        )
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pemasukan",
            category="Pendapatan Pinjaman",
            total_amount=Decimal("200.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("200.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 16, 11, 0),
        )
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pemasukan",
            category="Pendapatan Lain-Lain",
            total_amount=Decimal("300.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("300.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 17, 12, 0),
        )

        # Expenses
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pengeluaran",
            category="Pembelian Stok",
            total_amount=Decimal("1200.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("1200.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 18, 13, 0),
        )
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pengeluaran",
            category="Pembelian Bahan Baku",
            total_amount=Decimal("100.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("100.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 19, 14, 0),
        )
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pengeluaran",
            category="Biaya Operasional",
            total_amount=Decimal("100.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("100.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 20, 15, 0),
        )

        Transaksi.objects.create(  # status bukan "Selesai"
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pemasukan",
            category="Penjualan Barang",
            total_amount=Decimal("500.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("500.00"),
            status="Draft",
            created_at=datetime(2025, 4, 21, 10, 0),
        )
        Transaksi.objects.create(  # is_deleted=True
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pengeluaran",
            category="Pembelian Stok",
            total_amount=Decimal("300.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("300.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 22, 11, 0),
            is_deleted=True,
        )
        # beda bulan
        t_may = Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pemasukan",
            category="Penjualan Barang",
            total_amount=Decimal("400.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("400.00"),
            status="Selesai",
        )
        Transaksi.objects.filter(pk=t_may.pk).update(
            created_at=datetime(2025, 5, 1, 12, 0)
        )

    def test_income_statement_json(self):
        request = self.factory.get(
            "/api/laporan/income-statement", {"start_date": "2025-04-01", "end_date": "2025-04-30"}
        )
        request.user = self.user

        resp = income_statement(request,
                                 start_date=date(2025, 4, 1),
                                 end_date=date(2025, 4, 30))

        self.assertEqual(resp.toko_id, self.toko.id)
        self.assertEqual(resp.start_date, date(2025, 4, 1))
        self.assertEqual(resp.end_date,   date(2025, 4, 30))
        self.assertEqual(resp.currency, "IDR")

        # Cek detail income
        expected_income = {
            "Penjualan Barang": Decimal("1000.00"),
            "Pendapatan Pinjaman": Decimal("200.00"),
            "Pendapatan Lain-Lain": Decimal("300.00"),
        }
        for line in resp.income:
            self.assertIn(line.name, expected_income)
            self.assertEqual(line.total, expected_income[line.name])

        # Cek detail expenses
        expected_expenses = {
            "Pembelian Stok": Decimal("1200.00"),
            "Pembelian Bahan Baku": Decimal("100.00"),
            "Biaya Operasional": Decimal("100.00"),
        }
        for line in resp.expenses:
            self.assertIn(line.name, expected_expenses)
            self.assertEqual(line.total, expected_expenses[line.name])

        self.assertEqual(resp.net_profit, Decimal("100.00"))

    def test_income_statement_csv(self):
        request = self.factory.get(
            "/api/laporan/income-statement/download", {"start_date": "2025-04-01", "end_date": "2025-04-30"}
        )
        request.user = self.user

        resp = download_income_statement(request,
                                        start_date=date(2025, 4, 1),
                                        end_date=date(2025, 4, 30))
        self.assertIsInstance(resp, StreamingHttpResponse)

        content = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn(f"Toko ID,{self.toko.id}", content)
        self.assertIn("Periode,2025-04-01_to_2025-04-30", content)

        # Cek baris income 
        self.assertIn("Penjualan Barang,1.000,00", content)
        self.assertIn("Pendapatan Pinjaman,200,00", content)
        self.assertIn("Pendapatan Lain-Lain,300,00", content)

        # Cek baris expense
        self.assertIn("Pembelian Stok,1.200,00", content)
        self.assertIn("Pembelian Bahan Baku,100,00", content)
        self.assertIn("Biaya Operasional,100,00", content)

        self.assertIn("Laba (Rugi) Bersih,100,00", content)

    def test_negative_net_profit_csv(self):
        Transaksi.objects.all().delete()
        Transaksi.objects.create(
            toko=self.toko,
            created_by=self.user,
            transaction_type="Pengeluaran",
            category="Pembelian Stok",
            total_amount=Decimal("500.00"),
            total_modal=Decimal("0.00"),
            amount=Decimal("500.00"),
            status="Selesai",
            created_at=datetime(2025, 4, 10, 10, 0),
        )

        request = self.factory.get(
            "/api/laporan/income-statement/download",
            {"start_date": "2025-04-01", "end_date": "2025-04-30"}
        )
        request.user = self.user

        resp = download_income_statement(request,
                                        start_date=date(2025, 4, 1),
                                        end_date=date(2025, 4, 30))
        content = b"".join(resp.streaming_content).decode("utf-8")

        self.assertIn("Laba (Rugi) Bersih,(500,00)", content)
    
class UtilsAndInternalTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="dummy",
            email="dummy@example.com",
            password="pwd"
        )

    def test_format_parentheses_positive_and_negative(self):
        self.assertEqual(_format_parentheses(Decimal("1234.5")), "1.234,50")
        self.assertEqual(_format_parentheses(Decimal("-1234.567")), "(1.234,57)")
        self.assertEqual(_format_parentheses(Decimal("0")), "0,00")

    def test_build_csv_headers_and_filename(self):
        income = [IncomeStatementLine(name="A", total=Decimal("10"))]
        expense = [IncomeStatementLine(name="B", total=Decimal("5"))]
        resp = build_csv("2025-04", 7, income, expense, Decimal("5"))
        self.assertEqual(resp["Content-Type"], "text/csv")
        cd = resp["Content-Disposition"]
        self.assertIn('income_statement_2025-04.csv', cd)
        content = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn("Toko ID,7", content)
        self.assertIn("Laba (Rugi) Bersih,5,00", content)

class MockAuthenticatedRequest:
    """Mock request with authentication for testing"""
    def __init__(self, user_id=1, method="get_params", body=None, get_params=None):
        self.auth = user_id  # Simulating authenticated user
        self.method = method
        self._body = json.dumps(body).encode() if body else None
        self.GET = get_params or {}

User = get_user_model()

class ArusKasReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.toko = Toko.objects.create()
        self.user = User.objects.create_user(username="testuser", password="password", toko=self.toko, email="test@gmail.com")

        self.client.login(user=self.user)

        self.report = ArusKasReport.objects.create(
            toko=self.toko,
            bulan=4,
            tahun=2025,
            total_inflow=Decimal("100000.00"),
            total_outflow=Decimal("50000.00"),
            saldo=Decimal("50000.00")
        )

        self.detail1 = DetailArusKas.objects.create(
            report=self.report,
            jenis="inflow",
            nominal=Decimal("100000.00"),
            kategori="Penjualan",
            tanggal_transaksi=datetime(2025, 4, 10, 10, 0),
            keterangan="Penjualan produk"
        )

    def test_get_aruskas_report_existing(self):
        request = MockAuthenticatedRequest(user_id=self.user.id)
        response = aruskas_report(request, month="2025-04")  # langsung return object schema

        self.assertEqual(response.month, 4)
        self.assertEqual(response.year, 2025)
        self.assertEqual(response.total_inflow, Decimal("100000.00"))
        self.assertEqual(len(response.transactions), 1)
        self.assertEqual(response.transactions[0].kategori, "Penjualan")

    def test_get_aruskas_report_not_found(self):
        request = MockAuthenticatedRequest(user_id=self.user.id)
        response = aruskas_report(request, month="2024-01")

        self.assertEqual(response.id, 0)    
        self.assertEqual(response.total_inflow, 0)
        self.assertEqual(len(response.transactions), 0)

    def test_get_available_months(self):
        request = MockAuthenticatedRequest(user_id=self.user.id)

        response = available_months(request)

        self.assertIsInstance(response, list)
        self.assertIn("2025-04", response)


    def test_str_hutang_piutang_report(self):
        report = HutangPiutangReport.objects.create(
            toko=self.toko,
            total_hutang=10000,
            total_piutang=5000,
            jumlah_transaksi_hutang=2,
            jumlah_transaksi_piutang=1,
            tanggal=timezone.now().date()
        )
        self.assertIn("Laporan Hutang Piutang", str(report))

    def test_str_detail_hutang_piutang(self):
        report = HutangPiutangReport.objects.create(toko=self.toko)
        detail = DetailHutangPiutang.objects.create(
            report=report,
            transaksi_id="T123",
            jenis="hutang",
            jumlah=20000,
            tanggal_transaksi=timezone.now(),
            keterangan="Test"
        )
        self.assertIn("Hutang", str(detail))

    def test_str_aruskas_report(self):
        report = ArusKasReport.objects.create(
            toko=self.toko,
            bulan=5,
            tahun=2025,
            total_inflow=100000,
            total_outflow=40000,
            saldo=60000
        )
        self.assertIn("Laporan Arus Kas", str(report))

    def test_str_detail_aruskas(self):
        report = ArusKasReport.objects.create(toko=self.toko)
        detail = DetailArusKas.objects.create(
            report=report,
            jenis="inflow",
            nominal=50000,
            kategori="Penjualan",
            tanggal_transaksi=timezone.now()
        )
        self.assertIn("Inflow", str(detail))  # karena jenis="inflow"
