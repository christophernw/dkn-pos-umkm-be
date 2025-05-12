from ninja import Router, UploadedFile
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from backend import settings
from produk.models import Produk, KategoriProduk, Satuan
from ninja.security import HttpBearer
import jwt
from django.http import HttpResponse
from produk.schemas import (
    PaginatedResponseSchema,
    ProdukResponseSchema,
    CreateProdukSchema,
    UpdateProdukSchema,
)
from authentication.models import User
from django.db.models import Sum
from datetime import datetime
from transaksi.models import TransaksiItem
from ratelimit.decorators import ratelimit
import logging

logger = logging.getLogger(__name__)

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp"], "verify_exp": True}
            )
            user_id = payload.get("user_id")
            if user_id:
                return user_id
        except jwt.PyJWTError:
            return None
        return None

router = Router(auth=AuthBearer())

# ==== HELPERS ====

def _get_user_and_toko(request):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    if not user.toko:
        return None, {"status": 404, "message": "User doesn't have a toko"}
    return user, None

def _resolve_kategori(nama, toko):
    return KategoriProduk.objects.get_or_create(nama=nama, toko=toko)[0]

def _resolve_satuan(nama):
    return Satuan.objects.get_or_create(nama=nama)[0]

def _get_month_range(year, month):
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end

# ==== ROUTES ====

@router.get("", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_default(request, sort: str = None):
    return get_produk_paginated(request, page=1, sort=sort)

@router.get("/categories", response={200: list, 404: dict})
def get_categories(request):
    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}
    categories = KategoriProduk.objects.filter(toko=user.toko).values_list('nama', flat=True)
    return 200, list(categories)

@router.get("/units", response={200: list, 404: dict})
def get_units(request):
    units = Satuan.objects.all().values_list('nama', flat=True)
    return 200, list(units)

@router.get("/page/{page}", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_paginated(request, page: int, sort: str = None, q: str = ""):
    if sort not in [None, "stok", "-stok", "-id"]:
        return HttpResponseBadRequest("Invalid sort parameter.")
    sort = sort or "-id"

    if len(q) > 100:
        return 400, {"message": "Query too long"}

    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}

    queryset = Produk.objects.filter(toko=user.toko)
    if q:
        queryset = queryset.filter(nama__icontains=q)
    queryset = queryset.select_related("kategori").order_by(sort)

    try:
        per_page = int(request.GET.get("per_page", 7))
    except ValueError:
        per_page = 7

    total = queryset.count()
    total_pages = (total + per_page - 1) // per_page
    if page > total_pages and total > 0:
        return 404, {"message": "Page not found"}

    offset = (page - 1) * per_page
    page_items = queryset[offset: offset + per_page]

    return 200, {
        "items": [ProdukResponseSchema.from_orm(p) for p in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }

@router.post("/create", response={201: ProdukResponseSchema, 422: dict})
def create_produk(request, payload: CreateProdukSchema, foto: UploadedFile = None):
    user, error = _get_user_and_toko(request)
    if error:
        return 422, {"message": error["message"]}

    if foto:
        if not foto.content_type.startswith("image/"):
            return 400, {"message": "Only image files allowed"}
        if foto.size > 2 * 1024 * 1024:
            return 400, {"message": "Image too large (max 2MB)"}

    kategori_obj = _resolve_kategori(payload.kategori, user.toko)
    satuan_obj = _resolve_satuan(payload.satuan)

    produk = Produk.objects.create(
        nama=payload.nama,
        foto=foto,
        harga_modal=payload.harga_modal,
        harga_jual=payload.harga_jual,
        stok=payload.stok,
        satuan=satuan_obj.nama,
        kategori=kategori_obj,
        toko=user.toko,
    )

    return 201, ProdukResponseSchema.from_orm(produk)

@router.get("/most-popular", response={200: list, 404: dict})
def get_most_popular_products(request):
    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}

    popular_products = (
        TransaksiItem.objects
        .filter(
            transaksi__toko=user.toko,
            transaksi__is_deleted=False,
            transaksi__category="Penjualan Barang"
        )
        .values('product__id', 'product__nama')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:3]
    )

    result = []
    for item in popular_products:
        product = Produk.objects.get(id=item['product__id'])
        result.append({
            "id": product.id,
            "name": product.nama,
            "sold": item['total_sold'],
            "imageUrl": product.foto.url if product.foto else None,
        })

    return 200, result

@router.get("/low-stock", response={200: list, 404: dict})
def get_low_stock_products(request):
    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}

    products = Produk.objects.select_related("kategori").filter(toko=user.toko).order_by('stok')[:5]

    result = [{
        "id": product.id,
        "name": product.nama,
        "stock": product.stok,
        "imageUrl": product.foto.url if product.foto else None,
    } for product in products]

    return 200, result

@ratelimit(key='user', rate='5/m', method='GET', block=True)
@router.get("/{id}", response={200: ProdukResponseSchema, 404: dict})
def get_produk_by_id(request, id: int):
    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}
    produk = get_object_or_404(Produk, id=id, toko=user.toko)
    return 200, ProdukResponseSchema.from_orm(produk)

@router.post("/update/{id}", response={200: ProdukResponseSchema, 404: dict, 422: dict})
def update_produk(request, id: int, payload: UpdateProdukSchema, foto: UploadedFile = None):
    user, error = _get_user_and_toko(request)
    if error:
        return 422, {"message": error["message"]}

    try:
        produk = get_object_or_404(Produk, id=id, toko=user.toko)
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        if 'kategori' in update_data:
            produk.kategori = _resolve_kategori(update_data.pop('kategori'), user.toko)

        if 'satuan' in update_data:
            produk.satuan = _resolve_satuan(update_data.pop('satuan')).nama

        for field, value in update_data.items():
            setattr(produk, field, value)

        if foto:
            if not foto.content_type.startswith("image/"):
                return 400, {"message": "Only image files allowed"}
            if foto.size > 2 * 1024 * 1024:
                return 400, {"message": "Image too large (max 2MB)"}
            produk.foto = foto

        produk.save()
        return 200, ProdukResponseSchema.from_orm(produk)

    except Exception as e:
        logger.error(f"Update error: {str(e)}")
        return 422, {"message": "Terjadi kesalahan sistem"}

@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    user, error = _get_user_and_toko(request)
    if error:
        return {"message": error["message"]}
    produk = get_object_or_404(Produk, id=id, toko=user.toko)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}

@router.get("/top-selling/{year}/{month}", response={200: list, 404: dict})
def get_top_selling_products(request, year: int, month: int):
    user, error = _get_user_and_toko(request)
    if error:
        return error["status"], {"message": error["message"]}
    start_date, end_date = _get_month_range(year, month)

    top_products = (
        TransaksiItem.objects
        .filter(
            transaksi__toko=user.toko,
            transaksi__created_at__gte=start_date,
            transaksi__created_at__lt=end_date,
            transaksi__is_deleted=False,
            transaksi__category="Penjualan Barang"
        )
        .values('product__id', 'product__nama', 'product__foto')
        .annotate(sold=Sum('quantity'))
        .order_by('-sold')[:3]
    )

    result = [{
        "id": product['product__id'],
        "name": product['product__nama'],
        "imageUrl": product['product__foto'],
        "sold": product['sold']
    } for product in top_products]

    return 200, result

