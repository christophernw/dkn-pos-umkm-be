from ninja import Router
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from produk.models import Produk, KategoriProduk
from produk.schemas import PaginatedResponseSchema, ProdukSchema, CreateProdukSchema

router = Router()

def get_produk_queryset(sort=None):
    if sort not in [None, "asc", "desc"]:
        return None
        
    order_by_field = "stok" if sort == "asc" else "-stok"
    return Produk.objects.select_related("kategori").order_by(order_by_field, "id")

def format_produk_response(produk_list):
    return [
        ProdukSchema(
            id=p.id,
            nama=p.nama,
            foto=p.foto,
            harga_modal=float(p.harga_modal),
            harga_jual=float(p.harga_jual),
            stok=float(p.stok),
            satuan=p.satuan,
            kategori=p.kategori.nama,
        )
        for p in produk_list
    ]

@router.get("", response=list[ProdukSchema])
def get_produk(request, sort: str = None):
    queryset = get_produk_queryset(sort)
    if queryset is None:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")
    
    return format_produk_response(queryset)

@router.get("/page/{page}", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_paginated(request, page: int, sort: str = None):
    queryset = get_produk_queryset(sort)
    if queryset is None:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")
    
    per_page = 7
    if 'per_page' in request.GET:
        try:
            per_page = int(request.GET.get('per_page'))
        except ValueError:
            pass
    
    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page
    
    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}
    
    offset = (page - 1) * per_page
    page_items = queryset[offset:offset + per_page]
    
    return 200, {
        "items": format_produk_response(page_items),
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

@router.post("/create", response={201: ProdukSchema, 422: dict})
def create_produk(request):
    print(request)

    nama = request.POST.get("nama")
    foto = request.FILES.get("foto")
    harga_modal = request.POST.get("harga_modal")
    harga_jual = request.POST.get("harga_jual")
    stok = request.POST.get("stok")
    satuan = request.POST.get("satuan")
    kategori_nama = request.POST.get("kategori")

    try:
        harga_modal = float(harga_modal)
        harga_jual = float(harga_jual)
        stok = float(stok)
    except ValueError:
        return 422, {"detail": "Harga atau stok harus berupa angka"}

    if harga_modal < 0 or harga_jual < 0:
        return 422, {"detail": "Harga minus seharusnya invalid"}

    if stok < 0:
        return 422, {"detail": "Stok minus seharusnya invalid"}

    # Ambil atau buat kategori
    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=kategori_nama)

    # Simpan ke database
    produk = Produk.objects.create(
        nama=nama,
        foto=foto,
        harga_modal=harga_modal,
        harga_jual=harga_jual,
        stok=stok,
        satuan=satuan,
        kategori=kategori_obj
    )
    
    return 201, ProdukSchema(
        id=produk.id,
        nama=produk.nama,
        foto=produk.foto,
        harga_modal=float(produk.harga_modal),
        harga_jual=float(produk.harga_jual),
        stok=float(produk.stok),
        satuan=produk.satuan,
        kategori=kategori_obj.nama,
    )
  
@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    produk = get_object_or_404(Produk, id=id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}

@router.get("/search", response=list[ProdukSchema])
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
    
@router.get("/low-stock", response=list[ProdukSchema])
def get_low_stock_products(request):
    queryset = Produk.objects.select_related("kategori").filter(stok__lt=10).order_by("id")
    return format_produk_response(queryset)