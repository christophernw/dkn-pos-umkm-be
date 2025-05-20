# core/management/commands/seed_database.py

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from django.utils import timezone

from authentication.models import User, Toko, Invitation
from produk.models import Produk, KategoriProduk, Satuan
from transaksi.models import Transaksi, TransaksiItem
from laporan.models import ArusKasReport, DetailArusKas

class Command(BaseCommand):
    help = 'Seeds the database with sample data for testing and development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            default='local',
            choices=['local', 'server', 'production'],
            help='Seeding mode: local (minimal data), server (well-defined), production (with rollback)'
        )
        parser.add_argument(
            '--email', 
            type=str, 
            help='Email of the user to associate the seed data with'
        )
        parser.add_argument(
            '--clean', 
            action='store_true', 
            help='Clean existing data before seeding'
        )
        parser.add_argument(
            '--rollback-id', 
            type=str,
            help='ID of a previous seeding operation to rollback (production mode only)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        mode = options['mode']
        email = options.get('email')
        clean = options.get('clean', False)
        rollback_id = options.get('rollback_id')

        if mode == 'production' and rollback_id:
            self.rollback_seeding(rollback_id)
            return

        if not email:
            if mode == 'production':
                raise CommandError('Email is required for production seeding')
            email = 'demo@example.com'  # Default email for non-production modes

        # Generate a unique seed ID for tracking and potential rollback
        seed_id = f"seed_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        if clean:
            self.stdout.write(self.style.WARNING('Cleaning existing data...'))
            self.clean_data(email)
        
        self.stdout.write(self.style.SUCCESS(f'Starting {mode} seeding with ID: {seed_id}'))
        
        # Create or get user and toko
        user, toko = self.create_user_and_toko(email, seed_id)
        
        # Seed data based on mode
        if mode == 'local':
            self.seed_minimal_data(user, toko, seed_id)
        elif mode == 'server':
            self.seed_defined_data(user, toko, seed_id)
        elif mode == 'production':
            self.seed_production_data(user, toko, seed_id)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded the database in {mode} mode'))
        self.stdout.write(self.style.SUCCESS(f'Seed ID: {seed_id} (save for rollback if needed)'))

    def clean_data(self, email):
        """Remove existing data for the specified email"""
        try:
            user = User.objects.get(email=email)
            if user.toko:
                toko_id = user.toko.id
                
                # Delete related data
                TransaksiItem.objects.filter(transaksi__toko_id=toko_id).delete()
                Transaksi.objects.filter(toko_id=toko_id).delete()
                Produk.objects.filter(toko_id=toko_id).delete()
                KategoriProduk.objects.filter(toko_id=toko_id).delete()
                DetailArusKas.objects.filter(report__toko_id=toko_id).delete()
                ArusKasReport.objects.filter(toko_id=toko_id).delete()
                Invitation.objects.filter(toko_id=toko_id).delete()
                
                # Don't delete the toko or user, just their data
                self.stdout.write(self.style.SUCCESS(f'Cleaned data for user {email}'))
            else:
                self.stdout.write(self.style.WARNING(f'User {email} has no associated shop'))
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'User {email} not found, nothing to clean'))

    def create_user_and_toko(self, email, seed_id):
        """Create or get a user and their toko"""
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'is_active': True,
                'role': 'Pemilik',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new user: {email}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing user: {email}'))
        
        # Create a toko if user doesn't have one
        if not user.toko:
            toko = Toko.objects.create()
            user.toko = toko
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created new toko for user: {email}'))
        else:
            toko = user.toko
            self.stdout.write(self.style.SUCCESS(f'Using existing toko: {toko.id} for user: {email}'))
            
        return user, toko

    def seed_minimal_data(self, user, toko, seed_id):
        """Seed minimal data for local development"""
        self.stdout.write(self.style.WARNING('Seeding minimal data for local environment...'))
        
        # Create categories
        kategori_makanan = KategoriProduk.objects.create(nama="Makanan", toko=toko)
        kategori_minuman = KategoriProduk.objects.create(nama="Minuman", toko=toko)
        
        # Create units
        Satuan.objects.get_or_create(nama="Pcs")
        Satuan.objects.get_or_create(nama="Box")
        Satuan.objects.get_or_create(nama="Kg")
        
        # Create products (5 products is minimal)
        products = [
            Produk.objects.create(
                nama="Nasi Goreng",
                harga_modal=Decimal("10000"),
                harga_jual=Decimal("15000"),
                stok=50,
                satuan="Pcs",
                kategori=kategori_makanan,
                toko=toko
            ),
            Produk.objects.create(
                nama="Mie Goreng",
                harga_modal=Decimal("8000"),
                harga_jual=Decimal("12000"),
                stok=40,
                satuan="Pcs",
                kategori=kategori_makanan,
                toko=toko
            ),
            Produk.objects.create(
                nama="Es Teh",
                harga_modal=Decimal("2000"),
                harga_jual=Decimal("5000"),
                stok=100,
                satuan="Pcs",
                kategori=kategori_minuman,
                toko=toko
            ),
            Produk.objects.create(
                nama="Es Jeruk",
                harga_modal=Decimal("3000"),
                harga_jual=Decimal("6000"),
                stok=80,
                satuan="Pcs",
                kategori=kategori_minuman,
                toko=toko
            ),
            Produk.objects.create(
                nama="Kerupuk",
                harga_modal=Decimal("5000"),
                harga_jual=Decimal("7000"),
                stok=30,
                satuan="Box",
                kategori=kategori_makanan,
                toko=toko
            ),
        ]
        
        # Create transactions (3 sales, 2 purchases)
        # Sales transaction
        for i in range(3):
            product = random.choice(products)
            quantity = random.randint(1, 5)
            harga_jual = product.harga_jual
            harga_modal = product.harga_modal
            total_amount = quantity * harga_jual
            total_modal = quantity * harga_modal
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pemasukan",
                category="Penjualan Barang",
                total_amount=total_amount,
                total_modal=total_modal,
                amount=total_amount,
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i)
            )
            
            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=harga_jual,
                harga_modal_saat_transaksi=harga_modal
            )
            
            # Update stock
            product.stok -= quantity
            product.save()
            
        # Purchase transaction
        for i in range(2):
            product = random.choice(products)
            quantity = random.randint(5, 10)
            harga_modal = product.harga_modal
            total_amount = quantity * harga_modal
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pengeluaran",
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i)
            )
            
            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=harga_modal
            )
            
            # Update stock
            product.stok += quantity
            product.save()

    def seed_defined_data(self, user, toko, seed_id):
        """Seed well-defined data for server/CI environment"""
        self.stdout.write(self.style.WARNING('Seeding well-defined data for server environment...'))
        
        # Create categories with more variety
        categories = {}
        for cat_name in ["Makanan", "Minuman", "Snack", "Bahan Baku", "Pakaian", "Elektronik"]:
            categories[cat_name] = KategoriProduk.objects.create(nama=cat_name, toko=toko)
        
        # Create units with more options
        for unit in ["Pcs", "Box", "Kg", "Lusin", "Pack", "Botol", "Karton"]:
            Satuan.objects.get_or_create(nama=unit)
        
        # Create products (15 products for server environment)
        products = []
        product_data = [
            # Makanan
            {"nama": "Nasi Goreng Spesial", "modal": 12000, "jual": 18000, "stok": 50, "satuan": "Pcs", "kategori": "Makanan"},
            {"nama": "Mie Goreng Spesial", "modal": 10000, "jual": 15000, "stok": 45, "satuan": "Pcs", "kategori": "Makanan"},
            {"nama": "Ayam Goreng", "modal": 15000, "jual": 22000, "stok": 30, "satuan": "Pcs", "kategori": "Makanan"},
            
            # Minuman
            {"nama": "Es Teh Manis", "modal": 2000, "jual": 5000, "stok": 100, "satuan": "Pcs", "kategori": "Minuman"},
            {"nama": "Es Jeruk", "modal": 3000, "jual": 6000, "stok": 80, "satuan": "Pcs", "kategori": "Minuman"},
            {"nama": "Kopi Hitam", "modal": 4000, "jual": 8000, "stok": 60, "satuan": "Pcs", "kategori": "Minuman"},
            
            # Snack
            {"nama": "Keripik Singkong", "modal": 5000, "jual": 8000, "stok": 40, "satuan": "Pack", "kategori": "Snack"},
            {"nama": "Kerupuk Udang", "modal": 6000, "jual": 10000, "stok": 35, "satuan": "Pack", "kategori": "Snack"},
            {"nama": "Kacang Goreng", "modal": 7000, "jual": 12000, "stok": 25, "satuan": "Pack", "kategori": "Snack"},
            
            # Bahan Baku
            {"nama": "Tepung Terigu", "modal": 8000, "jual": 12000, "stok": 20, "satuan": "Kg", "kategori": "Bahan Baku"},
            {"nama": "Gula Pasir", "modal": 12000, "jual": 15000, "stok": 25, "satuan": "Kg", "kategori": "Bahan Baku"},
            
            # Pakaian
            {"nama": "Kaos Polos", "modal": 25000, "jual": 45000, "stok": 15, "satuan": "Pcs", "kategori": "Pakaian"},
            {"nama": "Kemeja", "modal": 45000, "jual": 85000, "stok": 10, "satuan": "Pcs", "kategori": "Pakaian"},
            
            # Elektronik
            {"nama": "Charger HP", "modal": 15000, "jual": 25000, "stok": 12, "satuan": "Pcs", "kategori": "Elektronik"},
            {"nama": "Earphone", "modal": 20000, "jual": 35000, "stok": 8, "satuan": "Pcs", "kategori": "Elektronik"},
        ]
        
        for data in product_data:
            product = Produk.objects.create(
                nama=data["nama"],
                harga_modal=Decimal(str(data["modal"])),
                harga_jual=Decimal(str(data["jual"])),
                stok=data["stok"],
                satuan=data["satuan"],
                kategori=categories[data["kategori"]],
                toko=toko
            )
            products.append(product)
        
        # Create different types of transactions
        # 1. Completed sales (Pemasukan - Penjualan Barang)
        for i in range(10):
            # Choose 1-3 products for this transaction
            selected_products = random.sample(products, random.randint(1, 3))
            total_amount = Decimal('0')
            total_modal = Decimal('0')
            
            # Create the transaction
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pemasukan",
                category="Penjualan Barang",
                total_amount=0,  # Will update after adding items
                total_modal=0,   # Will update after adding items
                amount=0,        # Will update after adding items
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i % 30, hours=random.randint(1, 12))
            )
            
            # Add items to the transaction
            for product in selected_products:
                quantity = random.randint(1, 3)
                
                # Create transaction item
                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=product.harga_jual,
                    harga_modal_saat_transaksi=product.harga_modal
                )
                
                # Update running totals
                item_total = product.harga_jual * quantity
                item_modal = product.harga_modal * quantity
                total_amount += item_total
                total_modal += item_modal
                
                # Update stock
                product.stok -= quantity
                product.save()
            
            # Update transaction with calculated totals
            transaksi.total_amount = total_amount
            transaksi.total_modal = total_modal
            transaksi.amount = total_amount
            transaksi.save()
            
        # 2. Unpaid sales (status="Belum Lunas")
        for i in range(5):
            product = random.choice(products)
            quantity = random.randint(1, 3)
            total_amount = product.harga_jual * quantity
            total_modal = product.harga_modal * quantity
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pemasukan",
                category="Penjualan Barang",
                total_amount=total_amount,
                total_modal=total_modal,
                amount=total_amount,
                status="Belum Lunas",
                created_at=timezone.now() - timedelta(days=i % 15, hours=random.randint(1, 12))
            )
            
            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=product.harga_jual,
                harga_modal_saat_transaksi=product.harga_modal
            )
            
            # Update stock
            product.stok -= quantity
            product.save()
        
        # 3. Stock purchases (Pengeluaran - Pembelian Stok)
        for i in range(8):
            product = random.choice(products)
            quantity = random.randint(5, 15)
            total_amount = product.harga_modal * quantity
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pengeluaran",
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i % 30, hours=random.randint(1, 12))
            )
            
            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal
            )
            
            # Update stock
            product.stok += quantity
            product.save()
            
        # 4. Unpaid purchases (Pengeluaran - Pembelian Stok - Belum Lunas)
        for i in range(3):
            product = random.choice(products)
            quantity = random.randint(10, 20)
            total_amount = product.harga_modal * quantity
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pengeluaran",
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Belum Lunas",
                created_at=timezone.now() - timedelta(days=i % 15, hours=random.randint(1, 12))
            )
            
            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal
            )
            
            # Update stock
            product.stok += quantity
            product.save()
            
        # 5. Other expenses (Pengeluaran - Biaya Operasional)
        expense_categories = ["Biaya Operasional", "Biaya Sewa", "Biaya Gaji"]
        for i in range(6):
            category = random.choice(expense_categories)
            amount = Decimal(str(random.randint(50, 500) * 1000))
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pengeluaran",
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i % 30, hours=random.randint(1, 12))
            )
            
        # 6. Other income (Pemasukan - Pendapatan Lain-Lain)
        income_categories = ["Pendapatan Lain-Lain", "Pendapatan Pinjaman"]
        for i in range(4):
            category = random.choice(income_categories)
            amount = Decimal(str(random.randint(50, 300) * 1000))
            
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="Pemasukan",
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Selesai",
                created_at=timezone.now() - timedelta(days=i % 30, hours=random.randint(1, 12))
            )
        
        # Create another user (employees) for the same toko
        employees = [
            {"email": f"karyawan1_{seed_id}@example.com", "username": "Karyawan Satu", "role": "Karyawan"},
            {"email": f"pengelola1_{seed_id}@example.com", "username": "Pengelola Satu", "role": "Pengelola"}
        ]
        
        for emp_data in employees:
            employee = User.objects.create(
                email=emp_data["email"],
                username=emp_data["username"],
                role=emp_data["role"],
                toko=toko,
                is_active=True
            )
            
        # Create pending invitations
        invitation_data = [
            {"email": f"invited1_{seed_id}@example.com", "name": "Calon Karyawan", "role": "Karyawan"},
            {"email": f"invited2_{seed_id}@example.com", "name": "Calon Pengelola", "role": "Pengelola"}
        ]
        
        for inv_data in invitation_data:
            expiration = timezone.now() + timedelta(days=1)
            token = f"dummy_token_{seed_id}_{inv_data['email']}"
            
            Invitation.objects.create(
                email=inv_data["email"],
                name=inv_data["name"],
                role=inv_data["role"],
                toko=toko,
                created_by=user,
                token=token,
                expires_at=expiration
            )

    def seed_production_data(self, user, toko, seed_id):
        """Seed production data with rollback capability"""
        self.stdout.write(self.style.WARNING('Seeding production data with rollback capability...'))
        
        # This method is similar to seed_defined_data but with more 
        # careful transaction handling and logging for rollback
        
        # Create rollback log file
        log_dir = os.path.join(settings.BASE_DIR, 'seed_logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f'rollback_{seed_id}.log')
        
        with open(log_path, 'w') as log_file:
            log_file.write(f"SEED_ID: {seed_id}\n")
            log_file.write(f"USER_EMAIL: {user.email}\n")
            log_file.write(f"TOKO_ID: {toko.id}\n")
            log_file.write(f"TIMESTAMP: {timezone.now().isoformat()}\n")
            log_file.write("---\n")
            
            # Log existing data counts for verification
            log_file.write(f"BEFORE_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n")
            log_file.write(f"BEFORE_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n")
            log_file.write(f"BEFORE_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n")
            log_file.write("---\n")
            
            # We'll use the same seeding as defined_data but with logging
            # Create categories
            categories = {}
            for cat_name in ["Makanan", "Minuman", "Snack", "Bahan Baku", "Pakaian", "Elektronik"]:
                cat = KategoriProduk.objects.create(nama=cat_name, toko=toko)
                categories[cat_name] = cat
                log_file.write(f"CREATED_CATEGORY: {cat.id} {cat_name}\n")
            
            # Create units
            for unit in ["Pcs", "Box", "Kg", "Lusin", "Pack", "Botol", "Karton"]:
                obj, created = Satuan.objects.get_or_create(nama=unit)
                if created:
                    log_file.write(f"CREATED_UNIT: {obj.id} {unit}\n")
            
            # Create products
            products = []
            product_data = [
                # Using the same product data as in seed_defined_data
                {"nama": "Nasi Goreng Spesial", "modal": 12000, "jual": 18000, "stok": 50, "satuan": "Pcs", "kategori": "Makanan"},
                {"nama": "Mie Goreng Spesial", "modal": 10000, "jual": 15000, "stok": 45, "satuan": "Pcs", "kategori": "Makanan"},
                {"nama": "Ayam Goreng", "modal": 15000, "jual": 22000, "stok": 30, "satuan": "Pcs", "kategori": "Makanan"},
                {"nama": "Es Teh Manis", "modal": 2000, "jual": 5000, "stok": 100, "satuan": "Pcs", "kategori": "Minuman"},
                {"nama": "Es Jeruk", "modal": 3000, "jual": 6000, "stok": 80, "satuan": "Pcs", "kategori": "Minuman"},
                {"nama": "Kopi Hitam", "modal": 4000, "jual": 8000, "stok": 60, "satuan": "Pcs", "kategori": "Minuman"},
                {"nama": "Keripik Singkong", "modal": 5000, "jual": 8000, "stok": 40, "satuan": "Pack", "kategori": "Snack"},
                {"nama": "Kerupuk Udang", "modal": 6000, "jual": 10000, "stok": 35, "satuan": "Pack", "kategori": "Snack"},
                {"nama": "Kacang Goreng", "modal": 7000, "jual": 12000, "stok": 25, "satuan": "Pack", "kategori": "Snack"},
                {"nama": "Tepung Terigu", "modal": 8000, "jual": 12000, "stok": 20, "satuan": "Kg", "kategori": "Bahan Baku"},
                {"nama": "Gula Pasir", "modal": 12000, "jual": 15000, "stok": 25, "satuan": "Kg", "kategori": "Bahan Baku"},
                {"nama": "Kaos Polos", "modal": 25000, "jual": 45000, "stok": 15, "satuan": "Pcs", "kategori": "Pakaian"},
                {"nama": "Kemeja", "modal": 45000, "jual": 85000, "stok": 10, "satuan": "Pcs", "kategori": "Pakaian"},
                {"nama": "Charger HP", "modal": 15000, "jual": 25000, "stok": 12, "satuan": "Pcs", "kategori": "Elektronik"},
                {"nama": "Earphone", "modal": 20000, "jual": 35000, "stok": 8, "satuan": "Pcs", "kategori": "Elektronik"},
            ]
            
            for data in product_data:
                product = Produk.objects.create(
                    nama=data["nama"],
                    harga_modal=Decimal(str(data["modal"])),
                    harga_jual=Decimal(str(data["jual"])),
                    stok=data["stok"],
                    satuan=data["satuan"],
                    kategori=categories[data["kategori"]],
                    toko=toko
                )
                products.append(product)
                log_file.write(f"CREATED_PRODUCT: {product.id} {product.nama}\n")
            
            # Create transactions with similar patterns to defined_data
            # but with fewer transactions (since this is production)
            
            # 1. Completed sales (5)
            for i in range(5):
                selected_products = random.sample(products, random.randint(1, 3))
                total_amount = Decimal('0')
                total_modal = Decimal('0')
                
                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="Pemasukan",
                    category="Penjualan Barang",
                    total_amount=0,
                    total_modal=0,
                    amount=0,
                    status="Selesai",
                    created_at=timezone.now() - timedelta(days=i % 15, hours=random.randint(1, 12))
                )
                
                log_file.write(f"CREATED_TRANSACTION: {transaksi.id} Pemasukan Penjualan_Barang\n")
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    
                    item = TransaksiItem.objects.create(
                        transaksi=transaksi,
                        product=product,
                        quantity=quantity,
                        harga_jual_saat_transaksi=product.harga_jual,
                        harga_modal_saat_transaksi=product.harga_modal
                    )
                    
                    log_file.write(f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n")
                    
                    item_total = product.harga_jual * quantity
                    item_modal = product.harga_modal * quantity
                    total_amount += item_total
                    total_modal += item_modal
                    
                    original_stock = product.stok
                    product.stok -= quantity
                    product.save()
                    log_file.write(f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n")
                
                transaksi.total_amount = total_amount
                transaksi.total_modal = total_modal
                transaksi.amount = total_amount
                transaksi.save()
                log_file.write(f"UPDATED_TRANSACTION_TOTALS: {transaksi.id} {total_amount} {total_modal}\n")
            
            # 2. Stock purchases (3)
            for i in range(3):
                product = random.choice(products)
                quantity = random.randint(5, 15)
                total_amount = product.harga_modal * quantity
                
                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="Pengeluaran",
                    category="Pembelian Stok",
                    total_amount=total_amount,
                    total_modal=0,
                    amount=total_amount,
                    status="Selesai",
                    created_at=timezone.now() - timedelta(days=i % 15, hours=random.randint(1, 12))
                )
                
                log_file.write(f"CREATED_TRANSACTION: {transaksi.id} Pengeluaran Pembelian_Stok\n")
                
                item = TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=0,
                    harga_modal_saat_transaksi=product.harga_modal
                )
                
                log_file.write(f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n")
                
                original_stock = product.stok
                product.stok += quantity
                product.save()
                log_file.write(f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n")
            
            # 3. Other income/expense (4)
            categories = ["Biaya Operasional", "Pendapatan Lain-Lain", "Biaya Sewa", "Pendapatan Pinjaman"]
            transaction_types = {
                "Biaya Operasional": "Pengeluaran",
                "Pendapatan Lain-Lain": "Pemasukan",
                "Biaya Sewa": "Pengeluaran",
                "Pendapatan Pinjaman": "Pemasukan"
            }
            
            for category in categories:
                amount = Decimal(str(random.randint(50, 300) * 1000))
                transaction_type = transaction_types[category]
                
                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type=transaction_type,
                    category=category,
                    total_amount=amount,
                    total_modal=0,
                    amount=amount,
                    status="Selesai",
                    created_at=timezone.now() - timedelta(days=random.randint(1, 15), hours=random.randint(1, 12))
                )
                
                log_file.write(f"CREATED_TRANSACTION: {transaksi.id} {transaction_type} {category}\n")
            
            log_file.write("---\n")
            log_file.write(f"AFTER_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n")
            log_file.write(f"AFTER_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n")
            log_file.write(f"AFTER_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n")
        
        self.stdout.write(self.style.SUCCESS(f'Production data seeded with rollback log at: {log_path}'))
    
    def rollback_seeding(self, seed_id):
        """Rollback a previous seeding operation"""
        self.stdout.write(self.style.WARNING(f'Rolling back seed operation: {seed_id}'))
        
        # Find the rollback log file
        log_dir = os.path.join(settings.BASE_DIR, 'seed_logs')
        log_path = os.path.join(log_dir, f'rollback_{seed_id}.log')
        
        if not os.path.exists(log_path):
            raise CommandError(f'Rollback log not found: {log_path}')
        
        with transaction.atomic():
            # Parse the log file
            with open(log_path, 'r') as log_file:
                lines = log_file.readlines()
                
                # Extract basic info
                metadata = {}
                for line in lines[:6]:  # First few lines are metadata
                    if ': ' in line:
                        key, value = line.strip().split(': ', 1)
                        metadata[key] = value
                
                # Check if we have the necessary metadata
                if 'USER_EMAIL' not in metadata or 'TOKO_ID' not in metadata:
                    raise CommandError('Invalid rollback log: missing metadata')
                
                user_email = metadata['USER_EMAIL']
                toko_id = int(metadata['TOKO_ID'])
                
                # Find the user and toko
                try:
                    user = User.objects.get(email=user_email)
                    toko = Toko.objects.get(id=toko_id)
                except (User.DoesNotExist, Toko.DoesNotExist):
                    raise CommandError(f'User {user_email} or Toko {toko_id} not found')
                
                # Delete the created data in reverse order
                # This is a simplified approach - in a real system you might want more granular rollback
                # based on the specific IDs in the log file
                
                # 1. Remove transactions and items
                TransaksiItem.objects.filter(transaksi__toko=toko).delete()
                Transaksi.objects.filter(toko=toko).delete()
                
                # 2. Remove products
                Produk.objects.filter(toko=toko).delete()
                
                # 3. Remove categories
                KategoriProduk.objects.filter(toko=toko).delete()
                
                # 4. Do not remove units as they are global
                
                self.stdout.write(self.style.SUCCESS(f'Successfully rolled back seed operation: {seed_id}'))
                
                # Rename the log file to indicate it's been rolled back
                os.rename(log_path, log_path + '.rolled_back')