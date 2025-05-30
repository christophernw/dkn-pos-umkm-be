import random
from django.db import models
from django.contrib.auth.models import User
from produk.models import Produk
from django.conf import settings
from authentication.models import Toko


class Transaksi(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    # Replace user with toko
    toko = models.ForeignKey(Toko, on_delete=models.CASCADE, related_name="transaksi")
    # Keep track of which user performed the transaction
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_transaksi",
    )
    transaction_type = models.CharField(max_length=20)
    category = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_modal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="Lunas")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            # Generate a unique hexadecimal ID
            hex_chars = "0123456789ABCDEF"
            random_id = "".join(random.choice(hex_chars) for _ in range(6))
            self.id = random_id

            # Ensure uniqueness
            while Transaksi.objects.filter(id=self.id).exists():
                random_id = "".join(random.choice(hex_chars) for _ in range(6))
                self.id = f"#{random_id}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaksi #{self.id} - {self.transaction_type}: {self.category}"


class TransaksiItem(models.Model):
    id = models.AutoField(primary_key=True)
    transaksi = models.ForeignKey(
        Transaksi, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Produk, on_delete=models.CASCADE, related_name="transaksi_items"
    )
    quantity = models.IntegerField()
    harga_jual_saat_transaksi = models.DecimalField(max_digits=10, decimal_places=2)
    harga_modal_saat_transaksi = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item #{self.id} - {self.product.nama} x {self.quantity}"
