from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock

from authentication.models import Toko
from .models import HutangPiutangReport, DetailHutangPiutang
from .schemas import (
    TransaksiHutangPiutangDetail,
    HutangPiutangSummaryResponse,
    HutangPiutangDetailResponse,
    HutangPiutangReportListItem,
    PaginatedHutangPiutangReportResponse,
    DateRangeRequest
)


class HutangPiutangReportModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.toko = Toko.objects.create(
            nama="Test Toko",
            alamat="Test Address",
            telepon="123456789"
        )
        self.test_date = date.today()
    
    def test_model_fields(self):
        """Test all model fields"""
        report = HutangPiutangReport.objects.create(
            toko=self.toko,
            total_hutang=Decimal('1000.50'),
            total_piutang=Decimal('750.25'),
            jumlah_transaksi_hutang=5,
            jumlah_transaksi_piutang=3,
            tanggal=self.test_date
        )
        
        self.assertEqual(report.toko, self.toko)
        self.assertEqual(report.total_hutang, Decimal('1000.50'))
        self.assertEqual(report.total_piutang, Decimal('750.25'))
        self.assertEqual(report.jumlah_transaksi_hutang, 5)
        self.assertEqual(report.jumlah_transaksi_piutang, 3)
        self.assertEqual(report.tanggal, self.test_date)
        self.assertTrue(hasattr(report, 'id'))
        self.assertIsNotNone(report.id)
    
    def test_default_values(self):
        """Test default values"""
        report = HutangPiutangReport.objects.create(toko=self.toko)
        
        self.assertEqual(report.total_hutang, Decimal('0'))
        self.assertEqual(report.total_piutang, Decimal('0'))
        self.assertEqual(report.jumlah_transaksi_hutang, 0)
        self.assertEqual(report.jumlah_transaksi_piutang, 0)
        self.assertEqual(report.tanggal, date.today())
    
    def test_str_method(self):
        """Test __str__ method"""
        report = HutangPiutangReport.objects.create(
            toko=self.toko,
            tanggal=self.test_date
        )
        expected_str = f"Laporan Hutang Piutang {self.toko.nama} - {self.test_date}"
        self.assertEqual(str(report), expected_str)
    
    def test_meta_options(self):
        """Test Meta class options"""
        # Test ordering
        report1 = HutangPiutangReport.objects.create(
            toko=self.toko,
            tanggal=date.today() - timedelta(days=2)
        )
        report2 = HutangPiutangReport.objects.create(
            toko=self.toko,
            tanggal=date.today() - timedelta(days=1)
        )
        
        reports = list(HutangPiutangReport.objects.all())
        self.assertEqual(reports[0], report2)  # More recent date first
        self.assertEqual(reports[1], report1)
        
        # Test unique_together constraint
        with self.assertRaises(IntegrityError):
            HutangPiutangReport.objects.create(
                toko=self.toko,
                tanggal=report1.tanggal
            )
    
    def test_foreign_key_cascade(self):
        """Test foreign key on_delete=CASCADE"""
        report = HutangPiutangReport.objects.create(toko=self.toko)
        report_id = report.id
        
        self.toko.delete()
        
        with self.assertRaises(HutangPiutangReport.DoesNotExist):
            HutangPiutangReport.objects.get(id=report_id)
    
    def test_related_name(self):
        """Test related_name"""
        report = HutangPiutangReport.objects.create(toko=self.toko)
        self.assertIn(report, self.toko.hutang_piutang_reports.all())


class DetailHutangPiutangModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.toko = Toko.objects.create(
            nama="Test Toko",
            alamat="Test Address",
            telepon="123456789"
        )
        self.report = HutangPiutangReport.objects.create(toko=self.toko)
        self.test_datetime = timezone.now()
    
    def test_model_fields(self):
        """Test all model fields"""
        detail = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime,
            keterangan="Test keterangan"
        )
        
        self.assertEqual(detail.report, self.report)
        self.assertEqual(detail.transaksi_id, "TRX001")
        self.assertEqual(detail.jenis, "hutang")
        self.assertEqual(detail.jumlah, Decimal('500.00'))
        self.assertEqual(detail.tanggal_transaksi, self.test_datetime)
        self.assertEqual(detail.keterangan, "Test keterangan")
        self.assertTrue(hasattr(detail, 'id'))
        self.assertIsNotNone(detail.id)
    
    def test_jenis_choices(self):
        """Test jenis field choices"""
        # Test hutang choice
        detail_hutang = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime
        )
        self.assertEqual(detail_hutang.jenis, "hutang")
        
        # Test piutang choice
        detail_piutang = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX002",
            jenis="piutang",
            jumlah=Decimal('300.00'),
            tanggal_transaksi=self.test_datetime
        )
        self.assertEqual(detail_piutang.jenis, "piutang")
    
    def test_optional_fields(self):
        """Test optional fields (blank=True, null=True)"""
        detail = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime
        )
        self.assertIsNone(detail.keterangan)
    
    def test_str_method(self):
        """Test __str__ method"""
        # Test with hutang
        detail_hutang = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime
        )
        expected_str = "Hutang - TRX001 - 500.00"
        self.assertEqual(str(detail_hutang), expected_str)
        
        # Test with piutang
        detail_piutang = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX002",
            jenis="piutang",
            jumlah=Decimal('300.00'),
            tanggal_transaksi=self.test_datetime
        )
        expected_str = "Piutang - TRX002 - 300.00"
        self.assertEqual(str(detail_piutang), expected_str)
    
    def test_meta_options(self):
        """Test Meta class options"""
        # Test ordering
        detail1 = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=timezone.now() - timedelta(hours=2)
        )
        detail2 = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX002",
            jenis="piutang",
            jumlah=Decimal('300.00'),
            tanggal_transaksi=timezone.now() - timedelta(hours=1)
        )
        
        details = list(DetailHutangPiutang.objects.all())
        self.assertEqual(details[0], detail2)  # More recent time first
        self.assertEqual(details[1], detail1)
    
    def test_foreign_key_cascade(self):
        """Test foreign key on_delete=CASCADE"""
        detail = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime
        )
        detail_id = detail.id
        
        self.report.delete()
        
        with self.assertRaises(DetailHutangPiutang.DoesNotExist):
            DetailHutangPiutang.objects.get(id=detail_id)
    
    def test_related_name(self):
        """Test related_name"""
        detail = DetailHutangPiutang.objects.create(
            report=self.report,
            transaksi_id="TRX001",
            jenis="hutang",
            jumlah=Decimal('500.00'),
            tanggal_transaksi=self.test_datetime
        )
        self.assertIn(detail, self.report.details.all())


