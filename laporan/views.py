from datetime import date
from calendar import monthrange
from decimal import Decimal
from typing import List

from django.shortcuts import render
from django.db.models import Sum, Q

from ninja import Router
from ninja.security import django_auth, HttpBearer
import jwt

from backend import settings
from transaksi.models import Transaksi
from authentication.models import User, Toko
from .models import ArusKasReport, DetailArusKas
from .schemas import IncomeStatementResponse, IncomeStatementLine, ArusKasReportWithDetailsSchema
from .utils import (INCOME_CATEGORIES, EXPENSE_CATEGORIES, build_csv)


router = Router(tags=["Income Statement"])
def _month_bounds(year: int, month: int):
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last

def _aggregate(toko: Toko, first: date, last: date):
    base_qs = Transaksi.objects.filter(
        toko=toko,
        is_deleted=False,
        status="Selesai",
        created_at__date__range=(first, last)
    )

    def sum_by(categories: dict) -> List[IncomeStatementLine]:
        lines = []
        for label in categories.values():
            total = base_qs.filter(category=label).aggregate(
                total=Sum("total_amount")
            )["total"] or Decimal("0")
            lines.append(IncomeStatementLine(name=label, total=total))
        return lines

    income_lines = sum_by(INCOME_CATEGORIES)
    expense_lines = sum_by(EXPENSE_CATEGORIES)

    net_profit = sum(
        (line.total for line in income_lines), Decimal("0")
    ) - sum((line.total for line in expense_lines), Decimal("0"))

    return income_lines, expense_lines, net_profit

@router.get(
    "/income-statement",
    response=IncomeStatementResponse,
    auth=django_auth
)
def income_statement(request, month: str):
    year, mm = map(int, month.split("-"))
    first, last = _month_bounds(year, mm)

    toko = request.user.toko  

    income_lines, expense_lines, net = _aggregate(toko, first, last)

    return IncomeStatementResponse(
        toko_id=toko.id,
        period=month,
        income=income_lines,
        expenses=expense_lines,
        net_profit=net
    )

@router.get(
    "/income-statement/download",
    auth=django_auth
)
def download_income_statement(request, month: str):
    year, mm = map(int, month.split("-"))
    first, last = _month_bounds(year, mm)
    toko = request.user.toko

    income_lines, expense_lines, net = _aggregate(toko, first, last)
    return build_csv(month, toko.id, income_lines, expense_lines, net)

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
def aruskas_report(request, month: str):
    year, mm = map(int, month.split("-"))

    user_id = request.auth
    user = User.objects.get(id=user_id)
    toko = user.toko

    report = ArusKasReport.objects.filter(
        toko=toko,
        bulan=mm,
        tahun=year
    ).first()

    if not report:
        return ArusKasReportWithDetailsSchema(
            id=0,
            month=mm,
            year=year,
            total_inflow=Decimal("0"),
            total_outflow=Decimal("0"),
            balance=Decimal("0"),
            transactions=[]
        )

    transactions = DetailArusKas.objects.filter(report=report)
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

