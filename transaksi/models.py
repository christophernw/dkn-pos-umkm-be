from django.db import models
from django.contrib.auth.models import User
from produk.models import Produk

class StatusTransaksi(models.TextChoices):
    LUNAS = 'LUNAS', 'Lunas'
    BELUM_LUNAS = 'BELUM_LUNAS', 'Belum Lunas'

class KategoriPemasukan(models.TextChoices):
    PENJUALAN = 'PENJUALAN', 'Penjualan'
    PENAMBAHAN_MODAL = 'PENAMBAHAN_MODAL', 'Penambahan Modal'
    PENDAPATAN_DI_LUAR_USAHA = 'PENDAPATAN_DI_LUAR_USAHA', 'Pendapatan Di Luar Usaha'
    PENDAPATAN_JASA_ATAU_KOMISI = 'PENDAPATAN_JASA_ATAU_KOMISI', 'Pendapatan Jasa Atau Komisi'
    TERIMA_PINJAMAN = 'TERIMA_PINJAMAN', 'Terima Pinjaman'
    PENAGIHAN_UTANG_ATAU_CICILAN = 'PENAGIHAN_UTANG_ATAU_CICILAN', 'Penagihan Utang Atau Cicilan'
    PENDAPATAN_LAIN = 'PENDAPATAN_LAIN', 'Pendapatan Lain'

class KategoriPengeluaran(models.TextChoices):
    PEMBELIAN_STOK = 'PEMBELIAN_STOK', 'Pembelian Stok'
    PENGELUARAN_DI_LUAR_USAHA = 'PENGELUARAN_DI_LUAR_USAHA', 'Pengeluaran Di Luar Usaha'
    PEMBELIAN_BAHAN_BAKU = 'PEMBELIAN_BAHAN_BAKU', 'Pembelian Bahan Baku'
    BIAYA_OPERASIONAL = 'BIAYA_OPERASIONAL', 'Biaya Operasional'
    GAJI_ATAU_BONUS_KARYAWAN = 'GAJI_ATAU_BONUS_KARYAWAN', 'Gaji Atau Bonus Karyawan'
    PEMBERIAN_UTANG = 'PEMBERIAN_UTANG', 'Pemberian Utang'
    PEMBAYARAN_UTANG_ATAU_CICILAN = 'PEMBAYARAN_UTANG_ATAU_CICILAN', 'Pembayaran Utang Atau Cicilan'
    PENGELUARAN_LAIN = 'PENGELUARAN_LAIN', 'Pengeluaran Lain'

class Transaksi(models.Model):
    id = models.AutoField(primary_key=True)
    daftarProduk = models.ManyToManyField(Produk, related_name='transaksi')
    status = models.CharField(max_length=20, choices=StatusTransaksi.choices)
    tanggalTransaksi = models.DateTimeField(auto_now_add=True)
    isDeleted = models.BooleanField(default=False)
    foto = models.ImageField(upload_to='transaksi/', blank=True, null=True)
    catatan = models.TextField(blank=True, null=True)
    namaPelanggan = models.CharField(max_length=255, blank=True, null=True)
    nomorTeleponPelanggan = models.CharField(max_length=15, blank=True, null=True)

class Pemasukan(models.Model):
    transaksi = models.OneToOneField(Transaksi, on_delete=models.CASCADE, related_name='pemasukan')
    kategori = models.CharField(max_length=50, choices=KategoriPemasukan.choices)
    totalPemasukan = models.FloatField()
    hargaModal = models.FloatField()

class Pengeluaran(models.Model):
    transaksi = models.OneToOneField(Transaksi, on_delete=models.CASCADE, related_name='pengeluaran')
    kategori = models.CharField(max_length=50, choices=KategoriPengeluaran.choices)
    totalPengeluaran = models.FloatField()