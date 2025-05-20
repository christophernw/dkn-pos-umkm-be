from decimal import Decimal, InvalidOperation
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
from django.db.models import Sum, F
from datetime import datetime
from dateutil.relativedelta import relativedelta
from transaksi.models import TransaksiItem
from typing import Optional

NO_TOKO_MESSAGE = "User doesn't have a toko"
MAX_DECIMAL = Decimal("99999999.99")

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": True})
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


@router.get("/categories", response={200: list, 404: dict})
def get_categories(request):
    user_id = request.auth
    user = User.objects.get(id=user_id)

    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}

    categories = KategoriProduk.objects.filter(toko=user.toko).values_list('nama', flat=True)
    return 200, list(categories)


@router.get("/units", response={200: list, 404: dict})
def get_units(request):
    user_id = request.auth
    user = User.objects.get(id=user_id)

    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}

    units = Satuan.objects.filter(toko=user.toko).values_list('nama', flat=True)
    return 200, list(units)


@router.get("/page/{page}", response={200: PaginatedResponseSchema, 404: dict})
def get_produk_paginated(request, page: int, sort: str = None, q: str = ""):
    if sort not in [None, "stok", "-stok", "-id"]:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")

    if sort is None:
        sort = "-id"
    
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}

    # Filter products by toko instead of user
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
    page_items = queryset[offset : offset + per_page]

    return 200, {
        "items": [ProdukResponseSchema.from_orm(p) for p in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.post("/create", response={201: ProdukResponseSchema, 422: dict})
def create_produk(request, payload: CreateProdukSchema, foto: UploadedFile = None):
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has a toko
    if not user.toko:
        return 422, {"message": NO_TOKO_MESSAGE}
    
    try:
        if Decimal(payload.harga_modal) > MAX_DECIMAL or Decimal(payload.harga_jual) > MAX_DECIMAL:
            return 422, {"message": "Harga terlalu besar. Maksimum adalah 99.999.999,99"}
    except InvalidOperation:
        return 422, {"message": "Format harga tidak valid."}

    # Get or create category
    kategori_obj, _ = KategoriProduk.objects.get_or_create(
    nama=payload.kategori,
    toko=user.toko
)
    
    # Get or create unit (satuan)
    satuan_obj, _ = Satuan.objects.get_or_create(
        nama=payload.satuan,
        toko=user.toko
    )

    produk = Produk.objects.create(
        nama=payload.nama,
        foto=foto,
        harga_modal=payload.harga_modal,
        harga_jual=payload.harga_jual,
        stok=payload.stok,
        satuan=satuan_obj.nama,  # Use the satuan name
        kategori=kategori_obj,
        toko=user.toko,  # Associate with toko instead of user
    )

    return 201, ProdukResponseSchema.from_orm(produk)


@router.get("/most-popular", response={200: list, 404: dict})
def get_most_popular_products(request):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}
    
    # Get most popular products by all-time sales volume
    popular_products = (
        TransaksiItem.objects
        .filter(
            transaksi__toko=user.toko,
            transaksi__is_deleted=False,
            transaksi__category="Penjualan Barang"
        )
        .values('product__id', 'product__nama')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:3]  # Get top 3
    )
    
    result = []
    for item in popular_products:
        product = Produk.objects.get(id=item['product__id'])
        result.append({
            "id": product.id,
            "name": product.nama,
            "sold": item['total_sold'],  # Show sold instead of stock
            "imageUrl": product.foto.url if product.foto else None,
        })
    
    return 200, result

@router.get("/low-stock", response={200: list, 404: dict})
def get_low_stock_products(request):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}
    
    products = (
        Produk.objects.select_related("kategori")
        .filter(toko=user.toko)
        .order_by('stok')[:5]  # Get top 5 with lowest stock
    )
    
    result = []
    for product in products:
        result.append({
            "id": product.id,
            "name": product.nama,
            "stock": product.stok,
            "imageUrl": product.foto.url if product.foto else None,
        })
    
    return 200, result

@router.get("/{id}", response={200: ProdukResponseSchema, 404: dict})
def get_produk_by_id(request, id: int):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}
    
    try:
        # Get product by id and check if it belongs to user's toko
        produk = get_object_or_404(Produk, id=id, toko=user.toko)
        return 200, ProdukResponseSchema.from_orm(produk)
    except Exception:
        return 404, {"message": "Produk tidak ditemukan"}


@router.post("/update/{id}", response={200: ProdukResponseSchema, 404: dict, 422: dict})
def update_produk(request, id: int, payload: UpdateProdukSchema, foto: UploadedFile = None):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return 422, {"message": NO_TOKO_MESSAGE}

    try:
        # Get product by id and check if it belongs to user's toko
        produk = get_object_or_404(Produk, id=id, toko=user.toko)

        # Convert payload to dict and filter out None values
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        try:
                if 'harga_modal' in update_data and Decimal(update_data['harga_modal']) > MAX_DECIMAL:
                    return 422, {"message": "Harga modal terlalu besar. Maksimum adalah 99.999.999,99"}
                if 'harga_jual' in update_data and Decimal(update_data['harga_jual']) > MAX_DECIMAL:
                    return 422, {"message": "Harga jual terlalu besar. Maksimum adalah 99.999.999,99"}
        except InvalidOperation:
            return 422, {"message": "Format harga tidak valid."}
        
        # Handle kategori separately as it needs special processing
        if 'kategori' in update_data:
            kategori_name = update_data.pop('kategori')
            kategori_obj, _ = KategoriProduk.objects.get_or_create(
                nama=kategori_name,
                toko=user.toko
            )
            produk.kategori = kategori_obj
        
        # Handle satuan separately to ensure it's added to the Satuan model
        if 'satuan' in update_data:
            satuan_name = update_data.pop('satuan')
            satuan_obj, _ = Satuan.objects.get_or_create(
                nama=satuan_name,
                toko=user.toko
            )
            produk.satuan = satuan_obj.nama
        
        # Update all other fields
        for field, value in update_data.items():
            setattr(produk, field, value)
        
        # Handle the uploaded file (if provided)
        if foto:
            produk.foto = foto

        produk.save()

        return 200, ProdukResponseSchema.from_orm(produk)

    except Exception:
        return 422, {"message": "Gagal memperbarui produk. Pastikan data valid dan produk tersedia."}


@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return {"message": NO_TOKO_MESSAGE}
    
    produk = get_object_or_404(Produk, id=id, toko=user.toko)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}


@router.get("/top-selling/{year}/{month}", response={200: list, 404: dict})
def get_top_selling_products(request, year: int, month: int):
    user_id = request.auth
    user = User.objects.get(id=user_id)
    
    if not user.toko:
        return 404, {"message": NO_TOKO_MESSAGE}
    
    # Define the month period
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get top-selling products for the specified month by querying TransaksiItem
    top_products = (
        TransaksiItem.objects
        .filter(
            transaksi__toko=user.toko,
            transaksi__created_at__gte=start_date,
            transaksi__created_at__lt=end_date,
            transaksi__is_deleted=False,
            transaksi__category="Penjualan Barang"  # Only include actual sales
        )
        .values('product__id', 'product__nama', 'product__foto')
        .annotate(sold=Sum('quantity'))
        .order_by('-sold')[:3]  # Get top 3
    )
    
    result = []
    for product in top_products:
        result.append({
            "id": product['product__id'],
            "name": product['product__nama'],
            "imageUrl": product['product__foto'],
            "sold": product['sold']
        })
    
    return 200, result