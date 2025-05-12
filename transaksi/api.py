from ninja import Router, Query
from typing import List, Optional, Dict, Any, Tuple, Union
from django.db.models import Q, QuerySet
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from .models import Pemasukan, Pengeluaran, Produk, Transaksi
from .schemas import (
    PemasukanCreate,
    PemasukanRead,
    PengeluaranCreate,
    PengeluaranRead,
    TransaksiUpdate,
    PaginatedPemasukanResponseSchema,
)


router = Router()


# Helper functions
def validate_products(product_ids: List[int]) -> Tuple[bool, List[Produk], str]:
    """Validate that all products exist."""
    products = list(Produk.objects.filter(id__in=product_ids))
    return True, products, ""


def create_transaction_base(
    status: str,
    catatan: Optional[str],
    nama_pelanggan: Optional[str],
    nomor_telepon: Optional[str],
    foto: Optional[str],
    product_ids: List[int]
) -> Tuple[bool, Union[Transaksi, str]]:
    """Create a base transaction with common fields."""

    _, products, _ = validate_products(product_ids)
        
    transaksi = Transaksi.objects.create(
        status=status,
        catatan=catatan,
        namaPelanggan=nama_pelanggan,
        nomorTeleponPelanggan=nomor_telepon,
        foto=foto,
    )
    
    transaksi.daftarProduk.set(products)
    return True, transaksi


def apply_filters(
    queryset: QuerySet,
) -> QuerySet:
    """Apply common filters to a queryset."""
    # Apply search filter
    # if q:
    #     queryset = queryset.filter(
    #         Q(transaksi__catatan__icontains=q)
    #         | Q(kategori__icontains=q)
    #         | Q(transaksi__namaPelanggan__icontains=q)
    #     )
        
    return queryset


def paginate_queryset(
    queryset: QuerySet,
    page: int,
    request: HttpRequest,
    default_per_page: int = 10
) -> Tuple[int, Dict[str, Any]]:
    """Paginate a queryset and return pagination metadata."""
    
    per_page = int(request.GET.get("per_page", default_per_page))

    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1


    offset = (page - 1) * per_page
    page_items = queryset[offset : offset + per_page]
    
    return 200, {
        "items": page_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


# API Endpoints for creating transactions
@router.post("/pemasukan/create", response={200: PemasukanRead, 422: dict})
def create_pemasukan(request, payload: PemasukanCreate):
    """Create a new income transaction with associated products."""

    with transaction.atomic():
        _, result = create_transaction_base(
            payload.status,
            payload.catatan,
            payload.namaPelanggan,
            payload.nomorTeleponPelanggan,
            payload.foto,
            payload.daftarProduk
        )
        

            
        transaksi = result
        
        # Create pemasukan record
        pemasukan = Pemasukan.objects.create(
            transaksi=transaksi,
            kategori=payload.kategori,
            totalPemasukan=payload.totalPemasukan,
            hargaModal=payload.hargaModal,
        )
        
        return 200, PemasukanRead.from_orm(pemasukan)
        



@router.post("/pengeluaran/create", response={200: PengeluaranRead, 422: dict})
def create_pengeluaran(request, payload: PengeluaranCreate):
    """Create a new expense transaction with associated products."""

    with transaction.atomic():
        _, result = create_transaction_base(
            payload.status,
            payload.catatan,
            payload.namaPelanggan,
            payload.nomorTeleponPelanggan,
            payload.foto,
            payload.daftarProduk
        )
        
            
        transaksi = result
        
        # Create pengeluaran record
        pengeluaran = Pengeluaran.objects.create(
            transaksi=transaksi,
            kategori=payload.kategori,
            totalPengeluaran=payload.totalPengeluaran,
        )
        
        return 200, PengeluaranRead.from_orm(pengeluaran)
        


# API Endpoints for retrieving transaction lists
@router.get("/pemasukan/daftar", response={200: List[PemasukanRead]})
def read_pemasukan(request):
    """Retrieve all income transactions."""
    pemasukan_list = Pemasukan.objects.filter(transaksi__isDeleted=False)
    return 200, [PemasukanRead.from_orm(p) for p in pemasukan_list]


@router.get("/pengeluaran/daftar", response={200: List[PengeluaranRead]})
def read_pengeluaran(request):
    """Retrieve all expense transactions."""
    pengeluaran_list = Pengeluaran.objects.filter(transaksi__isDeleted=False)
    return 200, [PengeluaranRead.from_orm(p) for p in pengeluaran_list]


# API Endpoints for retrieving single transactions
@router.get("/pemasukan/{pemasukan_id}", response={200: PemasukanRead, 404: dict})
def read_pemasukan_by_id(request, pemasukan_id: int):
    """Retrieve a specific income transaction by ID."""
    try:
        pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)
        return 200, PemasukanRead.from_orm(pemasukan)
    except Exception:
        return 404, {"error": "Pemasukan not found"}


