from django.contrib import admin
from .models import Transaksi, Pemasukan, Pengeluaran

# Register your models here.
admin.site.register(Transaksi)
admin.site.register(Pemasukan)
admin.site.register(Pengeluaran)