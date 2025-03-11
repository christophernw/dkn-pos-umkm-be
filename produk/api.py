from ninja import File, Form, Router, UploadedFile
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from produk.models import Produk, KategoriProduk
from produk.schemas import ProdukSchema

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

@router.post("/create", response={201: ProdukSchema, 422: dict})
def create_produk(
    request,
    nama: str = Form(...),
    harga_modal: float = Form(...),
    harga_jual: float = Form(...),
    stok: float = Form(...),
    satuan: str = Form(...),
    kategori: str = Form(...),
    foto: UploadedFile = File(None)
):
    if harga_modal < 0 or harga_jual < 0:
        return 422, {"detail": "Harga minus seharusnya invalid"}

    if stok < 0:
        return 422, {"detail": "Stok minus seharusnya invalid"}
    
    kategori_obj, _ = KategoriProduk.objects.get_or_create(nama=kategori)
    
    produk = Produk.objects.create(
        nama=nama,
        foto=foto,
        harga_modal=harga_modal,
        harga_jual=harga_jual,
        stok=stok,
        satuan=satuan,
        kategori=kategori_obj
    )
    
    return 201, ProdukSchema(
        id=produk.id,
        nama=produk.nama,
        foto=produk.foto.url if produk.foto else None,
        harga_modal=float(produk.harga_modal),
        harga_jual=float(produk.harga_jual),
        stok=float(produk.stok),
        satuan=produk.satuan,
        kategori=kategori_obj.nama,
    )
  
@router.delete("/delete/{id}")
def delete_produk(request, id: int):
    produk = get_object_or_404(Produk, id=id)
    produk.delete()
    return {"message": "Produk berhasil dihapus"}
