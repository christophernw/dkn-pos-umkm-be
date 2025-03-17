from ninja import File, Form, Router, UploadedFile
from ninja import Router, UploadedFile
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from backend import settings
from produk.models import Produk, KategoriProduk
from ninja.security import HttpBearer
import jwt
from django.http import HttpResponse
from produk.schemas import (
    PaginatedResponseSchema,
    ProdukResponseSchema,
    CreateProdukSchema,
    UpdateProdukSchema,
    UpdateProdukStokSchema,
)
from django.contrib.auth.models import User


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
    order_by_field = "stok" if sort == "asc" else "-stok"

    queryset = Produk.objects.filter(user_id=user_id)
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

@router.get("/{id}", response={200: ProdukResponseSchema, 404: dict})
def get_produk_by_id(request, id: int):
    user_id = request.auth
    produk = Produk.objects.filter(id=id, user_id=user_id).select_related("kategori").first()
    if not produk:
        return 404, {"detail": "Produk tidak ditemukan"}

    return 200, ProdukResponseSchema.from_orm(produk)

@router.put("/update/{id}", response={200: ProdukResponseSchema, 404: dict, 400: dict})
def update_produk(request, id: int, payload: UpdateProdukSchema):
    user_id = request.auth
    produk = get_object_or_404(Produk, id=id, user_id=user_id)

    # Validasi harga dan stok tidak boleh negatif jika ada perubahan
    if payload.harga_modal is not None and payload.harga_modal < 0:
        return 400, {"detail": "Harga modal tidak boleh negatif"}
    if payload.harga_jual is not None and payload.harga_jual < 0:
        return 400, {"detail": "Harga jual tidak boleh negatif"}
    if payload.stok is not None and payload.stok < 0:
        return 400, {"detail": "Stok tidak boleh negatif"}

    # Perbarui hanya field yang diberikan
    for attr, value in payload.dict(exclude_unset=True).items():
        if attr == "kategori":
            kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=value)
            setattr(produk, "kategori", kategori_obj)
        else:
            setattr(produk, attr, value)

    produk.save()

    return 200, ProdukResponseSchema.from_orm(produk)

@router.post("/create", response={201: ProdukResponseSchema, 422: dict})
def create_produk(request, payload: CreateProdukSchema, foto: UploadedFile = None):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)

    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=payload.kategori)

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

@router.post(
    "/update/{id}", response={200: ProdukResponseSchema, 404: dict, 422: dict}
)
def update_produk(
    request, id: int, payload: CreateProdukSchema, foto: UploadedFile = None
):
    user_id = request.auth

    try:
        produk = get_object_or_404(Produk, id=id, user_id=user_id)

        produk.nama = payload.nama
        produk.harga_modal = payload.harga_modal
        produk.harga_jual = payload.harga_jual
        produk.stok = payload.stok
        produk.satuan = payload.satuan

        kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=payload.kategori)
        produk.kategori = kategori_obj

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
