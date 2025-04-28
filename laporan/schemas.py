from ninja import Schema
from typing import List, Optional
from datetime import datetime, date
from pydantic import Field
from decimal import Decimal

class TransaksiHutangPiutangDetail(Schema):
    id: str
    transaction_type: str
    category: str
    total_amount: float
    created_at: datetime
    
    @classmethod
    def from_transaksi(cls, transaksi):
        return cls(
            id=transaksi.id,
            transaction_type=transaksi.transaction_type,
            category=transaksi.category,
            total_amount=float(transaksi.total_amount),
            created_at=transaksi.created_at
        )

class HutangPiutangSummaryResponse(Schema):
    total_hutang: float
    total_piutang: float
    jumlah_transaksi_hutang: int
    jumlah_transaksi_piutang: int

class HutangPiutangDetailResponse(Schema):
    hutang: List[TransaksiHutangPiutangDetail]
    piutang: List[TransaksiHutangPiutangDetail]

class HutangPiutangReportListItem(Schema):
    id: int
    tanggal: date
    total_hutang: float
    total_piutang: float
    jumlah_transaksi_hutang: int
    jumlah_transaksi_piutang: int
    
    @classmethod
    def from_orm(cls, report):
        return cls(
            id=report.id,
            tanggal=report.tanggal,
            total_hutang=float(report.total_hutang),
            total_piutang=float(report.total_piutang),
            jumlah_transaksi_hutang=report.jumlah_transaksi_hutang,
            jumlah_transaksi_piutang=report.jumlah_transaksi_piutang
        )

class PaginatedHutangPiutangReportResponse(Schema):
    items: List[HutangPiutangReportListItem]
    total: int
    page: int
    per_page: int
    total_pages: int

class DateRangeRequest(Schema):
    start_date: date = Field(None, description="Start date for filtering (YYYY-MM-DD)")
    end_date: date = Field(None, description="End date for filtering (YYYY-MM-DD)")

class IncomeStatementLine(Schema):
    name: str
    total: Decimal 

class IncomeStatementResponse(Schema):
    toko_id: int
    start_date: date
    end_date: date
    currency: str = "IDR"
    income: List[IncomeStatementLine]
    expenses: List[IncomeStatementLine]
    net_profit: Decimal 
