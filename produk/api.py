from ninja import Router
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from produk.models import Produk, KategoriProduk
from produk.schemas import (
    PaginatedResponseSchema,
    ProdukResponseSchema,
    CreateProdukSchema,
)

router = Router()


@router.get("", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_default(request, sort: str = None):
    return get_produk_paginated(request, page=1, sort=sort)


@router.get("/page/{page}", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_paginated(request, page: int, sort: str = None):
    if sort not in [None, "asc", "desc"]:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")

    order_by_field = "stok" if sort == "asc" else "-stok"
    queryset = Produk.objects.select_related("kategori").order_by(order_by_field, "id")

    try:
        per_page = int(request.GET.get("per_page", 7))
    except ValueError:
        per_page = 7

    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page

    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}

    offset = (page - 1) * per_page
    page_items = queryset[offset : offset + per_page]

    return 200, {
        "items": [ProdukResponseSchema.from_orm(p) for p in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.post("/create", response={201: ProdukResponseSchema, 422: dict})
def create_produk(request, payload: CreateProdukSchema):
    nama = payload.nama
    foto = payload.foto
    harga_modal = payload.harga_modal
    harga_jual = payload.harga_jual
    stok = payload.stok
    satuan = payload.satuan
    kategori_nama = payload.kategori

    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=kategori_nama)

    produk = Produk.objects.create(
        nama=nama,
        foto=foto,
        harga_modal=harga_modal,
        harga_jual=harga_jual,
        stok=stok,
        satuan=satuan,
        kategori=kategori_obj,
    )

    return 201, ProdukResponseSchema.from_orm(produk)


@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    produk = get_object_or_404(Produk, id=id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}


@router.get("/search", response=list[ProdukResponseSchema])
def search_produk(request, q: str = ""):
    produk_list = Produk.objects.filter(nama__icontains=q)
    return [
        {
            "id": p.id,
            "nama": p.nama,
            "foto": p.foto,
            "harga_modal": p.harga_modal,
            "harga_jual": p.harga_jual,
            "stok": p.stok,
            "satuan": p.satuan,
            "kategori": p.kategori.nama,
        }
        for p in produk_list
    ]


@router.get("/low-stock", response=list[ProdukResponseSchema])
def get_low_stock_products(request):
    products = (
        Produk.objects.select_related("kategori").filter(stok__lt=10).order_by("id")
    )
    return [ProdukResponseSchema.from_orm(p) for p in products]
