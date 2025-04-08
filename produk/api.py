from ninja import File, Form, Router, UploadedFile
from ninja import Router, UploadedFile
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from backend import settings
from produk.models import Produk, KategoriProduk
from ninja.security import HttpBearer
import jwt, imghdr
from django.http import HttpResponse
from produk.schemas import (
    PaginatedResponseSchema,
    ProdukResponseSchema,
    CreateProdukSchema,
    UpdateProdukSchema,
)
from authentication.models import User


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


@router.get("", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_default(request, sort: str = None):
    return get_produk_paginated(request, page=1, sort=sort)


@router.get("/page/{page}", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_paginated(request, page: int, sort: str = None, q: str = ""):
    if sort not in [None, "asc", "desc"]:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")

    user_id = request.auth
    user = User.objects.get(id=user_id)
    order_by_field = "stok" if sort == "asc" else "-stok"

    if user.role == "Karyawan":
        queryset = Produk.objects.filter(user=user.owner)
    else:
        queryset = Produk.objects.filter(user=user)

    if q:
        queryset = queryset.filter(nama__icontains=q)

    queryset = queryset.select_related("kategori").order_by(order_by_field, "id")

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

MAX_FILE_SIZE_MB = 3
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

@router.post("/create", response={201: ProdukResponseSchema, 422: dict})
def create_produk(request, payload: CreateProdukSchema, foto: UploadedFile = None):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)

    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=payload.kategori)

    if foto:
        allowed_types = ["jpeg", "png", "jpg", "webp"]
        file_type = imghdr.what(foto)
        if file_type not in allowed_types:
            return 422, {"message": "Format file tidak valid! Harap unggah PNG, JPG, atau JPEG."}
        if foto.size > MAX_FILE_SIZE_BYTES:
            return 422, {"message": f"Ukuran file terlalu besar! Maksimal {MAX_FILE_SIZE_MB}MB."}
    
    produk = Produk.objects.create(
        nama=payload.nama,
        foto=foto,
        harga_modal=payload.harga_modal,
        harga_jual=payload.harga_jual,
        stok=payload.stok,
        satuan=payload.satuan,
        kategori=kategori_obj,
        user=user,
    )

    return 201, ProdukResponseSchema.from_orm(produk)

@router.get("/{id}", response={200: ProdukResponseSchema, 404: dict})
def get_produk_by_id(request, id: int):
    user_id = request.auth
    try:
        produk = get_object_or_404(Produk, id=id, user_id=user_id)
        return 200, ProdukResponseSchema.from_orm(produk)
    except Exception as e:
        return 404, {"message": "Produk tidak ditemukan"}

@router.post("/update/{id}", response={200: ProdukResponseSchema, 404: dict, 422: dict})
def update_produk(request, id: int, payload: UpdateProdukSchema, foto: UploadedFile = None):
    user_id = request.auth

    try:
        produk = get_object_or_404(Produk, id=id, user_id=user_id)

        # Update fields from the payload if provided
        if payload.nama is not None:
            produk.nama = payload.nama
        if payload.kategori is not None:
            # Get or create the category instance
            kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=payload.kategori)
            produk.kategori = kategori_obj
        if payload.harga_jual is not None:
            produk.harga_jual = payload.harga_jual
        if payload.harga_modal is not None:
            produk.harga_modal = payload.harga_modal
        if payload.stok is not None:
            produk.stok = payload.stok
        if payload.satuan is not None:
            produk.satuan = payload.satuan

        # Handle the uploaded file (if provided)
        if foto:
            produk.foto = foto

        produk.save()

        return 200, ProdukResponseSchema.from_orm(produk)

    except Exception as e:
        return 422, {"message": str(e)}


@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    user_id = request.auth
    produk = get_object_or_404(Produk, id=id, user_id=user_id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}


@router.get("/low-stock", response=list[ProdukResponseSchema])
def get_low_stock_products(request):
    user_id = request.auth
    products = (
        Produk.objects.select_related("kategori")
        .filter(stok__lt=10, user_id=user_id)
        .order_by("id")
    )
    return [ProdukResponseSchema.from_orm(p) for p in products]
