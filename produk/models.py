from django.db import models
from django.conf import settings

from authentication.models import Toko

class KategoriProduk(models.Model):
    nama = models.CharField(max_length=255)

class Produk(models.Model):
    id = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=255)
    foto = models.ImageField(upload_to='produk/')
    harga_modal = models.DecimalField(max_digits=10, decimal_places=2)
    harga_jual = models.DecimalField(max_digits=10, decimal_places=2)
    stok = models.IntegerField()
    satuan = models.CharField(max_length=10)
    kategori = models.ForeignKey(KategoriProduk, on_delete=models.CASCADE, related_name="produk")
    
    # Replace user with toko
    toko = models.ForeignKey(
        Toko,
        on_delete=models.CASCADE,
        related_name="produk",
    )