from ninja import Router
from django.shortcuts import get_object_or_404
from .schemas import ProdukSchema
from .models import Produk

router = Router()

@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    produk = get_object_or_404(Produk, id=id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}