class TransaksiHutangPiutangDetailSchemaTest(TestCase):
    def test_schema_fields(self):
        """Test schema fields"""
        schema = TransaksiHutangPiutangDetail(
            id="TRX001",
            transaction_type="hutang",
            category="pembelian",
            total_amount=1500.50,
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        self.assertEqual(schema.id, "TRX001")
        self.assertEqual(schema.transaction_type, "hutang")
        self.assertEqual(schema.category, "pembelian")
        self.assertEqual(schema.total_amount, 1500.50)
        self.assertEqual(schema.created_at, datetime(2024, 1, 15, 10, 30, 0))
    
    def test_from_transaksi_classmethod(self):
        """Test from_transaksi class method"""
        mock_transaksi = Mock()
        mock_transaksi.id = "TRX002"
        mock_transaksi.transaction_type = "piutang"
        mock_transaksi.category = "penjualan"
        mock_transaksi.total_amount = Decimal('2000.75')
        mock_transaksi.created_at = datetime(2024, 1, 16, 14, 45, 30)
        
        schema = TransaksiHutangPiutangDetail.from_transaksi(mock_transaksi)
        
        self.assertEqual(schema.id, "TRX002")
        self.assertEqual(schema.transaction_type, "piutang")
        self.assertEqual(schema.category, "penjualan")
        self.assertEqual(schema.total_amount, 2000.75)
        self.assertEqual(schema.created_at, datetime(2024, 1, 16, 14, 45, 30))


class HutangPiutangSummaryResponseSchemaTest(TestCase):
    def test_schema_fields(self):
        """Test schema fields"""
        schema = HutangPiutangSummaryResponse(
            total_hutang=5000.25,
            total_piutang=3500.75,
            jumlah_transaksi_hutang=10,
            jumlah_transaksi_piutang=7
        )
        
        self.assertEqual(schema.total_hutang, 5000.25)
        self.assertEqual(schema.total_piutang, 3500.75)
        self.assertEqual(schema.jumlah_transaksi_hutang, 10)
        self.assertEqual(schema.jumlah_transaksi_piutang, 7)


class HutangPiutangDetailResponseSchemaTest(TestCase):
    def test_schema_fields(self):
        """Test schema fields"""
        hutang_detail = TransaksiHutangPiutangDetail(
            id="H001",
            transaction_type="hutang",
            category="pembelian",
            total_amount=1000.0,
            created_at=datetime.now()
        )
        
        piutang_detail = TransaksiHutangPiutangDetail(
            id="P001",
            transaction_type="piutang",
            category="penjualan",
            total_amount=750.0,
            created_at=datetime.now()
        )
        
        schema = HutangPiutangDetailResponse(
            hutang=[hutang_detail],
            piutang=[piutang_detail]
        )
        
        self.assertEqual(len(schema.hutang), 1)
        self.assertEqual(len(schema.piutang), 1)
        self.assertEqual(schema.hutang[0].id, "H001")
        self.assertEqual(schema.piutang[0].id, "P001")
        self.assertIsInstance(schema.hutang, list)
        self.assertIsInstance(schema.piutang, list)


class HutangPiutangReportListItemSchemaTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.toko = Toko.objects.create(
            nama="Test Toko",
            alamat="Test Address",
            telepon="123456789"
        )
    
    def test_schema_fields(self):
        """Test schema fields"""
        schema = HutangPiutangReportListItem(
            id=1,
            tanggal=date(2024, 1, 20),
            total_hutang=3000.0,
            total_piutang=2000.0,
            jumlah_transaksi_hutang=12,
            jumlah_transaksi_piutang=8
        )
        
        self.assertEqual(schema.id, 1)
        self.assertEqual(schema.tanggal, date(2024, 1, 20))
        self.assertEqual(schema.total_hutang, 3000.0)
        self.assertEqual(schema.total_piutang, 2000.0)
        self.assertEqual(schema.jumlah_transaksi_hutang, 12)
        self.assertEqual(schema.jumlah_transaksi_piutang, 8)
    
    def test_from_orm_classmethod(self):
        """Test from_orm class method"""
        report = HutangPiutangReport.objects.create(
            toko=self.toko,
            total_hutang=Decimal('2500.50'),
            total_piutang=Decimal('1750.25'),
            jumlah_transaksi_hutang=8,
            jumlah_transaksi_piutang=5,
            tanggal=date(2024, 1, 15)
        )
        
        schema = HutangPiutangReportListItem.from_orm(report)
        
        self.assertEqual(schema.id, report.id)
        self.assertEqual(schema.tanggal, date(2024, 1, 15))
        self.assertEqual(schema.total_hutang, 2500.50)
        self.assertEqual(schema.total_piutang, 1750.25)
        self.assertEqual(schema.jumlah_transaksi_hutang, 8)
        self.assertEqual(schema.jumlah_transaksi_piutang, 5)


class PaginatedHutangPiutangReportResponseSchemaTest(TestCase):
    def test_schema_fields(self):
        """Test schema fields"""
        item1 = HutangPiutangReportListItem(
            id=1,
            tanggal=date(2024, 1, 15),
            total_hutang=1000.0,
            total_piutang=750.0,
            jumlah_transaksi_hutang=5,
            jumlah_transaksi_piutang=3
        )
        
        item2 = HutangPiutangReportListItem(
            id=2,
            tanggal=date(2024, 1, 16),
            total_hutang=1500.0,
            total_piutang=1200.0,
            jumlah_transaksi_hutang=7,
            jumlah_transaksi_piutang=6
        )
        
        schema = PaginatedHutangPiutangReportResponse(
            items=[item1, item2],
            total=25,
            page=1,
            per_page=10,
            total_pages=3
        )
        
        self.assertEqual(len(schema.items), 2)
        self.assertEqual(schema.total, 25)
        self.assertEqual(schema.page, 1)
        self.assertEqual(schema.per_page, 10)
        self.assertEqual(schema.total_pages, 3)
        self.assertIsInstance(schema.items, list)
        self.assertEqual(schema.items[0].id, 1)
        self.assertEqual(schema.items[1].id, 2)


class DateRangeRequestSchemaTest(TestCase):
    def test_schema_fields_with_values(self):
        """Test schema fields with values"""
        schema = DateRangeRequest(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        self.assertEqual(schema.start_date, date(2024, 1, 1))
        self.assertEqual(schema.end_date, date(2024, 1, 31))
    
    def test_schema_fields_with_defaults(self):
        """Test schema fields with default values (None)"""
        schema = DateRangeRequest()
        
        self.assertIsNone(schema.start_date)
        self.assertIsNone(schema.end_date)
    
    def test_schema_fields_partial(self):
        """Test schema fields with partial values"""
        schema1 = DateRangeRequest(start_date=date(2024, 1, 1))
        self.assertEqual(schema1.start_date, date(2024, 1, 1))
        self.assertIsNone(schema1.end_date)
        
        schema2 = DateRangeRequest(end_date=date(2024, 1, 31))
        self.assertIsNone(schema2.start_date)
        self.assertEqual(schema2.end_date, date(2024, 1, 31))