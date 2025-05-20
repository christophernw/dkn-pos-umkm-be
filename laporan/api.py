from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from django.db.models import Sum
from ninja import Router
from ninja.security import django_auth
from ninja.errors import HttpError
from ninja.security import HttpBearer
import jwt
from backend import settings
from laporan.models import ArusKasReport, DetailArusKas
from transaksi.models import Transaksi
from authentication.models import Toko, User
from .schemas import ArusKasReportWithDetailsSchema, DateRangeRequest, IncomeStatementResponse, IncomeStatementLine, ArusKasDetailSchema
from .utils import INCOME_CATEGORIES, EXPENSE_CATEGORIES, build_csv

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if user_id:
                return user_id
        except jwt.PyJWTError:
            return None
        return None
    
router = Router(auth=AuthBearer())

def _month_bounds(year: int, month: int):
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last

@router.get("/aruskas-report", response=ArusKasReportWithDetailsSchema)
def aruskas_report(request, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Get a cash flow report with optional date filters for transactions.
    """
    if hasattr(request, 'auth') and request.auth:
        user_id = request.auth
        user = User.objects.get(id=user_id)
        toko = user.toko
    else:
        toko = request.user.toko

    report = ArusKasReport.objects.filter(
        toko=toko,
        bulan=start_date.month if start_date else None,
        tahun=start_date.year if start_date else None
    ).first()

    if not report:
        return ArusKasReportWithDetailsSchema(
            id=0,
            month=0,
            year=0,
            total_inflow=Decimal("0"),
            total_outflow=Decimal("0"),
            balance=Decimal("0"),
            transactions=[]
        )

    transactions = DetailArusKas.objects.filter(report=report)

    if start_date:
        transactions = transactions.filter(tanggal_transaksi__gte=start_date)
    if end_date:
        transactions = transactions.filter(tanggal_transaksi__lte=end_date)

    return ArusKasReportWithDetailsSchema.from_report(report, transactions)

@router.get("/aruskas-available-months", response=List[str])
def available_months(request):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    toko = user.toko

    reports = ArusKasReport.objects.filter(toko=toko).order_by('-tahun', '-bulan')

    months = [
        f"{report.tahun}-{report.bulan:02d}"
        for report in reports
    ]

    return months