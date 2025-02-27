from ninja import NinjaAPI
from api.models import Produk
from api.schemas import ProdukSchema

api = NinjaAPI()

@api.get("/produk", response=list[ProdukSchema])
def get_produk(request):
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
        for p in Produk.objects.select_related("kategori").order_by("id")
    ]