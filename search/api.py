from ninja import Router
from produk.schemas import ProdukSchema
from produk.models import Produk

router = Router()

@router.get("/produk", response=list[ProdukSchema])
def search_produk(request, q: str = ""):
    produk_list = Produk.objects.filter(nama__icontains=q)
    return [
        {
            "id": p.id,
            "nama": p.nama,
            "foto": p.foto,
            "harga_modal": p.harga_modal,
            "harga_jual": p.harga_jual,
            "stok": p.stok,
            "satuan": p.satuan,
            "kategori": p.kategori.nama,
        }
        for p in produk_list
    ]
    
