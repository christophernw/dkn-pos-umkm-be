from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.security import django_auth
from ninja.errors import HttpError
from ninja.security import HttpBearer
import jwt
from backend import settings

from laporan.models import ArusKasReport, DetailArusKas
from transaksi.models import Transaksi
from authentication.models import Toko, User
from .schemas import (
    ArusKasReportWithDetailsSchema,
    DateRangeRequest,
    IncomeStatementResponse,
    IncomeStatementLine,
    ArusKasDetailSchema,
)
from .utils import INCOME_CATEGORIES, EXPENSE_CATEGORIES, build_csv

router = Router(tags=["Income Statement"])


def _aggregate(toko: Toko, start: date, end: date):
    qs = Transaksi.objects.filter(
        toko=toko,
        is_deleted=False,
        status="Lunas",
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    def sum_by(cats: dict) -> List[IncomeStatementLine]:
        out = []
        for label in cats.values():
            amt = qs.filter(category=label).aggregate(total=Sum("total_amount"))[
                "total"
            ] or Decimal("0")
            out.append(IncomeStatementLine(name=label, total=amt))
        return out

    inc = sum_by(INCOME_CATEGORIES)
    exp = sum_by(EXPENSE_CATEGORIES)
    net = sum((l.total for l in inc), Decimal("0")) - sum(
        (l.total for l in exp), Decimal("0")
    )
    return inc, exp, net


@router.get("/income-statement", response=IncomeStatementResponse, auth=django_auth)
def income_statement(request, start_date: date, end_date: date):
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    if (end_date - start_date).days < 28:
        raise HttpError(400, "Date range must be at least 28 days")

    toko = request.user.toko
    inc, exp, net = _aggregate(toko, start_date, end_date)
    return IncomeStatementResponse(
        toko_id=toko.id,
        start_date=start_date,
        end_date=end_date,
        income=inc,
        expenses=exp,
        net_profit=net,
    )


@router.get("/income-statement/download", auth=django_auth)
def download_income_statement(request, start_date: date, end_date: date):
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    if (end_date - start_date).days < 28:
        raise HttpError(400, "Date range must be at least 28 days")

    toko = request.user.toko
    inc, exp, net = _aggregate(toko, start_date, end_date)
    period = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
    return build_csv(period, toko.id, inc, exp, net)


router = Router(tags=["Income Statement"])


def _month_bounds(year: int, month: int):
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def _aggregate(toko: Toko, first: date, last: date):
    base_qs = Transaksi.objects.filter(
        toko=toko,
        is_deleted=False,
        status="Lunas",
        created_at__date__range=(first, last),
    )

    def sum_by(categories: dict) -> List[IncomeStatementLine]:
        lines = []
        for label in categories.values():
            total = base_qs.filter(category=label).aggregate(total=Sum("total_amount"))[
                "total"
            ] or Decimal("0")
            lines.append(IncomeStatementLine(name=label, total=total))
        return lines

    income_lines = sum_by(INCOME_CATEGORIES)
    expense_lines = sum_by(EXPENSE_CATEGORIES)

    net_profit = sum((line.total for line in income_lines), Decimal("0")) - sum(
        (line.total for line in expense_lines), Decimal("0")
    )

    return income_lines, expense_lines, net_profit


@router.get("/income-statement", response=IncomeStatementResponse, auth=django_auth)
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
        net_profit=net,
    )


@router.get("/income-statement/download", auth=django_auth)
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
def aruskas_report(
    request, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
):
    """
    Get a cash flow report with optional date filters for transactions.
    """
    if hasattr(request, "auth") and request.auth:
        user_id = request.auth
        user = User.objects.get(id=user_id)
        toko = user.toko
    else:
        toko = request.user.toko

    report = ArusKasReport.objects.filter(toko=toko).first()

    if not report:
        return ArusKasReportWithDetailsSchema(
            id=0,
            month=0,
            year=0,
            total_inflow=Decimal("0"),
            total_outflow=Decimal("0"),
            balance=Decimal("0"),
            transactions=[],
        )

    transactions = DetailArusKas.objects.filter(report=report)

    if start_date:
        transactions = transactions.filter(tanggal_transaksi__gte=start_date)
    if end_date:
        transactions = transactions.filter(tanggal_transaksi__lte=end_date)

    return ArusKasReportWithDetailsSchema.from_report(report, transactions)


# laporan/api.py
@router.get(
    "/bpr/shop/{shop_id}/aruskas",
    response={200: ArusKasReportWithDetailsSchema, 403: dict, 404: dict},
    auth=AuthBearer(),
)
def get_shop_aruskas_for_bpr(request, shop_id: int):
    """Get cash flow report for a specific shop for BPR users."""
    user_id = request.auth

    try:
        user = User.objects.get(id=user_id)

        # Check ONLY the email, not the role
        if user.email != settings.BPR_EMAIL:
            return 403, {"error": "Only BPR users can access this endpoint"}

        # Get the shop
        shop = get_object_or_404(Toko, id=shop_id)

        # Get report for the shop
        report = ArusKasReport.objects.filter(toko=shop).first()

        if not report:
            return ArusKasReportWithDetailsSchema(
                id=0,
                month=0,
                year=0,
                total_inflow=Decimal("0"),
                total_outflow=Decimal("0"),
                balance=Decimal("0"),
                transactions=[],
            )

        transactions = DetailArusKas.objects.filter(report=report)

        return ArusKasReportWithDetailsSchema.from_report(report, transactions)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 403, {"error": "Access denied"}


# @router.get("/aruskas-available-months", response=List[str])
# def available_months(request):
#     user_id = request.auth
#     user = User.objects.get(id=user_id)
#     toko = user.toko

#     reports = ArusKasReport.objects.filter(toko=toko).order_by('-tahun', '-bulan')

#     months = [
#         f"{report.tahun}-{report.bulan:02d}"
#         for report in reports
#     ]

#     return months
