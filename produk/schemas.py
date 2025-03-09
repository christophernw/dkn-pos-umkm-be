from ninja import Schema
from typing import List, Optional

class ProdukSchema(Schema):
    id: int
    nama: str
    foto: Optional[str]
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str
    kategori: str

class CreateProdukSchema(Schema):
    nama: str
    foto: Optional[str] = None
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str
    kategori: str

class PaginatedResponseSchema(Schema):
    items: List[ProdukSchema]
    total: int
    total_pages: int
    current_page: int