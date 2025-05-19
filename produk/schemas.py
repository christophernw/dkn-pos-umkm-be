from ninja import Schema, UploadedFile
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ProdukResponseSchema(Schema):
    id: int
    nama: str = Field(max_length=100)
    foto: Optional[str]
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str = Field(max_length=30)
    kategori: str = Field(max_length=50)

    @classmethod
    def from_orm(cls, produk):

        return cls(
            id=produk.id,
            nama=produk.nama,
            foto=produk.foto.url if produk.foto else None,
            harga_modal=float(produk.harga_modal),
            harga_jual=float(produk.harga_jual),
            stok=float(produk.stok),
            satuan=produk.satuan,
            kategori=produk.kategori.nama,
        )


class CreateProdukSchema(BaseModel):
    nama: str = Field(max_length=100)
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str = Field(max_length=30)
    kategori: str = Field(max_length=50)

    @field_validator("harga_modal")
    def validate_harga_modal(cls, v):
        if v < 0:
            raise ValueError("Harga modal minus seharusnya invalid")
        return v

    @field_validator("harga_jual")
    def validate_harga_jual(cls, v):
        if v < 0:
            raise ValueError("Harga jual minus seharusnya invalid")
        return v

    @field_validator("stok")
    def validate_stok(cls, v):
        if v < 0:
            raise ValueError("Stok minus seharusnya invalid")
        return v

class UpdateProdukSchema(Schema):
    nama: Optional[str]
    harga_modal: Optional[float]
    harga_jual: Optional[float]
    stok: Optional[float]
    satuan: Optional[str]
    kategori: Optional[str]

    @field_validator("harga_modal")
    def validate_harga_modal(cls, v):
        if v is not None and v < 0:
            raise ValueError("Harga modal minus tidak valid")
        return v

    @field_validator("harga_jual")
    def validate_harga_jual(cls, v):
        if v is not None and v < 0:
            raise ValueError("Harga jual minus tidak valid")
        return v

    @field_validator("stok")
    def validate_stok(cls, v):
        if v is not None and v < 0:
            raise ValueError("Stok minus tidak valid")
        return v

class PaginatedResponseSchema(Schema):
    items: List[ProdukResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int
