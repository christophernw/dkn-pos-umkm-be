from datetime import date
from calendar import monthrange
from decimal import Decimal
from typing import List

from django.db.models import Sum
from ninja import Router
from ninja.security import django_auth

from transaksi.models import Transaksi
from authentication.models import Toko
from .schemas import IncomeStatementResponse, IncomeStatementLine
from .utils import INCOME_CATEGORIES, EXPENSE_CATEGORIES, build_csv

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
        created_at__year=first.year,
        created_at__month=first.month,
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

    net_profit = sum((l.total for l in income_lines), Decimal("0")) \
                 - sum((l.total for l in expense_lines), Decimal("0"))
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

    income, expenses, net = _aggregate(toko, first, last)
    return IncomeStatementResponse(
        toko_id=toko.id,
        period=month,
        income=income,
        expenses=expenses,
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

    income, expenses, net = _aggregate(toko, first, last)
    return build_csv(month, toko.id, income, expenses, net)
