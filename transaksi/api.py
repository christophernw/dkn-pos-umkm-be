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

    products_valid, products, error = validate_products(product_ids)
        
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
    q: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> QuerySet:
    """Apply common filters to a queryset."""
    # Apply search filter
    if q:
        queryset = queryset.filter(
            Q(transaksi__catatan__icontains=q)
            | Q(kategori__icontains=q)
            | Q(transaksi__namaPelanggan__icontains=q)
        )
        
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
        success, result = create_transaction_base(
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
        success, result = create_transaction_base(
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
    queryset = apply_filters(queryset, q, start_date, end_date)

    # Apply ordering
    queryset = queryset.order_by(order_by_field, "id")

    # Paginate results
    status, pagination_data = paginate_queryset(queryset, page, request)
    
        
    # Convert models to schemas
    pagination_data["items"] = [PemasukanRead.from_orm(p) for p in pagination_data["items"]]
    
    return 200, pagination_data