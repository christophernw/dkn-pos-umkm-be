from ninja import Router
from django.shortcuts import get_object_or_404
from api.models import Product
from api.serializers import ProductUpdateSchema
from django.http import JsonResponse


router = Router()

@router.get("/ping")
def ping(request):
    return {"message": "pong"}

@router.put("/products/{product_id}")
def update_product(request, product_id: int, data: ProductUpdateSchema):
    product = get_object_or_404(Product, id=product_id)

    # Validasi input
    if data.price < 0 or data.stock < 0:
        return JsonResponse({"error": "Harga dan stok harus positif"}, status=400)

    # Update data produk
    for attr, value in data.dict().items():
        setattr(product, attr, value)
    product.save()

    return JsonResponse({
        "message": "Produk berhasil diperbarui",
        "product": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "stock": product.stock,
            "category": product.category,
        }
    })
