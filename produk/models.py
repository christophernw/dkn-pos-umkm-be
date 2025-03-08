from django.db import models

from django.db import models

class KategoriProduk(models.Model):
    nama = models.CharField(max_length=255)

    def __str__(self):
        return self.nama

class Produk(models.Model):
    id = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=255)
    foto = models.ImageField(upload_to='produk/')
    harga_modal = models.DecimalField(max_digits=10, decimal_places=2)
    harga_jual = models.DecimalField(max_digits=10, decimal_places=2)
    stok = models.DecimalField(max_digits=10, decimal_places=3)
    satuan = models.CharField(max_length=10)
    kategori = models.ForeignKey(KategoriProduk, on_delete=models.CASCADE, related_name="produk")

    def __str__(self):
        return self.nama
