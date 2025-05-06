from django.contrib import admin
from .models import KategoriProduk, Produk, Satuan

# Register your models here.
admin.site.register(KategoriProduk)
admin.site.register(Produk)
admin.site.register(Satuan)  # Register the new model