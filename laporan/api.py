from datetime import date
from decimal import Decimal
from typing import List

from django.db.models import Sum
from ninja import Router
from ninja.security import django_auth
from ninja.errors import HttpError

from transaksi.models import Transaksi
from authentication.models import Toko
from .schemas import IncomeStatementResponse, IncomeStatementLine
from .utils import INCOME_CATEGORIES, EXPENSE_CATEGORIES, build_csv

router = Router(tags=["Income Statement"])

def _aggregate(toko: Toko, start: date, end: date):
    qs = Transaksi.objects.filter(
        toko=toko,
        is_deleted=False,
        status="Selesai",
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    def sum_by(cats: dict) -> List[IncomeStatementLine]:
        out = []
        for label in cats.values():
            amt = qs.filter(category=label).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
            out.append(IncomeStatementLine(name=label, total=amt))
        return out

    inc = sum_by(INCOME_CATEGORIES)
    exp = sum_by(EXPENSE_CATEGORIES)
    net = sum((l.total for l in inc), Decimal("0")) - sum((l.total for l in exp), Decimal("0"))
    return inc, exp, net

@router.get("/income-statement", response=IncomeStatementResponse, auth=django_auth)
def income_statement(request,
                     start_date: date,
                     end_date: date):
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
def download_income_statement(request,
                             start_date: date,
                             end_date: date):
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    if (end_date - start_date).days < 28:
        raise HttpError(400, "Date range must be at least 28 days")

    toko = request.user.toko
    inc, exp, net = _aggregate(toko, start_date, end_date)
    period = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
    return build_csv(period, toko.id, inc, exp, net)
