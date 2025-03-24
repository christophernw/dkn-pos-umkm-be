from ninja import Router
from django.shortcuts import get_object_or_404
from typing import List
from .models import Pemasukan, Pengeluaran, Produk, Transaksi
from .schemas import (
    PemasukanCreate, PemasukanRead, 
    PengeluaranCreate, PengeluaranRead
)

router = Router()


@router.post("/pemasukan/create", response=PemasukanRead)
def create_pemasukan(request, payload: PemasukanCreate):
    
    transaksi = Transaksi.objects.create(
        status=payload.status,
        catatan=payload.catatan,
        namaPelanggan=payload.namaPelanggan,
        nomorTeleponPelanggan=payload.nomorTeleponPelanggan,
        foto=payload.foto,
    )
    
    transaksi.save()
    transaksi.daftarProduk.set(Produk.objects.filter(id__in=payload.daftarProduk))
    
    pemasukan = Pemasukan.objects.create(
        transaksi=transaksi,
        kategori=payload.kategori,
        totalPemasukan=payload.totalPemasukan,
        hargaModal=payload.hargaModal,
    )
    
    return PemasukanRead.from_orm(pemasukan)


@router.post("/pengeluaran/create", response=PengeluaranRead)
def create_pengeluaran(request, payload: PengeluaranCreate):
    
    transaksi = Transaksi.objects.create(
        status=payload.status,
        catatan=payload.catatan,
        namaPelanggan=payload.namaPelanggan,
        nomorTeleponPelanggan=payload.nomorTeleponPelanggan,
        foto=payload.foto,
    )
    
    transaksi.daftarProduk.set(Produk.objects.filter(id__in=payload.daftarProduk))
    
    pengeluaran = Pengeluaran.objects.create(
        transaksi=transaksi,
        kategori=payload.kategori,
        totalPengeluaran=payload.totalPengeluaran,
    )
    
    return PengeluaranRead.from_orm(pengeluaran)


@router.get("/pemasukan/daftar", response=List[PemasukanRead])
def read_pemasukan(request):
    pemasukan_list = Pemasukan.objects.all()
    return [PemasukanRead.from_orm(p) for p in pemasukan_list]

@router.get("/pengeluaran/daftar", response=List[PengeluaranRead])
def read_pengeluaran(request):
    pengeluaran_list = Pengeluaran.objects.all()
    return [PengeluaranRead.from_orm(p) for p in pengeluaran_list]

@router.get("/pemasukan/{pemasukan_id}", response=PemasukanRead)
def read_pemasukan_by_id(request, pemasukan_id: int):
    pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)
    return PemasukanRead.from_orm(pemasukan)


@router.get("/pengeluaran/{pengeluaran_id}", response=PengeluaranRead)
def read_pengeluaran_by_id(request, pengeluaran_id: int):
    pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)
    return PengeluaranRead.from_orm(pengeluaran)

@router.delete("/pengeluaran/{pengeluaran_id}/delete", response={200: dict, 404: dict})
def delete_pengeluaran(request, pengeluaran_id: int):
    try:
        pengeluaran = get_object_or_404(Pengeluaran, id=pengeluaran_id)
        

        transaksi = pengeluaran.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pengeluaran.delete()
        
        return 200, {"message": "Pengeluaran deleted successfully"}
    except:
        return 404, {"error": "Pengeluaran not found"}
    
@router.delete("/pemasukan/{pemasukan_id}/delete", response={200: dict, 404: dict})
def delete_pemasukan(request, pemasukan_id: int):
    try:
        pemasukan = get_object_or_404(Pemasukan, id=pemasukan_id)
        
        transaksi = pemasukan.transaksi
        transaksi.isDeleted = True
        transaksi.save()

        pemasukan.delete()
        
        return 200, {"message": "Pemasukan deleted successfully"}
    except:
        return 404, {"error": "Pemasukan not found"}