@router.get("/pengeluaran/{pengeluaran_id}", response={200: PengeluaranRead, 404: dict})
def read_pengeluaran_by_id(request, pengeluaran_id: int):
    """Retrieve a specific expense transaction by ID."""
    try:
        pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)
        return 200, PengeluaranRead.from_orm(pengeluaran)
    except Exception:
        return 404, {"error": "Pengeluaran not found"}


# API Endpoints for deleting transactions
@router.delete("/pengeluaran/{pengeluaran_id}/delete", response={200: dict, 404: dict})
def delete_pengeluaran(request, pengeluaran_id: int):
    """Delete an expense transaction."""
    try:
        pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)

        transaksi = pengeluaran.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pengeluaran.delete()

        return 200, {"message": "Pengeluaran deleted successfully"}
    except Exception:
        return 404, {"error": "Pengeluaran not found"}


@router.delete("/pemasukan/{pemasukan_id}/delete", response={200: dict, 404: dict})
def delete_pemasukan(request, pemasukan_id: int):
    """Delete an income transaction."""
    try:
        pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)

        transaksi = pemasukan.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pemasukan.delete()

        return 200, {"message": "Pemasukan deleted successfully"}
    except Exception:
        return 404, {"error": "Pemasukan not found"}


# API Endpoint for updating transactions
@router.put("/transaksi/{transaksi_id}/update", response={200: dict, 404: dict, 422: dict})
def update_transaksi(request, transaksi_id: int, payload: TransaksiUpdate):
    """Update a transaction."""
    try:
        transaksi = get_object_or_404(Transaksi, id=transaksi_id)
        
        # Check if transaction is already marked as deleted
        if transaksi.isDeleted:
            return 404, {"error": "Transaction not found or already deleted"}
        
        # Update fields if provided in payload
        if payload.status is not None:
            transaksi.status = payload.status
        
        if payload.catatan is not None:
            transaksi.catatan = payload.catatan
            
        if payload.namaPelanggan is not None:
            transaksi.namaPelanggan = payload.namaPelanggan
            
        if payload.nomorTeleponPelanggan is not None:
            transaksi.nomorTeleponPelanggan = payload.nomorTeleponPelanggan
            
        if payload.foto is not None:
            transaksi.foto = payload.foto
            
        if payload.daftarProduk is not None:
            # Clear existing products and set new ones
            transaksi.daftarProduk.clear()
            transaksi.daftarProduk.set(Produk.objects.filter(id__in=payload.daftarProduk))
        
        transaksi.save()
        
        return 200, {"message": "Transaction updated successfully"}
    except Exception as e:
        return 404, {"error": str(e)}


