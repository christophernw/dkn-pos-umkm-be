import csv
from io import StringIO
from decimal import Decimal, ROUND_HALF_UP
from django.http import StreamingHttpResponse
from .schemas import IncomeStatementLine

INCOME_CATEGORIES = {
    "Penjualan Barang": "Penjualan Barang",
    "Pendapatan Pinjaman": "Pendapatan Pinjaman",
    "Pendapatan Lain-Lain": "Pendapatan Lain-Lain",
}

EXPENSE_CATEGORIES = {
    "Pembelian Stok": "Pembelian Stok",
    "Pembelian Bahan Baku": "Pembelian Bahan Baku",
    "Biaya Operasional": "Biaya Operasional",
}

def _format_parentheses(value: Decimal) -> str:
    """IDR format with comma decimal and dot thousand, negative => (xxx)."""
    q = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    is_negative = q < 0
    num = f"{abs(q):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"({num})" if is_negative else num

def build_csv(period: str, toko_id: int, income_lines, expense_lines, net_profit):
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(["Toko ID", toko_id])
    writer.writerow(["Periode", period])
    writer.writerow([])
    writer.writerow(["Pendapatan"])
    for line in income_lines:
        writer.writerow([line.name, _format_parentheses(line.total)])
    writer.writerow([])
    writer.writerow(["Beban"])
    for line in expense_lines:
        writer.writerow([line.name, _format_parentheses(line.total)])
    writer.writerow([])
    writer.writerow(["Laba (Rugi) Bersih", _format_parentheses(net_profit)])
    raw = f.getvalue().replace('"', '')
    f2 = StringIO(raw)
    return StreamingHttpResponse(
        f2, content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="income_statement_{period}.csv"'}
    )
