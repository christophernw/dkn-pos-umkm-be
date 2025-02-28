from ninja import NinjaAPI
from django.http import HttpResponseBadRequest
from api.models import Produk
from api.schemas import ProdukSchema

api = NinjaAPI()

@api.get("/produk", response=list[ProdukSchema])
def get_produk(request, sort: str = None):
    if sort not in [None, "asc", "desc"]:
        return HttpResponseBadRequest("Invalid sort parameter. Use 'asc' or 'desc'.")

    order_by_field = "stok" if sort == "asc" else "-stok"
    produk_list = Produk.objects.select_related("kategori").order_by(order_by_field, "id")  # Pastikan fallback ke id

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
