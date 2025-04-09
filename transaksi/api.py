from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponseBadRequest
from transaksi.models import Transaksi, TransaksiItem
from produk.models import Produk
from transaksi.schemas import (
    CreateTransaksiRequest,
    TransaksiResponse,
    PaginatedTransaksiResponse,
)
from authentication.models import User
from produk.api import AuthBearer
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Sum

router = Router(auth=AuthBearer())


@router.post("", response={201: TransaksiResponse, 422: dict})
@transaction.atomic
def create_transaksi(request, payload: CreateTransaksiRequest):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 422, {"message": "User doesn't have a toko"}

    try:
        # Create main transaction
        transaksi = Transaksi.objects.create(
            toko=user.toko,  # Associate with toko instead of user
            created_by=user,  # Keep track of which user created the transaction
            transaction_type=payload.transaction_type,
            category=payload.category,
            total_amount=payload.total_amount,
            total_modal=payload.total_modal,
            amount=payload.amount,
            status=payload.status,
        )

        # Create transaction items and update stock if this is a product sale
        if payload.category == "Penjualan Barang" and payload.items:
            for item_data in payload.items:
                product = get_object_or_404(
                    Produk, id=item_data.product_id, toko=user.toko
                )

                # Create transaction item
                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=item_data.quantity,
                    harga_jual_saat_transaksi=item_data.harga_jual_saat_transaksi,
                    harga_modal_saat_transaksi=item_data.harga_modal_saat_transaksi,
                )

                # Update product stock
                if product.stok < item_data.quantity:
                    raise ValueError(f"Stok tidak cukup untuk produk {product.nama}")
                product.stok -= item_data.quantity
                product.save()

        # Create transaction items and update stock if this is a stock purchase
        elif payload.category == "Pembelian Stok" and payload.items:
            for item_data in payload.items:
                product = get_object_or_404(
                    Produk, id=item_data.product_id, toko=user.toko
                )

                # Create transaction item
                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=item_data.quantity,
                    harga_jual_saat_transaksi=item_data.harga_jual_saat_transaksi,
                    harga_modal_saat_transaksi=item_data.harga_modal_saat_transaksi,
                )

                # Increase product stock
                product.stok += item_data.quantity
                product.save()

        # Reload transaction with all items for response
        transaksi = Transaksi.objects.get(id=transaksi.id)
        return 201, TransaksiResponse.from_orm(transaksi)

    except ValueError as e:
        return 422, {"message": str(e)}
    except Exception as e:
        return 422, {"message": f"Error during transaction: {str(e)}"}


@router.get("", response={200: PaginatedTransaksiResponse, 404: dict})
def get_transaksi_list(
    request,
    page: int = 1,
    q: str = "",
    category: str = "",
    transaction_type: str = "",
    status: str = "",
    show_deleted: bool = False,
):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}
    
    # Filter transactions by toko instead of user
    queryset = Transaksi.objects.filter(toko=user.toko, is_deleted=show_deleted)
    queryset = queryset.order_by("-created_at")

    if q:
        # Search by transaction ID or category
        queryset = queryset.filter(id__icontains=q) | queryset.filter(
            category__icontains=q
        )

    if category:
        queryset = queryset.filter(category=category)

    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)

    if status:
        queryset = queryset.filter(status=status)

    try:
        per_page = int(request.GET.get("per_page", 10))
    except ValueError:
        per_page = 10

    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page

    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}

    offset = (page - 1) * per_page
    page_items = queryset[offset : offset + per_page]

    return 200, {
        "items": [TransaksiResponse.from_orm(t) for t in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/{id}", response={200: TransaksiResponse, 404: dict})
def get_transaksi_detail(request, id: str):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}
    
    try:
        # Get transaction by ID and check if it belongs to the user's toko
        transaksi = get_object_or_404(Transaksi, id=id, toko=user.toko)
        return 200, TransaksiResponse.from_orm(transaksi)
    except Exception:
        return 404, {"message": "Transaksi tidak ditemukan"}


@router.delete("/{id}", response={200: dict, 404: dict, 422: dict})
@transaction.atomic
def delete_transaksi(request, id: str):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}
    
    try:
        # Get transaction by ID and check if it belongs to the user's toko
        transaksi = get_object_or_404(Transaksi, id=id, toko=user.toko)

        # Restore product stock if transaction is a product sale
        if transaksi.category == "Penjualan Barang":
            for item in transaksi.items.all():
                product = item.product
                product.stok += item.quantity
                product.save()

        # Reduce product stock if transaction is a stock purchase
        elif transaksi.category == "Pembelian Stok":
            for item in transaksi.items.all():
                product = item.product
                if product.stok < item.quantity:
                    raise ValueError(
                        f"Tidak dapat menghapus transaksi. Stok produk {product.nama} tidak mencukupi."
                    )
                product.stok -= item.quantity
                product.save()

        # Instead of transaksi.delete(), do a soft delete
        transaksi.is_deleted = True
        transaksi.save()

        return 200, {"message": "Transaksi berhasil dihapus"}
    except ValueError as e:
        return 422, {"message": str(e)}
    except Exception as e:
        return 404, {"message": f"Error: {str(e)}"}


