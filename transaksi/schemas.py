from ninja import Schema
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class TransaksiItemRequest(Schema):
    product_id: int
    quantity: float
    harga_jual_saat_transaksi: float
    harga_modal_saat_transaksi: float
    
    @field_validator("quantity")
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity harus lebih dari 0")
        return v

class CreateTransaksiRequest(Schema):
    transaction_type: str
    category: str
    total_amount: float
    total_modal: float = 0
    amount: float
    items: List[TransaksiItemRequest] = []
    status: str = "Selesai"
    
    @field_validator("items")
    def validate_items(cls, v, values):
        if "category" in values.data and values.data["category"] == "Penjualan Barang" and not v:
            raise ValueError("Minimal satu item harus ditambahkan untuk penjualan barang")
        return v

class TransaksiItemResponse(Schema):
    id: int
    product_id: int
    product_name: str
    product_image_url: Optional[str]
    quantity: int
    harga_jual_saat_transaksi: float
    harga_modal_saat_transaksi: float
    subtotal: float
    
    @classmethod
    def from_orm(cls, item):
        return cls(
            id=item.id,
            product_id=item.product.id,
            product_name=item.product.nama,
            product_image_url=item.product.foto.url if item.product.foto else None,
            quantity=float(item.quantity),
            harga_jual_saat_transaksi=float(item.harga_jual_saat_transaksi),
            harga_modal_saat_transaksi=float(item.harga_modal_saat_transaksi),
            subtotal=float(item.quantity * item.harga_jual_saat_transaksi)
        )

class TransaksiResponse(Schema):
    id: str
    transaction_type: str
    category: str
    total_amount: float
    total_modal: float
    amount: float
    items: List[TransaksiItemResponse]
    status: str
    is_deleted: bool
    created_at: datetime
    
    @classmethod
    def from_orm(cls, transaksi):
        return cls(
            id=transaksi.id,
            transaction_type=transaksi.transaction_type,
            category=transaksi.category,
            total_amount=float(transaksi.total_amount),
            total_modal=float(transaksi.total_modal),
            amount=float(transaksi.amount),
            items=[TransaksiItemResponse.from_orm(item) for item in transaksi.items.all()],
            status=transaksi.status,
            is_deleted=transaksi.is_deleted,
            created_at=transaksi.created_at,
        )

class PaginatedTransaksiResponse(Schema):
    items: List[TransaksiResponse]
    total: int
    page: int
    per_page: int
    total_pages: int