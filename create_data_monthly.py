# create_monthly_data.py
from authentication.models import User, Toko
from transaksi.models import Transaksi
from decimal import Decimal
import random
from datetime import datetime, timedelta
import pytz

# Get user and toko
user = User.objects.first()
toko = user.toko

# Create transactions over the past 3 months
now = datetime.now(pytz.UTC)
transaction_types = ["pemasukan", "pengeluaran"]
categories = ["Penjualan Barang", "Pembelian Stok", "Pendapatan Lain-Lain", "Biaya Operasional"]

# Create 200 transactions spread over 3 months
for i in range(200):
    # Random date in the past 90 days
    days_ago = random.randint(0, 90)
    trans_date = now - timedelta(days=days_ago)
    
    # Determine transaction type
    trans_type = random.choice(transaction_types)
    
    # Make categories appropriate for transaction type
    if trans_type == "pemasukan":
        category = random.choice([categories[0], categories[2]])  # Sales or Other Income
    else:
        category = random.choice([categories[1], categories[3]])  # Stock Purchase or Operational
    
    # Create transaction (without items for simplicity)
    total_amount = Decimal(random.randint(10000, 1000000))
    
    Transaksi.objects.create(
        toko=toko,
        created_by=user,
        transaction_type=trans_type,
        category=category,
        total_amount=total_amount,
        total_modal=Decimal("0"),
        amount=total_amount,
        status="Selesai",
        created_at=trans_date
    )

print(f"Created 200 transactions over the past 3 months")