# API Endpoint for paginated and sorted transactions
@router.get(
    "/pemasukan/page/{page}",
    response={200: PaginatedPemasukanResponseSchema, 404: dict, 400: dict},
)
def get_pemasukan_paginated(
    request,
    page: int,
    sort: Optional[str] = None,
    sort_by: Optional[str] = "date",  
    q: Optional[str] = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Implementasi pagination untuk daftar pemasukan dengan sorting."""
    # Validate sort parameters
    
    if sort_by not in ["date", "amount"]:
        return 400, {"message": "Invalid sort_by parameter. Use 'date' or 'amount'."}

    # Determine sort field based on sort_by parameter
    sort_mapping = {
        "date": {
            "asc": "transaksi__tanggalTransaksi",
            "desc": "-transaksi__tanggalTransaksi"
        },
        "amount": {
            "asc": "totalPemasukan",
            "desc": "-totalPemasukan"
        }
    }
    
    order_by_field = sort_mapping[sort_by][sort] if sort else sort_mapping[sort_by]["desc"]

    # Base queryset of non-deleted records
    queryset = Pemasukan.objects.filter(transaksi__isDeleted=False)
    
    # Apply filters
    queryset = apply_filters(queryset)

    # Apply ordering
    queryset = queryset.order_by(order_by_field, "id")

    # Paginate results
    _, pagination_data = paginate_queryset(queryset, page, request)
    
        
    # Convert models to schemas
    pagination_data["items"] = [PemasukanRead.from_orm(p) for p in pagination_data["items"]]
    
    return 200, pagination_data

# Add these imports at the top of the file
from datetime import datetime, timedelta
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from .schemas import (
    LaporanRequest, LaporanPenjualanResponse, LaporanPengeluaranResponse,
    LaporanLabaRugiResponse, LaporanProdukResponse, LaporanPeriodeItem,
    LaporanLabaRugiItem, LaporanProdukItem
)

# Add these helper functions
def get_date_range(periode, tanggal_mulai=None, tanggal_akhir=None):
    """Get date range based on period"""
    today = datetime.now().date()
    
    if periode == "HARIAN":
        return today, today
    elif periode == "MINGGUAN":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    elif periode == "BULANAN":
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return start_date, end_date
    elif periode == "TAHUNAN":
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        return start_date, end_date
    elif periode == "KUSTOM":
        if not tanggal_mulai or not tanggal_akhir:
            raise ValueError("Custom period requires start and end dates")
        return tanggal_mulai, tanggal_akhir
    
    return today, today

def get_trunc_function(periode):
    """Get the appropriate truncation function for the period"""
    if periode == "HARIAN":
        return TruncDay
    elif periode == "MINGGUAN":
        return TruncWeek
    elif periode == "BULANAN":
        return TruncMonth
    # elif periode == "TAHUNAN":
    #     return TruncYear
    else:
        return TruncDay  # Default to daily for custom periods

# Add these new API endpoints
@router.post("/laporan/penjualan", response={200: LaporanPenjualanResponse, 422: dict})
def laporan_penjualan(request, payload: LaporanRequest):
    """Generate sales report"""
    try:
        start_date, end_date = get_date_range(
            payload.periode, payload.tanggal_mulai, payload.tanggal_akhir
        )
        
        # Filter pemasukan within date range
        pemasukan_queryset = Pemasukan.objects.filter(
            transaksi__tanggalTransaksi__date__gte=start_date,
            transaksi__tanggalTransaksi__date__lte=end_date,
            transaksi__isDeleted=False
        )
        
        # Calculate total sales and transaction count
        total_penjualan = pemasukan_queryset.aggregate(
            total=Sum('totalPemasukan')
        )['total'] or 0
        
        jumlah_transaksi = pemasukan_queryset.count()
        
        # Group by period
        trunc_function = get_trunc_function(payload.periode)
        periode_data = pemasukan_queryset.annotate(
            periode=trunc_function('transaksi__tanggalTransaksi')
        ).values('periode').annotate(
            total=Sum('totalPemasukan'),
            count=Count('id')
        ).order_by('periode')
        
        # Format period data
        formatted_periode_data = []
        for item in periode_data:
            formatted_periode_data.append(
                LaporanPeriodeItem(
                    periode=item['periode'].strftime('%Y-%m-%d'),
                    total=item['total'],
                    count=item['count']
                )
            )
        
        return 200, LaporanPenjualanResponse(
            total_penjualan=total_penjualan,
            jumlah_transaksi=jumlah_transaksi,
            periode_data=formatted_periode_data
        )
    
    except Exception as e:
        return 422, {"error": str(e)}

@router.post("/laporan/pengeluaran", response={200: LaporanPengeluaranResponse, 422: dict})
def laporan_pengeluaran(request, payload: LaporanRequest):
    """Generate expense report"""
    # try:
    start_date, end_date = get_date_range(
        payload.periode, payload.tanggal_mulai, payload.tanggal_akhir
    )
    
    # Filter pengeluaran within date range
    pengeluaran_queryset = Pengeluaran.objects.filter(
        transaksi__tanggalTransaksi__date__gte=start_date,
        transaksi__tanggalTransaksi__date__lte=end_date,
        transaksi__isDeleted=False
    )
    
    # Calculate total expenses and transaction count
    total_pengeluaran = pengeluaran_queryset.aggregate(
        total=Sum('totalPengeluaran')
    )['total'] or 0
    
    jumlah_transaksi = pengeluaran_queryset.count()
    
    # Group by period
    trunc_function = get_trunc_function(payload.periode)
    periode_data = pengeluaran_queryset.annotate(
        periode=trunc_function('transaksi__tanggalTransaksi')
    ).values('periode').annotate(
        total=Sum('totalPengeluaran'),
        count=Count('id')
    ).order_by('periode')
    
    # Format period data
    formatted_periode_data = []
    for item in periode_data:
        formatted_periode_data.append(
            LaporanPeriodeItem(
                periode=item['periode'].strftime('%Y-%m-%d'),
                total=item['total'],
                count=item['count']
            )
        )
    
    return 200, LaporanPengeluaranResponse(
        total_pengeluaran=total_pengeluaran,
        jumlah_transaksi=jumlah_transaksi,
        periode_data=formatted_periode_data
    )

    # except Exception as e:
    #     return 422, {"error": str(e)}

@router.post("/laporan/laba-rugi", response={200: LaporanLabaRugiResponse, 422: dict})
def laporan_laba_rugi(request, payload: LaporanRequest):
    """Generate profit/loss report"""
    # try:
    start_date, end_date = get_date_range(
        payload.periode, payload.tanggal_mulai, payload.tanggal_akhir
    )
    
    # Filter transactions within date range
    pemasukan_queryset = Pemasukan.objects.filter(
        transaksi__tanggalTransaksi__date__gte=start_date,
        transaksi__tanggalTransaksi__date__lte=end_date,
        transaksi__isDeleted=False
    )
    
    pengeluaran_queryset = Pengeluaran.objects.filter(
        transaksi__tanggalTransaksi__date__gte=start_date,
        transaksi__tanggalTransaksi__date__lte=end_date,
        transaksi__isDeleted=False
    )
    
    # Calculate totals
    total_penjualan = pemasukan_queryset.aggregate(
        total=Sum('totalPemasukan')
    )['total'] or 0
    
    total_pengeluaran = pengeluaran_queryset.aggregate(
        total=Sum('totalPengeluaran')
    )['total'] or 0
    
    laba_rugi = total_penjualan - total_pengeluaran
    
    # Group by period
    trunc_function = get_trunc_function(payload.periode)
    
    # Get pemasukan by period
    pemasukan_by_periode = dict(
        pemasukan_queryset.annotate(
            periode=trunc_function('transaksi__tanggalTransaksi')
        ).values('periode').annotate(
            total=Sum('totalPemasukan')
        ).values_list('periode', 'total')
    )
    
    # Get pengeluaran by period
    pengeluaran_by_periode = dict(
        pengeluaran_queryset.annotate(
            periode=trunc_function('transaksi__tanggalTransaksi')
        ).values('periode').annotate(
            total=Sum('totalPengeluaran')
        ).values_list('periode', 'total')
    )
    
    # Combine periods
    all_periods = set(pemasukan_by_periode.keys()) | set(pengeluaran_by_periode.keys())
    
    # Format period data
    periode_data = []
    for periode in sorted(all_periods):
        penjualan = pemasukan_by_periode.get(periode, 0)
        pengeluaran = pengeluaran_by_periode.get(periode, 0)
        
        periode_data.append(
            LaporanLabaRugiItem(
                periode=periode.strftime('%Y-%m-%d'),
                total_penjualan=penjualan,
                total_pengeluaran=pengeluaran,
                laba_rugi=penjualan - pengeluaran
            )
        )
    
    return 200, LaporanLabaRugiResponse(
        total_penjualan=total_penjualan,
        total_pengeluaran=total_pengeluaran,
        laba_rugi=laba_rugi,
        periode_data=periode_data
    )

    # except Exception as e:
    #     return 422, {"error": str(e)}

@router.post("/laporan/produk", response={200: LaporanProdukResponse, 422: dict})
def laporan_produk(request, payload: LaporanRequest):
    """Generate product sales report"""
    # try:
    start_date, end_date = get_date_range(
        payload.periode, payload.tanggal_mulai, payload.tanggal_akhir
    )
    
    # Get all income transactions in the date range
    pemasukan_list = Pemasukan.objects.filter(
        transaksi__tanggalTransaksi__date__gte=start_date,
        transaksi__tanggalTransaksi__date__lte=end_date,
        transaksi__isDeleted=False
    )
    
    # Get all products from these transactions
    product_data = {}
    total_sold = 0
    total_revenue = 0
    
    # Collect data about each product
    for pemasukan in pemasukan_list:
        transaksi = pemasukan.transaksi
        products = transaksi.daftarProduk.all()
        
        # Distribute income evenly across products for simplicity
        # In a real system, you'd want to track quantities and prices per product
        if products.count() > 0:
            revenue_per_product = pemasukan.totalPemasukan / products.count()
            
            for product in products:
                if product.id not in product_data:
                    product_data[product.id] = {
                        'id': product.id,
                        'nama': product.nama,
                        'total_terjual': 0,
                        'total_pendapatan': 0
                    }
                
                product_data[product.id]['total_terjual'] += 1
                product_data[product.id]['total_pendapatan'] += revenue_per_product
                
                total_sold += 1
                total_revenue += revenue_per_product
    
    # Sort products by total revenue (highest first)
    sorted_products = sorted(
        product_data.values(),
        key=lambda x: x['total_pendapatan'],
        reverse=True
    )
    
    # Format product data
    formatted_produk_data = []
    for item in sorted_products:
        formatted_produk_data.append(
            LaporanProdukItem(
                id=item['id'],
                nama=item['nama'],
                total_terjual=item['total_terjual'],
                total_pendapatan=item['total_pendapatan']
            )
        )
    
    return 200, LaporanProdukResponse(
        total_produk_terjual=total_sold,
        total_pendapatan=total_revenue,
        produk_data=formatted_produk_data
    )
    
    # except Exception as e:
    #     return 422, {"error": str(e)}
    
@router.get("/all-transactions", response={200: List[dict]})
def get_all_transactions(request):
    """Retrieve all transactions from all users/stores."""
    all_transactions = []
    
    # Get all non-deleted transactions
    pemasukan_list = Pemasukan.objects.filter(transaksi__isDeleted=False)
    pengeluaran_list = Pengeluaran.objects.filter(transaksi__isDeleted=False)
    
    # Process income transactions
    for pemasukan in pemasukan_list:
        transaksi = pemasukan.transaksi
        # Get user from the first product (Note: This assumes all products in the transaction belong to the same user)
        if not transaksi.daftarProduk.exists():
            continue
        
        user = transaksi.daftarProduk.first().user
        
        all_transactions.append({
            "id": pemasukan.id,
            "type": "pemasukan",
            "transaksi_id": transaksi.id,
            "status": transaksi.status,
            "catatan": transaksi.catatan,
            "namaPelanggan": transaksi.namaPelanggan,
            "nomorTeleponPelanggan": transaksi.nomorTeleponPelanggan,
            "tanggalTransaksi": transaksi.tanggalTransaksi.isoformat(),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "kategori": pemasukan.kategori,
            "total": pemasukan.totalPemasukan
        })
    
    # Process expense transactions
    for pengeluaran in pengeluaran_list:
        transaksi = pengeluaran.transaksi
        # Get user from the first product (Note: This assumes all products in the transaction belong to the same user)
        # if not transaksi.daftarProduk.exists():
        #     continue
        
        user = transaksi.daftarProduk.first().user
        
        all_transactions.append({
            "id": pengeluaran.id,
            "type": "pengeluaran",
            "transaksi_id": transaksi.id,
            "status": transaksi.status,
            "catatan": transaksi.catatan,
            "namaPelanggan": transaksi.namaPelanggan,
            "nomorTeleponPelanggan": transaksi.nomorTeleponPelanggan,
            "tanggalTransaksi": transaksi.tanggalTransaksi.isoformat(),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "kategori": pengeluaran.kategori,
            "total": pengeluaran.totalPengeluaran
        })
    
    # Sort by date (newest first)
    all_transactions.sort(key=lambda t: t["tanggalTransaksi"], reverse=True)
    
    return 200, all_transactions

@router.get("/all-transactions/page/{page}", response={200: dict, 404: dict})
def get_all_transactions_paginated(request, page: int):
    """Retrieve all transactions from all stores/users with pagination."""
    all_transactions = []
    
    # Get all non-deleted transactions
    pemasukan_list = Pemasukan.objects.filter(transaksi__isDeleted=False)
    
    # Process income transactions
    for pemasukan in pemasukan_list:
        transaksi = pemasukan.transaksi
        # Get user from the first product (Note: This assumes all products in the transaction belong to the same user)
        # if not transaksi.daftarProduk.exists():
        #     continue
        
        user = transaksi.daftarProduk.first().user
        
        all_transactions.append({
            "id": pemasukan.id,
            "type": "pemasukan",
            "transaksi_id": transaksi.id,
            "status": transaksi.status,
            "catatan": transaksi.catatan,
            "namaPelanggan": transaksi.namaPelanggan,
            "nomorTeleponPelanggan": transaksi.nomorTeleponPelanggan,
            "tanggalTransaksi": transaksi.tanggalTransaksi.isoformat(),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "kategori": pemasukan.kategori,
            "total": pemasukan.totalPemasukan
        })
    
    
    # Sort by date (newest first)
    all_transactions.sort(key=lambda t: t["tanggalTransaksi"], reverse=True)
    
    # Pagination
    # try:
    per_page = int(request.GET.get("per_page", 10))
    # except ValueError:
    #     per_page = 10

    total = len(all_transactions)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}

    offset = (page - 1) * per_page
    page_items = all_transactions[offset : offset + per_page]

    return 200, {
        "items": page_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }