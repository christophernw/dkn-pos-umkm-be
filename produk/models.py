from django.db import models
from django.conf import settings

from authentication.models import Toko

class KategoriProduk(models.Model):
    nama = models.CharField(max_length=255)
    toko = models.ForeignKey("authentication.Toko", on_delete=models.CASCADE, related_name="kategori", null=True)

    class Meta:
        unique_together = ("nama", "toko")  # Ensure no duplicate names within the same shop

    def __str__(self):
        return self.nama

class Satuan(models.Model):
    nama = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.nama

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