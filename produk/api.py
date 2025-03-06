from ninja import Router
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from produk.models import Produk
from produk.schemas import ProdukSchema

router = Router()

@router.get("", response=list[ProdukSchema])  # HAPUS "produk" biar langsung pakai prefix dari add_router
def get_produk(request, sort: str = None):
    if sort not in [None, "asc", "desc"]:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")

    order_by_field = "stok" if sort == "asc" else "-stok"
    produk_list = Produk.objects.select_related("kategori").order_by(order_by_field, "id")

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

@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    produk = get_object_or_404(Produk, id=id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}