@router.get("/summary/monthly", response={200: dict, 404: dict})
def get_monthly_summary(request):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}

    # Get current month period
    current_date = datetime.now()
    year, month = current_date.year, current_date.month

    # Define the current month period
    start_date = datetime(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    end_date = datetime(next_year, next_month, 1)

    # Define the previous month period
    prev_start_date = start_date - relativedelta(months=1)
    prev_end_date = start_date

    # Filter transactions for current month by toko instead of user
    current_month_transactions = Transaksi.objects.filter(
        toko=user.toko,
        created_at__gte=start_date,
        created_at__lt=end_date,
        is_deleted=False,
    )

    # Filter transactions for previous month by toko instead of user
    prev_month_transactions = Transaksi.objects.filter(
        toko=user.toko,
        created_at__gte=prev_start_date,
        created_at__lt=prev_end_date,
        is_deleted=False,
    )

    # Calculate income (pemasukan) for current and previous months
    current_income = (
        current_month_transactions.filter(transaction_type="pemasukan").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    prev_income = (
        prev_month_transactions.filter(transaction_type="pemasukan").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    # Calculate expenses (pengeluaran) for current and previous months
    current_expenses = (
        current_month_transactions.filter(transaction_type="pengeluaran").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    prev_expenses = (
        prev_month_transactions.filter(transaction_type="pengeluaran").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    # Calculate percentage changes
    income_change = 0
    if prev_income > 0:
        income_change = round(((current_income - prev_income) / prev_income) * 100, 2)

    expense_change = 0
    if prev_expenses > 0:
        expense_change = round(
            ((current_expenses - prev_expenses) / prev_expenses) * 100, 2
        )

    # Calculate net amount and determine status
    net_amount = current_income - current_expenses
    status = "untung" if net_amount >= 0 else "rugi"

    return 200, {
        "pemasukan": {
            "amount": current_income,
            "change": income_change,
        },
        "pengeluaran": {
            "amount": current_expenses,
            "change": expense_change,
        },
        "status": status,
        "amount": abs(net_amount),
    }

@router.patch("/{id}/toggle-payment-status", response={200: dict, 404: dict, 422: dict})
def toggle_payment_status(request, id: str):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": "User doesn't have a toko"}
    
    try:
        # Get transaction by ID, ensure it belongs to user's toko and is not deleted
        transaksi = get_object_or_404(Transaksi, id=id, toko=user.toko, is_deleted=False)
        
        # Check if current status is "Belum Lunas"
        if transaksi.status != "Belum Lunas":
            return 422, {"message": "Only transactions with 'Belum Lunas' status can be toggled"}
        
        # Update status to "Lunas"
        transaksi.status = "Lunas"
        transaksi.save()
        
        return 200, {
            "message": "Status transaksi berhasil diubah menjadi Lunas",
            "transaction_id": str(transaksi.id),
            "status": transaksi.status
        }
    except Exception as e:
        return 404, {"message": f"Error: {str(e)}"}