from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from datetime import date, datetime
from decimal import Decimal
from django.http import StreamingHttpResponse

from authentication.models import Toko, User 
from laporan.schemas import IncomeStatementLine
from transaksi.models import Transaksi
from laporan.api import income_statement, download_income_statement, _month_bounds, _aggregate
from laporan.utils import _format_parentheses, build_csv
from io import StringIO


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
            "/api/laporan/income-statement", {"month": "2025-04"}
        )
        request.user = self.user

        resp = income_statement(request, month="2025-04")

        self.assertEqual(resp.toko_id, self.toko.id)
        self.assertEqual(resp.period, "2025-04")
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
            "/api/laporan/income-statement/download", {"month": "2025-04"}
        )
        request.user = self.user

        resp = download_income_statement(request, month="2025-04")
        self.assertIsInstance(resp, StreamingHttpResponse)

        content = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn(f"Toko ID,{self.toko.id}", content)
        self.assertIn("Periode,2025-04", content)

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
            "/api/laporan/income-statement/download", {"month": "2025-04"}
        )
        request.user = self.user

        resp = download_income_statement(request, month="2025-04")
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

    def test_month_bounds(self):
        first, last = _month_bounds(2025, 4)
        self.assertEqual(first, date(2025, 4, 1))
        self.assertEqual(last, date(2025, 4, 30))
        f2, l2 = _month_bounds(2024, 2)
        self.assertEqual(l2.day, 29)

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

    def test_aggregate_empty(self):
        toko2 = Toko.objects.create()
        first, last = _month_bounds(2025, 4)
        inc, exp, net = _aggregate(toko2, first, last)
        for line in inc + exp:
            self.assertEqual(line.total, Decimal("0"))
        self.assertEqual(net, Decimal("0"))

