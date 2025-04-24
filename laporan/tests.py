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
    
class TransaksiHutangPiutangDetailSchemaTest(TestCase):
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