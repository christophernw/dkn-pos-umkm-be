from ninja import Router
from silk.profiling.profiler import silk_profile
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.conf import settings
from django.db.models import Prefetch 
from typing import List, Optional
from .models import Pemasukan, Pengeluaran, Produk, Transaksi
from .schemas import (
    PemasukanCreate, PemasukanRead, 
    PengeluaranCreate, PengeluaranRead,
    StatusTransaksiEnum
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
    
    produk_list = Produk.objects.filter(id__in=payload.daftarProduk)
    transaksi.daftarProduk.set(produk_list)
    
    if payload.kategori == "PEMBELIAN_STOK":
        total_pengeluaran = sum(produk.harga_modal for produk in produk_list)
    else:
        total_pengeluaran = payload.totalPengeluaran
        
    transaksi.save()
    
    pengeluaran = Pengeluaran.objects.create(
        transaksi=transaksi,
        kategori=payload.kategori,
        totalPengeluaran=total_pengeluaran,
    )
    
    return PengeluaranRead.from_orm(pengeluaran)


@router.get("/pengeluaran/daftar", response=List[PengeluaranRead])
@silk_profile(name="Profiling Daftar Pemasukan")
def read_pengeluaran(request, status: Optional[StatusTransaksiEnum] = None):
    cache_key = f"pengeluaran_list:{status or 'all'}"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        print("Cache hit! Returning cached data")
        return cached_data
    
    print("Cache miss! Fetching from database")

    pengeluaran_list = Pengeluaran.objects.filter(transaksi__isDeleted=False)
    
    if status:
        pengeluaran_list = pengeluaran_list.filter(transaksi__status=status)
    
    pengeluaran_list = pengeluaran_list.prefetch_related(
        'transaksi', 
        'transaksi__daftarProduk'
    )   
    result = [PengeluaranRead.from_orm(p) for p in pengeluaran_list]
    
    cache.set(cache_key, result, timeout=settings.CACHE_TTL)
    
    return result

@router.get("/pemasukan/daftar", response=List[PemasukanRead])
@silk_profile(name="Profiling Daftar Pemasukan") 
def read_pemasukan(request, status: Optional[StatusTransaksiEnum] = None):
    cache_key = f"pemasukan_list:{status or 'all'}"
    
    # Cek cache dulu
    cached_data = cache.get(cache_key)
    if cached_data:
        print("Cache hit! Returning cached data")
        return cached_data
    
    print("Cache miss! Fetching from database")

    # Buat query dasar yang efisien
    pemasukan_list = (
        Pemasukan.objects
        .filter(transaksi__isDeleted=False)
        .filter(transaksi__status=status) if status else 
        Pemasukan.objects.filter(transaksi__isDeleted=False)
    )
    
    # Optimasi relasi
    pemasukan_list = (
        pemasukan_list
        # Gunakan select_related untuk foreign key (transaksi)
        .select_related('transaksi')
        # Gunakan prefetch_related untuk many-to-many (daftarProduk)
        .prefetch_related(
            # Prefetch dengan queryset kustom untuk optimasi lebih lanjut
            Prefetch(
                'transaksi__daftarProduk',
                queryset=Produk.objects.select_related('kategori')  # Prefetch kategori juga
            )
        )
    )
    
    # Gunakan iterator untuk mengoptimalkan memori saat mengambil data banyak
    result = [
        PemasukanRead.from_orm(p) 
        for p in pemasukan_list.iterator(chunk_size=200)
    ]
    
    cache.set(cache_key, result, timeout=settings.CACHE_TTL)
    
    return result

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