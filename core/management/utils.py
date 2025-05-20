# core/management/utils.py

import os
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from django.conf import settings

def generate_product_data(category_name, count=5):
    """Generate random product data for a specific category"""
    
    # Define base products by category
    category_products = {
        "Makanan": [
            "Nasi Goreng", "Mie Goreng", "Ayam Goreng", "Sate Ayam", "Bakso", 
            "Gado-gado", "Soto Ayam", "Rendang", "Pecel", "Nasi Padang"
        ],
        "Minuman": [
            "Es Teh", "Es Jeruk", "Kopi Hitam", "Kopi Susu", "Jus Alpukat",
            "Jus Mangga", "Soda Gembira", "Air Mineral", "Teh Botol", "Susu"
        ],
        "Snack": [
            "Keripik Singkong", "Kerupuk Udang", "Kacang Goreng", "Pisang Goreng",
            "Tahu Goreng", "Bakwan", "Tempe Goreng", "Risoles", "Martabak Manis", "Donat"
        ],
        "Bahan Baku": [
            "Tepung Terigu", "Gula Pasir", "Minyak Goreng", "Beras", "Telur", 
            "Bumbu Dapur", "Garam", "Tepung Tapioka", "Cabai", "Bawang"
        ],
        "Pakaian": [
            "Kaos Polos", "Kemeja", "Celana Jeans", "Jaket", "Topi", 
            "Kaos Kaki", "Daster", "Rok", "Celana Pendek", "Piyama"
        ],
        "Elektronik": [
            "Charger HP", "Earphone", "Kabel Data", "Power Bank", "Case HP",
            "Mouse", "Keyboard", "Flash Disk", "Lampu LED", "Adaptor"
        ]
    }
    
    # Default for unknown categories
    default_products = ["Produk A", "Produk B", "Produk C", "Produk D", "Produk E"]
    
    # Get product names based on category, or use default if category unknown
    product_names = category_products.get(category_name, default_products)
    
    # Take random subset if we need fewer products
    if len(product_names) > count:
        product_names = random.sample(product_names, count)
    
    # If we need more products than available in our base list, add variants
    if len(product_names) < count:
        variants = ["Spesial", "Premium", "Super", "Jumbo", "Mini", "Ekonomis"]
        while len(product_names) < count:
            base_product = random.choice(category_products.get(category_name, default_products))
            variant = random.choice(variants)
            new_product = f"{base_product} {variant}"
            if new_product not in product_names:
                product_names.append(new_product)
    
    # Determine price ranges based on category
    price_ranges = {
        "Makanan": (10000, 30000),
        "Minuman": (3000, 15000),
        "Snack": (5000, 20000),
        "Bahan Baku": (5000, 25000),
        "Pakaian": (25000, 150000),
        "Elektronik": (15000, 100000)
    }
    
    default_range = (5000, 50000)
    price_range = price_ranges.get(category_name, default_range)
    
    # Generate full product data
    products = []
    for name in product_names:
        # Generate random modal price within range
        modal = random.randint(price_range[0] // 2, price_range[1] // 2)
        # Generate jual price with a 30-70% markup
        markup = random.uniform(1.3, 1.7)
        jual = int(modal * markup)
        
        # Random stock based on category
        if category_name in ["Bahan Baku", "Minuman"]:
            stok = random.randint(20, 100)
        elif category_name in ["Elektronik", "Pakaian"]:
            stok = random.randint(5, 20)
        else:
            stok = random.randint(10, 50)
        
        # Choose appropriate unit based on category
        if category_name == "Makanan" or category_name == "Minuman":
            satuan = "Porsi" if category_name == "Makanan" else "Gelas"
        elif category_name == "Bahan Baku":
            satuan = random.choice(["Kg", "Gram", "Pack"])
        elif category_name == "Pakaian":
            satuan = "Pcs"
        elif category_name == "Elektronik":
            satuan = "Unit"
        else:
            satuan = random.choice(["Pcs", "Box", "Pack"])
            
        products.append({
            "nama": name,
            "modal": modal,
            "jual": jual,
            "stok": stok,
            "satuan": satuan,
            "kategori": category_name
        })
    
    return products

def generate_transaction_data(products, user, toko, count=10, days_range=30, include_unpaid=True):
    """Generate realistic transaction data using the provided products"""
    
    transactions = []
    
    # Define transaction types and their probability
    transaction_types = [
        {"type": "Pemasukan", "category": "Penjualan Barang", "weight": 50},
        {"type": "Pengeluaran", "category": "Pembelian Stok", "weight": 30},
        {"type": "Pemasukan", "category": "Pendapatan Lain-Lain", "weight": 10},
        {"type": "Pemasukan", "category": "Pendapatan Pinjaman", "weight": 5},
        {"type": "Pengeluaran", "category": "Biaya Operasional", "weight": 15},
        {"type": "Pengeluaran", "category": "Biaya Sewa", "weight": 5},
        {"type": "Pengeluaran", "category": "Biaya Gaji", "weight": 10}
    ]
    
    # Calculate the total weight for weighted random selection
    total_weight = sum(t["weight"] for t in transaction_types)
    
    # Generate transactions
    for i in range(count):
        # Select a transaction type based on weight
        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        selected_type = None
        
        for t in transaction_types:
            cumulative_weight += t["weight"]
            if r <= cumulative_weight:
                selected_type = t
                break
        
        # Generate realistic timestamp within the days range
        days_ago = random.randint(0, days_range)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = timezone.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Determine if this will be an unpaid transaction (for credit sales/purchases)
        is_unpaid = include_unpaid and random.random() < 0.15  # 15% chance of unpaid transaction
        status = "Belum Lunas" if is_unpaid else "Selesai"
        
        # Prepare transaction data
        transaction = {
            "toko": toko,
            "created_by": user,
            "transaction_type": selected_type["type"],
            "category": selected_type["category"],
            "status": status,
            "created_at": timestamp
        }
        
        # For product-related transactions, select products and calculate amounts
        if selected_type["category"] in ["Penjualan Barang", "Pembelian Stok"]:
            # Choose 1-3 products for this transaction
            num_products = random.randint(1, 3)
            selected_products = random.sample(products, min(num_products, len(products)))
            
            items = []
            total_amount = Decimal('0')
            total_modal = Decimal('0')
            
            for product in selected_products:
                if selected_type["category"] == "Penjualan Barang":
                    quantity = random.randint(1, 3)
                    item_total = product.harga_jual * quantity
                    item_modal = product.harga_modal * quantity
                    
                    items.append({
                        "product": product,
                        "quantity": quantity,
                        "harga_jual_saat_transaksi": product.harga_jual,
                        "harga_modal_saat_transaksi": product.harga_modal
                    })
                    
                    total_amount += item_total
                    total_modal += item_modal
                    
                elif selected_type["category"] == "Pembelian Stok":
                    quantity = random.randint(5, 15)
                    item_total = product.harga_modal * quantity
                    
                    items.append({
                        "product": product,
                        "quantity": quantity,
                        "harga_jual_saat_transaksi": 0,
                        "harga_modal_saat_transaksi": product.harga_modal
                    })
                    
                    total_amount += item_total
            
            transaction["items"] = items
            transaction["total_amount"] = total_amount
            transaction["total_modal"] = total_modal if selected_type["category"] == "Penjualan Barang" else Decimal('0')
            transaction["amount"] = total_amount
            
        # For non-product transactions, generate realistic amounts
        else:
            if selected_type["category"] == "Pendapatan Lain-Lain":
                amount = Decimal(str(random.randint(50, 500) * 1000))
            elif selected_type["category"] == "Pendapatan Pinjaman":
                amount = Decimal(str(random.randint(1000, 5000) * 1000))
            elif selected_type["category"] == "Biaya Operasional":
                amount = Decimal(str(random.randint(50, 300) * 1000))
            elif selected_type["category"] == "Biaya Sewa":
                amount = Decimal(str(random.randint(500, 2000) * 1000))
            elif selected_type["category"] == "Biaya Gaji":
                amount = Decimal(str(random.randint(1000, 3000) * 1000))
            else:
                amount = Decimal(str(random.randint(100, 1000) * 1000))
            
            transaction["total_amount"] = amount
            transaction["total_modal"] = Decimal('0')
            transaction["amount"] = amount
            transaction["items"] = []
        
        transactions.append(transaction)
    
    # Sort by timestamp
    transactions.sort(key=lambda x: x["created_at"])
    
    return transactions

def save_rollback_info(seed_id, file_path, data):
    """Save rollback information to a file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Convert any non-serializable objects to strings
    serializable_data = {}
    for key, value in data.items():
        if isinstance(value, (datetime, Decimal)):
            serializable_data[key] = str(value)
        else:
            serializable_data[key] = value
    
    with open(file_path, 'w') as f:
        json.dump({
            'seed_id': seed_id,
            'timestamp': timezone.now().isoformat(),
            'data': serializable_data
        }, f, indent=2)