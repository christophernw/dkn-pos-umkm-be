from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class StatusTransaksiEnum(str, Enum):
    LUNAS = "LUNAS"
    BELUM_LUNAS = "BELUM_LUNAS"


class KategoriPemasukanEnum(str, Enum):
    PENJUALAN = "PENJUALAN"
    PENAMBAHAN_MODAL = "PENAMBAHAN_MODAL"
    PENDAPATAN_DI_LUAR_USAHA = "PENDAPATAN_DI_LUAR_USAHA"
    PENDAPATAN_JASA_ATAU_KOMISI = "PENDAPATAN_JASA_ATAU_KOMISI"
    TERIMA_PINJAMAN = "TERIMA_PINJAMAN"
    PENAGIHAN_UTANG_ATAU_CICILAN = "PENAGIHAN_UTANG_ATAU_CICILAN"
    PENDAPATAN_LAIN = "PENDAPATAN_LAIN"


class KategoriPengeluaranEnum(str, Enum):
    PEMBELIAN_STOK = "PEMBELIAN_STOK"
    PENGELUARAN_DI_LUAR_USAHA = "PENGELUARAN_DI_LUAR_USAHA"
    PEMBELIAN_BAHAN_BAKU = "PEMBELIAN_BAHAN_BAKU"
    BIAYA_OPERASIONAL = "BIAYA_OPERASIONAL"
    GAJI_ATAU_BONUS_KARYAWAN = "GAJI_ATAU_BONUS_KARYAWAN"
    PEMBERIAN_UTANG = "PEMBERIAN_UTANG"
    PEMBAYARAN_UTANG_ATAU_CICILAN = "PEMBAYARAN_UTANG_ATAU_CICILAN"
    PENGELUARAN_LAIN = "PENGELUARAN_LAIN"


class ProdukBase(BaseModel):
    id: int
    nama: str
    foto: Optional[str]
    harga_modal: float
    harga_jual: float
    stok: float
    satuan: str
    kategori: str

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


class TransaksiRead(BaseModel):
    id: int
    status: StatusTransaksiEnum
    catatan: Optional[str] = None
    namaPelanggan: Optional[str] = None
    nomorTeleponPelanggan: Optional[str] = None
    foto: Optional[str] = None
    daftarProduk: List[ProdukBase]
    tanggalTransaksi: datetime
    isDeleted: bool

    @classmethod
    def from_orm(cls, transaksi):

        return cls(
            id=transaksi.id,
            status=transaksi.status,
            catatan=transaksi.catatan,
            namaPelanggan=transaksi.namaPelanggan,
            nomorTeleponPelanggan=transaksi.nomorTeleponPelanggan,
            daftarProduk=[ProdukBase.from_orm(p) for p in transaksi.daftarProduk.all()],
            tanggalTransaksi=transaksi.tanggalTransaksi,
            isDeleted=transaksi.isDeleted,
            foto=transaksi.foto.url if transaksi.foto else None,
        )


class PemasukanRead(BaseModel):
    id: int
    transaksi: TransaksiRead
    kategori: KategoriPemasukanEnum
    totalPemasukan: float
    hargaModal: float
    tanggalTransaksi: datetime

    @classmethod
    def from_orm(cls, pemasukan):
        return cls(
            id=pemasukan.id,
            transaksi=TransaksiRead.from_orm(pemasukan.transaksi),
            kategori=pemasukan.kategori,
            totalPemasukan=pemasukan.totalPemasukan,
            hargaModal=float(pemasukan.hargaModal),
            tanggalTransaksi=pemasukan.transaksi.tanggalTransaksi,
        )


class PengeluaranRead(BaseModel):
    id: int
    transaksi: TransaksiRead
    kategori: KategoriPengeluaranEnum
    totalPengeluaran: float
    tanggalTransaksi: datetime

    @classmethod
    def from_orm(cls, pengeluaran):

        return cls(
            id=pengeluaran.id,
            transaksi=TransaksiRead.from_orm(pengeluaran.transaksi),
            kategori=pengeluaran.kategori,
            totalPengeluaran=pengeluaran.totalPengeluaran,
            tanggalTransaksi=pengeluaran.transaksi.tanggalTransaksi,
        )


class PemasukanCreate(BaseModel):
    status: StatusTransaksiEnum
    catatan: Optional[str] = None
    namaPelanggan: Optional[str] = None
    nomorTeleponPelanggan: Optional[str] = None
    foto: Optional[str] = None
    daftarProduk: List[int]
    kategori: KategoriPemasukanEnum
    totalPemasukan: float
    hargaModal: float


class PengeluaranCreate(BaseModel):
    status: StatusTransaksiEnum
    catatan: Optional[str] = None
    namaPelanggan: Optional[str] = None
    nomorTeleponPelanggan: Optional[str] = None
    foto: Optional[str] = None
    daftarProduk: List[int]
    kategori: KategoriPengeluaranEnum
    totalPengeluaran: float


class TransaksiUpdate(BaseModel):
    status: Optional[StatusTransaksiEnum] = None
    catatan: Optional[str] = None
    namaPelanggan: Optional[str] = None
    nomorTeleponPelanggan: Optional[str] = None
    foto: Optional[str] = None
    daftarProduk: Optional[List[int]] = None


from typing import List


class PaginatedPemasukanResponseSchema(BaseModel):
    items: List[PemasukanRead]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    # Add these new schemas to transaksi/schemas.py
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from enum import Enum

class LaporanPeriodeEnum(str, Enum):
    HARIAN = "HARIAN"
    MINGGUAN = "MINGGUAN"
    BULANAN = "BULANAN"
    TAHUNAN = "TAHUNAN"
    KUSTOM = "KUSTOM"

class LaporanRequest(BaseModel):
    periode: LaporanPeriodeEnum
    tanggal_mulai: Optional[date] = None
    tanggal_akhir: Optional[date] = None
    
class LaporanPeriodeItem(BaseModel):
    periode: str
    total: float
    count: int
    
class LaporanProdukItem(BaseModel):
    id: int
    nama: str
    total_terjual: int
    total_pendapatan: float
    
class LaporanPenjualanResponse(BaseModel):
    total_penjualan: float
    jumlah_transaksi: int
    periode_data: List[LaporanPeriodeItem]
    
class LaporanPengeluaranResponse(BaseModel):
    total_pengeluaran: float
    jumlah_transaksi: int
    periode_data: List[LaporanPeriodeItem]
    
class LaporanLabaRugiItem(BaseModel):
    periode: str
    total_penjualan: float
    total_pengeluaran: float
    laba_rugi: float
    
class LaporanLabaRugiResponse(BaseModel):
    total_penjualan: float
    total_pengeluaran: float
    laba_rugi: float
    periode_data: List[LaporanLabaRugiItem]
    
class LaporanProdukResponse(BaseModel):
    total_produk_terjual: int
    total_pendapatan: float
    produk_data: List[LaporanProdukItem]
    
# Add these at the end of transaksi/schemas.py

class UserInfo(BaseModel):
    id: int
    username: str
    email: str

class AllTransactionSchema(BaseModel):
    id: int
    type: str  # "pemasukan" or "pengeluaran"
    transaksi_id: int
    status: str
    catatan: Optional[str] = None
    namaPelanggan: Optional[str] = None
    nomorTeleponPelanggan: Optional[str] = None
    tanggalTransaksi: str
    user: UserInfo
    kategori: str
    total: float