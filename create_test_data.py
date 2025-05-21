# create_financial_data.py
from authentication.models import User, Toko
from transaksi.models import Transaksi, TransaksiItem
from produk.models import Produk
from decimal import Decimal
import random
from datetime import datetime, timedelta
import pytz

# Get user and toko
user = User.objects.first()
toko = user.toko

# Get or create a few products to use in transactions
products = list(Produk.objects.filter(toko=toko)[:5])
if not products:
    # Create some products if none exist
    categories = list(toko.kategori.all())
    if not categories:
        from produk.models import KategoriProduk
        cat = KategoriProduk.objects.create(nama="Test Category", toko=toko)
        categories = [cat]
    
    for i in range(5):
        p = Produk.objects.create(
            nama=f"Test Product {i}",
            harga_modal=Decimal("10000"),
            harga_jual=Decimal("15000"),
            stok=100,
            satuan="Pcs",
            kategori=random.choice(categories),
            toko=toko
        )
        products.append(p)

# Create transactions over the past 30 days
now = datetime.now(pytz.UTC)
transaction_types = ["pemasukan", "pengeluaran"]
categories = ["Penjualan Barang", "Pembelian Stok", "Pendapatan Lain-Lain", "Biaya Operasional"]

# Create 100 transactions with items
for i in range(100):
    # Random date in the past 30 days
    days_ago = random.randint(0, 30)
    trans_date = now - timedelta(days=days_ago)
    
    # Determine transaction type and category
    trans_type = random.choice(transaction_types)
    if trans_type == "pemasukan":
        category = categories[0] if random.random() > 0.3 else categories[2]  # Mostly sales
    else:
        category = categories[1] if random.random() > 0.3 else categories[3]  # Mostly stock purchases
    
    # Create transaction
    total_amount = Decimal(random.randint(10000, 1000000))
    total_modal = Decimal(random.randint(5000, 500000)) if trans_type == "pemasukan" else Decimal("0")
    
    trans = Transaksi.objects.create(
        toko=toko,
        created_by=user,
        transaction_type=trans_type,
        category=category,
        total_amount=total_amount,
        total_modal=total_modal,
        amount=total_amount,
        status=random.choice(["Selesai", "Belum Lunas"]),
        created_at=trans_date
    )
    
    # Create 1-5 items for this transaction
    if category in ["Penjualan Barang", "Pembelian Stok"]:
        num_items = random.randint(1, 5)
        for j in range(num_items):
            product = random.choice(products)
            quantity = random.randint(1, 10)
            
            TransaksiItem.objects.create(
                transaksi=trans,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=product.harga_jual,
                harga_modal_saat_transaksi=product.harga_modal
            )

print(f"Created 100 transactions with items over the past 30 days")