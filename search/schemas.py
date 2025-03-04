from ninja import Schema
from typing import Optional

class ProdukSchema(Schema):
    id: int
    nama: str
    foto: Optional[str]
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str
    kategori: str