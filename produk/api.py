from ninja import Router
from django.http import HttpResponseBadRequest
from produk.models import Produk, KategoriProduk
from produk.schemas import ProdukSchema, CreateProdukSchema

router = Router()

@router.get("", response=list[ProdukSchema])
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

create_router = Router()

@create_router.post("", response={201: ProdukSchema})
def create_produk(request, payload: CreateProdukSchema):
    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=payload.kategori)
    
    produk = Produk.objects.create(
        nama=payload.nama,
        foto=payload.foto,
        harga_modal=payload.harga_modal,
        harga_jual=payload.harga_jual,
        stok=payload.stok,
        satuan=payload.satuan,
        kategori=kategori_obj
    )
    
    return ProdukSchema(
        id=produk.id,
        nama=produk.nama,
        foto=produk.foto,
        harga_modal=float(produk.harga_modal),
        harga_jual=float(produk.harga_jual),
        stok=float(produk.stok),
        satuan=produk.satuan,
        kategori=kategori_obj.nama,
    )
