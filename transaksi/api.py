from ninja import Router, Query
from typing import List, Optional
from django.db.models import Q
from django.shortcuts import get_object_or_404
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


@router.post("/pemasukan/create", response=PemasukanRead)
def create_pemasukan(request, payload: PemasukanCreate):

    transaksi = Transaksi.objects.create(
        status=payload.status,
        catatan=payload.catatan,
        namaPelanggan=payload.namaPelanggan,
        nomorTeleponPelanggan=payload.nomorTeleponPelanggan,
        foto=payload.foto,
    )

    transaksi.save()
    transaksi.daftarProduk.set(Produk.objects.filter(id__in=payload.daftarProduk))

    pemasukan = Pemasukan.objects.create(
        transaksi=transaksi,
        kategori=payload.kategori,
        totalPemasukan=payload.totalPemasukan,
        hargaModal=payload.hargaModal,
    )

    return PemasukanRead.from_orm(pemasukan)


@router.post("/pengeluaran/create", response=PengeluaranRead)
def create_pengeluaran(request, payload: PengeluaranCreate):

    transaksi = Transaksi.objects.create(
        status=payload.status,
        catatan=payload.catatan,
        namaPelanggan=payload.namaPelanggan,
        nomorTeleponPelanggan=payload.nomorTeleponPelanggan,
        foto=payload.foto,
    )

    transaksi.daftarProduk.set(Produk.objects.filter(id__in=payload.daftarProduk))

    pengeluaran = Pengeluaran.objects.create(
        transaksi=transaksi,
        kategori=payload.kategori,
        totalPengeluaran=payload.totalPengeluaran,
    )

    return PengeluaranRead.from_orm(pengeluaran)


@router.get("/pemasukan/daftar", response=List[PemasukanRead])
def read_pemasukan(request):
    pemasukan_list = Pemasukan.objects.all()
    return [PemasukanRead.from_orm(p) for p in pemasukan_list]


@router.get("/pengeluaran/daftar", response=List[PengeluaranRead])
def read_pengeluaran(request):
    pengeluaran_list = Pengeluaran.objects.all()
    return [PengeluaranRead.from_orm(p) for p in pengeluaran_list]


@router.get("/pemasukan/{pemasukan_id}", response=PemasukanRead)
def read_pemasukan_by_id(request, pemasukan_id: int):
    pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)
    return PemasukanRead.from_orm(pemasukan)


@router.get("/pengeluaran/{pengeluaran_id}", response=PengeluaranRead)
def read_pengeluaran_by_id(request, pengeluaran_id: int):
    pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)
    return PengeluaranRead.from_orm(pengeluaran)


@router.delete("/pengeluaran/{pengeluaran_id}/delete", response={200: dict, 404: dict})
def delete_pengeluaran(request, pengeluaran_id: int):
    try:
        pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)

        transaksi = pengeluaran.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pengeluaran.delete()

        return 200, {"message": "Pengeluaran deleted successfully"}
    except:
        return 404, {"error": "Pengeluaran not found"}
        raise


@router.delete("/pemasukan/{pemasukan_id}/delete", response={200: dict, 404: dict})
def delete_pemasukan(request, pemasukan_id: int):
    try:
        pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)

        transaksi = pemasukan.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pemasukan.delete()

        return 200, {"message": "Pemasukan deleted successfully"}
    except:
        return 404, {"error": "Pemasukan not found"}
        raise


@router.put("/transaksi/{transaksi_id}/update", response={200: dict, 404: dict})
def update_transaksi(request, transaksi_id: int, payload: TransaksiUpdate):
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
            transaksi.daftarProduk.set(
                Produk.objects.filter(id__in=payload.daftarProduk)
            )

        transaksi.save()

        return 200, {"message": "Transaction updated successfully"}
    except Exception as e:
        return 404, {"error": str(e)}


# Add this to your existing router


@router.get(
    "/pemasukan/page/{page}",
    response={200: PaginatedPemasukanResponseSchema, 404: dict, 400: dict},
)
def get_pemasukan_paginated(
    request,
    page: int,
    sort: Optional[str] = None,
    q: Optional[str] = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Implementasi pagination untuk daftar pemasukan
    """
    if sort not in [None, "asc", "desc"]:
        return 400, {"message": "Invalid sort parameter. Use 'asc' or 'desc'."}

    # Default sort by date descending
    order_by_field = (
        "transaksi__tanggalTransaksi"
        if sort == "asc"
        else "-transaksi__tanggalTransaksi"
    )

    # Get base queryset of non-deleted records
    queryset = Pemasukan.objects.filter(transaksi__isDeleted=False)

    # Apply search filter
    if q:
        queryset = queryset.filter(
            Q(transaksi__catatan__icontains=q)
            | Q(kategori__icontains=q)
            | Q(transaksi__namaPelanggan__icontains=q)
        )

    # Apply date filters
    if start_date:
        queryset = queryset.filter(transaksi__tanggalTransaksi__date__gte=start_date)

    if end_date:
        queryset = queryset.filter(transaksi__tanggalTransaksi__date__lte=end_date)

    queryset = queryset.order_by(order_by_field, "id")

    # Pagination logic
    try:
        per_page = int(request.GET.get("per_page", 10))
    except ValueError:
        per_page = 10

    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}

    offset = (page - 1) * per_page
    page_items = queryset[offset : offset + per_page]

    return 200, {
        "items": [PemasukanRead.from_orm(p) for p in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }
