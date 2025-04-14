from django.db import models
from django.conf import settings

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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Ganti dengan AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name="produk",
        limit_choices_to={"role": "Pemilik"},  
    )
    is_deleted = models.BooleanField(default=False) 
