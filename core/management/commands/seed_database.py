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
    help = "Seeds the database with sample data for testing and development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            default="local",
            choices=["local", "server", "production"],
            help="Seeding mode: local (minimal data), server (well-defined), production (with rollback)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Email of the user to associate the seed data with",
        )
        parser.add_argument(
            "--clean", action="store_true", help="Clean existing data before seeding"
        )
        parser.add_argument(
            "--rollback-id",
            type=str,
            help="ID of a previous seeding operation to rollback (production mode only)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        mode = options["mode"]
        email = options.get("email")
        clean = options.get("clean", False)
        rollback_id = options.get("rollback_id")

        if mode == "production" and rollback_id:
            return self.rollback_seeding(rollback_id)
        
        # Rest of the handle method continues as before

        if not email:
            if mode == "production":
                raise CommandError("Email is required for production seeding")
            email = "demo@example.com"  # Default email for non-production modes

        # Generate a unique seed ID for tracking and potential rollback
        seed_id = f"seed_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Print the seed ID for easy reference
        self.stdout.write(self.style.SUCCESS(f"Generated seed ID: {seed_id}"))

        if clean:
            self.stdout.write(self.style.WARNING("Cleaning existing data..."))
            self.clean_data(email)

        self.stdout.write(
            self.style.SUCCESS(f"Starting {mode} seeding with ID: {seed_id}")
        )

        # Create or get user and toko
        user, toko = self.create_user_and_toko(email, seed_id)

        # Seed data based on mode
        if mode == "local":
            self.seed_minimal_data(user, toko, seed_id)
        elif mode == "server":
            self.seed_defined_data(user, toko, seed_id)
        elif mode == "production":
            self.seed_production_data(user, toko, seed_id)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded the database in {mode} mode")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Seed ID: {seed_id} (save for rollback if needed)")
        )

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
                self.stdout.write(self.style.SUCCESS(f"Cleaned data for user {email}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"User {email} has no associated shop")
                )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f"User {email} not found, nothing to clean")
            )

    def create_user_and_toko(self, email, seed_id):
        """Create or get a user and their toko"""
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@")[0],
                "is_active": True,
                "role": "Pemilik",
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created new user: {email}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Using existing user: {email}"))

        # Create a toko if user doesn't have one
        if not user.toko:
            toko = Toko.objects.create()
            user.toko = toko
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created new toko for user: {email}"))
        else:
            toko = user.toko
            self.stdout.write(
                self.style.SUCCESS(f"Using existing toko: {toko.id} for user: {email}")
            )

        return user, toko

    def seed_minimal_data(self, user, toko, seed_id):
        """Seed minimal data for local development"""
        self.stdout.write(
            self.style.WARNING("Seeding minimal data for local environment...")
        )

        # Initialize entity tracking containers
        created_categories = []
        created_products = []
        created_transactions = []
        created_transaction_items = []
        created_units = []

        # Create log and JSON file paths
        log_dir = settings.SEED_LOGS_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"rollback_{seed_id}.log")
        json_path = os.path.join(log_dir, f"rollback_{seed_id}.json")
        
        # Debug log creation
        self.stdout.write(self.style.SUCCESS(f"Creating log file at: {log_path}"))
        self.stdout.write(self.style.SUCCESS(f"Creating JSON file at: {json_path}"))
        
        # Create and start writing to the log file
        with open(log_path, "w") as log_file:
            # Write metadata
            log_file.write(f"SEED_ID: {seed_id}\n")
            log_file.write(f"USER_EMAIL: {user.email}\n")
            log_file.write(f"TOKO_ID: {toko.id}\n")
            log_file.write(f"TIMESTAMP: {timezone.now().isoformat()}\n")
            log_file.write("---\n")

            # Log existing data counts for verification
            log_file.write(
                f"BEFORE_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n"
            )
            log_file.write("---\n")

        # Create categories with variety
        categories = {}
        for cat_name in [
            "Makanan",
            "Minuman",
            "Snack",
            "Bahan Baku",
        ]:
            category = KategoriProduk.objects.create(
                nama=cat_name, toko=toko
            )
            categories[cat_name] = category
            # Track this category
            created_categories.append({"id": category.id, "name": cat_name})
            # Log created category
            with open(log_path, "a") as log_file:
                log_file.write(f"CREATED_CATEGORY: {category.id} {cat_name}\n")

        # Create units with more options
        for unit in [
            "Pcs",
            "Box",
            "Kg",
            "Pack",
            "Botol",
        ]:
            unit_obj, created = Satuan.objects.get_or_create(nama=unit)
            if created:
                # Track only newly created units
                created_units.append({"id": unit_obj.id, "name": unit})
                # Log created unit
                with open(log_path, "a") as log_file:
                    log_file.write(f"CREATED_UNIT: {unit_obj.id} {unit}\n")

        # Create products (10 products for local environment)
        products = []
        product_data = [
            # Makanan
            {
                "nama": "Nasi Goreng",
                "modal": 12000,
                "jual": 18000,
                "stok": 50,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Mie Goreng",
                "modal": 10000,
                "jual": 15000,
                "stok": 45,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Ayam Goreng",
                "modal": 15000,
                "jual": 22000,
                "stok": 30,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            # Minuman
            {
                "nama": "Es Teh Manis",
                "modal": 2000,
                "jual": 5000,
                "stok": 100,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            {
                "nama": "Es Jeruk",
                "modal": 3000,
                "jual": 6000,
                "stok": 80,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            # Snack
            {
                "nama": "Keripik Singkong",
                "modal": 5000,
                "jual": 8000,
                "stok": 40,
                "satuan": "Pack",
                "kategori": "Snack",
            },
            {
                "nama": "Kerupuk Udang",
                "modal": 6000,
                "jual": 10000,
                "stok": 35,
                "satuan": "Pack",
                "kategori": "Snack",
            },
            # Bahan Baku
            {
                "nama": "Tepung Terigu",
                "modal": 8000,
                "jual": 12000,
                "stok": 20,
                "satuan": "Kg",
                "kategori": "Bahan Baku",
            },
            {
                "nama": "Gula Pasir",
                "modal": 12000,
                "jual": 15000,
                "stok": 25,
                "satuan": "Kg",
                "kategori": "Bahan Baku",
            },
            {
                "nama": "Minyak Goreng",
                "modal": 14000,
                "jual": 18000,
                "stok": 30,
                "satuan": "Kg",
                "kategori": "Bahan Baku",
            },
        ]

        for data in product_data:
            product = Produk.objects.create(
                nama=data["nama"],
                harga_modal=Decimal(str(data["modal"])),
                harga_jual=Decimal(str(data["jual"])),
                stok=data["stok"],
                satuan=data["satuan"],
                kategori=categories[data["kategori"]],
                toko=toko,
            )
            products.append(product)
            # Track created product
            created_products.append({
                "id": product.id,
                "name": product.nama,
                "category_id": product.kategori.id
            })
            # Log created product
            with open(log_path, "a") as log_file:
                log_file.write(f"CREATED_PRODUCT: {product.id} {product.nama}\n")

        # Date range for transactions - past 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Create different types of transactions with spread-out dates
        # 1. Completed sales (Pemasukan - Penjualan Barang) - 8 transactions
        for i in range(8):
            # Choose 1-2 products for this transaction
            selected_products = random.sample(products, random.randint(1, 2))
            total_amount = Decimal("0")
            total_modal = Decimal("0")

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            transaction_date = start_date + timedelta(
                days=random_days, hours=random_hours, minutes=random_minutes
            )

            # Create the transaction
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category="Penjualan Barang",
                total_amount=0,  # Will update after adding items
                total_modal=0,  # Will update after adding items
                amount=0,  # Will update after adding items
                status="Lunas",
            )

            # Update the created_at date directly in the database to bypass auto_now_add
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

            # Refresh the object after the update
            transaksi.refresh_from_db()

            # Add items to the transaction
            for product in selected_products:
                quantity = random.randint(1, 3)

                # Create transaction item
                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=product.harga_jual,
                    harga_modal_saat_transaksi=product.harga_modal,
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

        # 2. Unpaid sales (status="Belum Lunas") - 4 transactions
        for i in range(4):
            selected_products = random.sample(products, random.randint(1, 2))
            total_amount = Decimal("0")
            total_modal = Decimal("0")

            # Generate a random date within the range, more recent
            later_start = start_date + timedelta(days=20)
            days_diff = (end_date - later_start).days
            random_days = random.randint(0, days_diff) if days_diff > 0 else 0
            transaction_date = later_start + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category="Penjualan Barang",
                total_amount=0,
                total_modal=0,
                amount=0,
                status="Belum Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            for product in selected_products:
                quantity = random.randint(1, 2)

                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=product.harga_jual,
                    harga_modal_saat_transaksi=product.harga_modal,
                )

                item_total = product.harga_jual * quantity
                item_modal = product.harga_modal * quantity
                total_amount += item_total
                total_modal += item_modal

                product.stok -= quantity
                product.save()

            transaksi.total_amount = total_amount
            transaksi.total_modal = total_modal
            transaksi.amount = total_amount
            transaksi.save()

        # 3. Stock purchases (Pengeluaran - Pembelian Stok) - 6 transactions
        for i in range(6):
            product = random.choice(products)
            quantity = random.randint(5, 15)
            total_amount = product.harga_modal * quantity

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal,
            )

            # Update stock
            product.stok += quantity
            product.save()

        # 4. Unpaid purchases (Pengeluaran - Pembelian Stok - Belum Lunas) - 3 transactions
        for i in range(3):
            product = random.choice(products)
            quantity = random.randint(10, 20)
            total_amount = product.harga_modal * quantity

            # Generate a random date within the range, more recent
            later_start = start_date + timedelta(days=15)
            days_diff = (end_date - later_start).days
            random_days = random.randint(0, days_diff) if days_diff > 0 else 0
            transaction_date = later_start + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Belum Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal,
            )

            # Update stock
            product.stok += quantity
            product.save()

        # 5. Other expenses (Pengeluaran - various categories) - 5 transactions
        expense_categories = [
            "Biaya Operasional",
            "Biaya Sewa",
            "Biaya Gaji",
        ]
        for i in range(5):
            category = random.choice(expense_categories)
            amount = Decimal(str(random.randint(50, 200) * 1000))

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

        # 6. Other income (Pemasukan - various categories) - 4 transactions
        income_categories = [
            "Pendapatan Lain-Lain",
            "Pendapatan Pinjaman",
        ]
        for i in range(4):
            category = random.choice(income_categories)
            amount = Decimal(str(random.randint(50, 200) * 1000))

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

        # Create another user (employees) for the same toko
        employees = [
            {
                "email": f"karyawan1_{seed_id}@example.com",
                "username": "Karyawan Satu",
                "role": "Karyawan",
            },
        ]

        for emp_data in employees:
            employee = User.objects.create(
                email=emp_data["email"],
                username=emp_data["username"],
                role=emp_data["role"],
                toko=toko,
                is_active=True,
            )

        # Create pending invitations
        invitation_data = [
            {
                "email": f"invited1_{seed_id}@example.com",
                "name": "Calon Karyawan",
                "role": "Karyawan",
            },
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
                expires_at=expiration,
            )

        # Save rollback information to JSON file
        try:
            from core.management.utils import save_rollback_info
            rollback_data = {
                "user_email": user.email,
                "toko_id": toko.id,
                "created_entities": {
                    "categories": created_categories,
                    "products": created_products,
                    "transactions": created_transactions,
                    "transaction_items": created_transaction_items,
                    "units": created_units,
                }
            }
            save_result, save_error = save_rollback_info(seed_id, json_path, rollback_data)
            if save_result:
                self.stdout.write(self.style.SUCCESS(f"JSON rollback data saved to: {json_path}"))
            else:
                self.stdout.write(self.style.ERROR(f"Error saving JSON rollback data: {save_error}"))
                
            # Create detailed rollback file similar to production mode
            with open(log_path, "a") as log_file:
                # Write some additional stats
                log_file.write("---\n")
                log_file.write(f"AFTER_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n")
                log_file.write(f"AFTER_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n")
                log_file.write(f"AFTER_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n")
                log_file.write("---\n")
                log_file.write(f"TOTAL_PRODUCTS: {len(created_products)}\n")
                log_file.write(f"TOTAL_CATEGORIES: {len(created_categories)}\n")
                log_file.write(f"TOTAL_TRANSACTIONS: {len(created_transactions)}\n")
                log_file.write(f"TOTAL_TRANSACTION_ITEMS: {len(created_transaction_items)}\n")
                
                # Write entity IDs for rollback script
                for category in created_categories:
                    log_file.write(f"CREATED_CATEGORY: {category['id']} {category['name']}\n")
                
                for product in created_products:
                    log_file.write(f"CREATED_PRODUCT: {product['id']} {product['name']}\n")
                
                for transaction in created_transactions:
                    log_file.write(f"CREATED_TRANSACTION: {transaction['id']} {transaction['type']} {transaction['category']}\n")
                
                for item in created_transaction_items:
                    if 'id' in item and 'transaction_id' in item and 'product_id' in item and 'quantity' in item:
                        log_file.write(f"CREATED_TRANSACTION_ITEM: {item['id']} {item['transaction_id']} {item['product_id']} {item['quantity']}\n")
                
                for unit in created_units:
                    log_file.write(f"CREATED_UNIT: {unit['id']} {unit['name']}\n")
                    
            self.stdout.write(self.style.SUCCESS(f"Rollback log saved to: {log_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving rollback data: {str(e)}"))

    def seed_defined_data(self, user, toko, seed_id):
        """Seed well-defined data for server/CI environment"""
        self.stdout.write(
            self.style.WARNING("Seeding well-defined data for server environment...")
        )
        
        # Initialize entity tracking containers
        created_categories = []
        created_products = []
        created_transactions = []
        created_transaction_items = []
        created_units = []

        # Create log and JSON file paths
        log_dir = settings.SEED_LOGS_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"rollback_{seed_id}.log")
        json_path = os.path.join(log_dir, f"rollback_{seed_id}.json")
        
        # Debug log creation
        self.stdout.write(self.style.SUCCESS(f"Creating log file at: {log_path}"))
        self.stdout.write(self.style.SUCCESS(f"Creating JSON file at: {json_path}"))
        
        # Create and start writing to the log file
        with open(log_path, "w") as log_file:
            # Write metadata
            log_file.write(f"SEED_ID: {seed_id}\n")
            log_file.write(f"USER_EMAIL: {user.email}\n")
            log_file.write(f"TOKO_ID: {toko.id}\n")
            log_file.write(f"TIMESTAMP: {timezone.now().isoformat()}\n")
            log_file.write("---\n")

            # Log existing data counts for verification
            log_file.write(
                f"BEFORE_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n"
            )
            log_file.write("---\n")

        # Create categories with more variety
        categories = {}
        for cat_name in [
            "Makanan",
            "Minuman",
            "Snack",
            "Bahan Baku",
            "Pakaian",
            "Elektronik",
            "Alat Tulis",
        ]:
            category = KategoriProduk.objects.create(
                nama=cat_name, toko=toko
            )
            categories[cat_name] = category
            # Track this category
            created_categories.append({"id": category.id, "name": cat_name})

        # Create units with more options
        for unit in [
            "Pcs",
            "Box",
            "Kg",
            "Lusin",
            "Pack",
            "Botol",
            "Karton",
            "Set",
            "Roll",
        ]:
            unit_obj, created = Satuan.objects.get_or_create(nama=unit)
            if created:
                # Track only newly created units
                created_units.append({"id": unit_obj.id, "name": unit})

        # Create products (20 products for server environment)
        products = []
        product_data = [
            # Makanan
            {
                "nama": "Nasi Goreng Spesial",
                "modal": 12000,
                "jual": 18000,
                "stok": 50,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Mie Goreng Spesial",
                "modal": 10000,
                "jual": 15000,
                "stok": 45,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Ayam Goreng",
                "modal": 15000,
                "jual": 22000,
                "stok": 30,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Bakso Komplit",
                "modal": 14000,
                "jual": 20000,
                "stok": 35,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            {
                "nama": "Sate Ayam",
                "modal": 16000,
                "jual": 25000,
                "stok": 40,
                "satuan": "Pcs",
                "kategori": "Makanan",
            },
            # Minuman
            {
                "nama": "Es Teh Manis",
                "modal": 2000,
                "jual": 5000,
                "stok": 100,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            {
                "nama": "Es Jeruk",
                "modal": 3000,
                "jual": 6000,
                "stok": 80,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            {
                "nama": "Kopi Hitam",
                "modal": 4000,
                "jual": 8000,
                "stok": 60,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            {
                "nama": "Jus Alpukat",
                "modal": 8000,
                "jual": 15000,
                "stok": 40,
                "satuan": "Pcs",
                "kategori": "Minuman",
            },
            # Snack
            {
                "nama": "Keripik Singkong",
                "modal": 5000,
                "jual": 8000,
                "stok": 40,
                "satuan": "Pack",
                "kategori": "Snack",
            },
            {
                "nama": "Kerupuk Udang",
                "modal": 6000,
                "jual": 10000,
                "stok": 35,
                "satuan": "Pack",
                "kategori": "Snack",
            },
            {
                "nama": "Kacang Goreng",
                "modal": 7000,
                "jual": 12000,
                "stok": 25,
                "satuan": "Pack",
                "kategori": "Snack",
            },
            # Bahan Baku
            {
                "nama": "Tepung Terigu",
                "modal": 8000,
                "jual": 12000,
                "stok": 20,
                "satuan": "Kg",
                "kategori": "Bahan Baku",
            },
            {
                "nama": "Gula Pasir",
                "modal": 12000,
                "jual": 15000,
                "stok": 25,
                "satuan": "Kg",
                "kategori": "Bahan Baku",
            },
            {
                "nama": "Minyak Goreng",
                "modal": 14000,
                "jual": 18000,
                "stok": 30,
                "satuan": "Liter",
                "kategori": "Bahan Baku",
            },
            # Pakaian
            {
                "nama": "Kaos Polos",
                "modal": 25000,
                "jual": 45000,
                "stok": 15,
                "satuan": "Pcs",
                "kategori": "Pakaian",
            },
            {
                "nama": "Kemeja",
                "modal": 45000,
                "jual": 85000,
                "stok": 10,
                "satuan": "Pcs",
                "kategori": "Pakaian",
            },
            # Elektronik
            {
                "nama": "Charger HP",
                "modal": 15000,
                "jual": 25000,
                "stok": 12,
                "satuan": "Pcs",
                "kategori": "Elektronik",
            },
            {
                "nama": "Earphone",
                "modal": 20000,
                "jual": 35000,
                "stok": 8,
                "satuan": "Pcs",
                "kategori": "Elektronik",
            },
            {
                "nama": "Powerbank",
                "modal": 65000,
                "jual": 120000,
                "stok": 5,
                "satuan": "Pcs",
                "kategori": "Elektronik",
            },
        ]

        for data in product_data:
            product = Produk.objects.create(
                nama=data["nama"],
                harga_modal=Decimal(str(data["modal"])),
                harga_jual=Decimal(str(data["jual"])),
                stok=data["stok"],
                satuan=data["satuan"],
                kategori=categories[data["kategori"]],
                toko=toko,
            )
            products.append(product)
            # Track created product
            created_products.append({
                "id": product.id,
                "name": product.nama,
                "category_id": product.kategori.id
            })

        # Date range from January 1, 2025 to May 21, 2025
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 5, 21)

        # Create different types of transactions with spread-out dates
        # 1. Completed sales (Pemasukan - Penjualan Barang) - 30 transactions
        for i in range(30):
            # Choose 1-3 products for this transaction
            selected_products = random.sample(products, random.randint(1, 3))
            total_amount = Decimal("0")
            total_modal = Decimal("0")

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            transaction_date = start_date + timedelta(
                days=random_days, hours=random_hours, minutes=random_minutes
            )

            # Create the transaction
            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category="Penjualan Barang",
                total_amount=0,  # Will update after adding items
                total_modal=0,  # Will update after adding items
                amount=0,  # Will update after adding items
                status="Lunas",
            )

            # Update the created_at date directly in the database to bypass auto_now_add
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

            # Refresh the object after the update
            transaksi.refresh_from_db()

            # Add items to the transaction
            for product in selected_products:
                quantity = random.randint(1, 3)

                # Create transaction item
                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=product.harga_jual,
                    harga_modal_saat_transaksi=product.harga_modal,
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

        # 2. Unpaid sales (status="Belum Lunas") - 15 transactions
        for i in range(15):
            selected_products = random.sample(products, random.randint(1, 2))
            total_amount = Decimal("0")
            total_modal = Decimal("0")

            # Generate a random date within the range, more recent
            later_start = start_date + timedelta(days=100)
            days_diff = (end_date - later_start).days
            random_days = random.randint(0, days_diff) if days_diff > 0 else 0
            transaction_date = later_start + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category="Penjualan Barang",
                total_amount=0,
                total_modal=0,
                amount=0,
                status="Belum Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            for product in selected_products:
                quantity = random.randint(1, 2)

                TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=product.harga_jual,
                    harga_modal_saat_transaksi=product.harga_modal,
                )

                item_total = product.harga_jual * quantity
                item_modal = product.harga_modal * quantity
                total_amount += item_total
                total_modal += item_modal

                product.stok -= quantity
                product.save()

            transaksi.total_amount = total_amount
            transaksi.total_modal = total_modal
            transaksi.amount = total_amount
            transaksi.save()

        # 3. Stock purchases (Pengeluaran - Pembelian Stok) - 20 transactions
        for i in range(20):
            product = random.choice(products)
            quantity = random.randint(5, 15)
            total_amount = product.harga_modal * quantity

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal,
            )

            # Update stock
            product.stok += quantity
            product.save()

        # 4. Unpaid purchases (Pengeluaran - Pembelian Stok - Belum Lunas) - 10 transactions
        for i in range(10):
            product = random.choice(products)
            quantity = random.randint(10, 20)
            total_amount = product.harga_modal * quantity

            # Generate a random date within the range, more recent
            later_start = start_date + timedelta(days=90)
            days_diff = (end_date - later_start).days
            random_days = random.randint(0, days_diff) if days_diff > 0 else 0
            transaction_date = later_start + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category="Pembelian Stok",
                total_amount=total_amount,
                total_modal=0,
                amount=total_amount,
                status="Belum Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

            TransaksiItem.objects.create(
                transaksi=transaksi,
                product=product,
                quantity=quantity,
                harga_jual_saat_transaksi=0,
                harga_modal_saat_transaksi=product.harga_modal,
            )

            # Update stock
            product.stok += quantity
            product.save()

        # 5. Other expenses (Pengeluaran - various categories) - 25 transactions
        expense_categories = [
            "Biaya Operasional",
            "Biaya Sewa",
            "Biaya Gaji",
            "Biaya Utilitas",
            "Biaya Transportasi",
        ]
        for i in range(25):
            category = random.choice(expense_categories)
            amount = Decimal(str(random.randint(50, 500) * 1000))

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pengeluaran",  # lowercase
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

        # 6. Other income (Pemasukan - various categories) - 15 transactions
        income_categories = [
            "Pendapatan Lain-Lain",
            "Pendapatan Pinjaman",
            "Pendapatan Investasi",
            "Pendapatan Hibah",
        ]
        for i in range(15):
            category = random.choice(income_categories)
            amount = Decimal(str(random.randint(50, 300) * 1000))

            # Generate a random date within the range
            days_diff = (end_date - start_date).days
            random_days = random.randint(0, days_diff)
            transaction_date = start_date + timedelta(days=random_days)

            transaksi = Transaksi.objects.create(
                toko=toko,
                created_by=user,
                transaction_type="pemasukan",  # lowercase
                category=category,
                total_amount=amount,
                total_modal=0,
                amount=amount,
                status="Lunas",
            )

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )

        # Create another user (employees) for the same toko
        employees = [
            {
                "email": f"karyawan1_{seed_id}@example.com",
                "username": "Karyawan Satu",
                "role": "Karyawan",
            },
            {
                "email": f"karyawan2_{seed_id}@example.com",
                "username": "Karyawan Dua",
                "role": "Karyawan",
            },
            {
                "email": f"pengelola1_{seed_id}@example.com",
                "username": "Pengelola Satu",
                "role": "Pengelola",
            },
        ]

        for emp_data in employees:
            employee = User.objects.create(
                email=emp_data["email"],
                username=emp_data["username"],
                role=emp_data["role"],
                toko=toko,
                is_active=True,
            )

        # Create pending invitations
        invitation_data = [
            {
                "email": f"invited1_{seed_id}@example.com",
                "name": "Calon Karyawan",
                "role": "Karyawan",
            },
            {
                "email": f"invited2_{seed_id}@example.com",
                "name": "Calon Pengelola",
                "role": "Pengelola",
            },
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
                expires_at=expiration,
            )
            
        # Save rollback information to JSON file
        try:
            from core.management.utils import save_rollback_info
            rollback_data = {
                "user_email": user.email,
                "toko_id": toko.id,
                "created_entities": {
                    "categories": created_categories,
                    "products": created_products,
                    "transactions": created_transactions,
                    "transaction_items": created_transaction_items,
                    "units": created_units,
                }
            }
            save_result, save_error = save_rollback_info(seed_id, json_path, rollback_data)
            if save_result:
                self.stdout.write(self.style.SUCCESS(f"JSON rollback data saved to: {json_path}"))
            else:
                self.stdout.write(self.style.ERROR(f"Error saving JSON rollback data: {save_error}"))
                
            # Create detailed rollback file similar to production mode
            with open(log_path, "a") as log_file:
                # Write some additional stats
                log_file.write("---\n")
                log_file.write(f"AFTER_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n")
                log_file.write(f"AFTER_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n")
                log_file.write(f"AFTER_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n")
                log_file.write("---\n")
                log_file.write(f"TOTAL_PRODUCTS: {len(created_products)}\n")
                log_file.write(f"TOTAL_CATEGORIES: {len(created_categories)}\n")
                log_file.write(f"TOTAL_TRANSACTIONS: {len(created_transactions)}\n")
                log_file.write(f"TOTAL_TRANSACTION_ITEMS: {len(created_transaction_items)}\n")
                
                # Write entity IDs for rollback script
                for category in created_categories:
                    log_file.write(f"CREATED_CATEGORY: {category['id']} {category['name']}\n")
                
                for product in created_products:
                    log_file.write(f"CREATED_PRODUCT: {product['id']} {product['name']}\n")
                
                for transaction in created_transactions:
                    if 'id' in transaction and 'type' in transaction and 'category' in transaction:
                        log_file.write(f"CREATED_TRANSACTION: {transaction['id']} {transaction['type']} {transaction['category']}\n")
                
                for item in created_transaction_items:
                    if 'id' in item and 'transaction_id' in item and 'product_id' in item and 'quantity' in item:
                        log_file.write(f"CREATED_TRANSACTION_ITEM: {item['id']} {item['transaction_id']} {item['product_id']} {item['quantity']}\n")
                
                for unit in created_units:
                    log_file.write(f"CREATED_UNIT: {unit['id']} {unit['name']}\n")
                    
            self.stdout.write(self.style.SUCCESS(f"Rollback log saved to: {log_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving rollback data: {str(e)}"))

    def seed_production_data(self, user, toko, seed_id):
        """Seed production data with enhanced rollback capability"""
        self.stdout.write(
            self.style.WARNING("Seeding production data with rollback capability...")
        )

        # Create rollback log file
        log_dir = settings.SEED_LOGS_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"rollback_{seed_id}.log")
        json_path = os.path.join(log_dir, f"rollback_{seed_id}.json")
        
        # Debug log creation
        self.stdout.write(self.style.SUCCESS(f"Creating log file at: {log_path}"))
        self.stdout.write(self.style.SUCCESS(f"Creating JSON file at: {json_path}"))

        # Initialize entity tracking containers
        created_categories = []
        created_products = []
        created_transactions = []
        created_transaction_items = []
        created_units = []

        with open(log_path, "w") as log_file:
            # Write metadata
            log_file.write(f"SEED_ID: {seed_id}\n")
            log_file.write(f"USER_EMAIL: {user.email}\n")
            log_file.write(f"TOKO_ID: {toko.id}\n")
            log_file.write(f"TIMESTAMP: {timezone.now().isoformat()}\n")
            log_file.write("---\n")

            # Log existing data counts for verification
            log_file.write(
                f"BEFORE_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"BEFORE_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n"
            )
            log_file.write("---\n")

            # Create categories
            categories = {}
            for cat_name in [
                "Makanan",
                "Minuman",
                "Snack",
                "Bahan Baku",
                "Pakaian",
                "Elektronik",
            ]:
                cat = KategoriProduk.objects.create(nama=cat_name, toko=toko)
                categories[cat_name] = cat
                # Track this category
                created_categories.append({"id": cat.id, "name": cat_name})
                log_file.write(f"CREATED_CATEGORY: {cat.id} {cat_name}\n")

            # Create units
            for unit in ["Pcs", "Box", "Kg", "Lusin", "Pack", "Botol", "Karton"]:
                obj, created = Satuan.objects.get_or_create(nama=unit)
                if created:
                    # Track only newly created units
                    created_units.append({"id": obj.id, "name": unit})
                    log_file.write(f"CREATED_UNIT: {obj.id} {unit}\n")

            # Create products (15 products for production environment)
            products = []
            product_data = [
                # Makanan
                {
                    "nama": "Nasi Goreng Spesial",
                    "modal": 12000,
                    "jual": 18000,
                    "stok": 50,
                    "satuan": "Pcs",
                    "kategori": "Makanan",
                },
                {
                    "nama": "Mie Goreng Spesial",
                    "modal": 10000,
                    "jual": 15000,
                    "stok": 45,
                    "satuan": "Pcs",
                    "kategori": "Makanan",
                },
                {
                    "nama": "Ayam Goreng",
                    "modal": 15000,
                    "jual": 22000,
                    "stok": 30,
                    "satuan": "Pcs",
                    "kategori": "Makanan",
                },
                # Minuman
                {
                    "nama": "Es Teh Manis",
                    "modal": 2000,
                    "jual": 5000,
                    "stok": 100,
                    "satuan": "Pcs",
                    "kategori": "Minuman",
                },
                {
                    "nama": "Es Jeruk",
                    "modal": 3000,
                    "jual": 6000,
                    "stok": 80,
                    "satuan": "Pcs",
                    "kategori": "Minuman",
                },
                {
                    "nama": "Kopi Hitam",
                    "modal": 4000,
                    "jual": 8000,
                    "stok": 60,
                    "satuan": "Pcs",
                    "kategori": "Minuman",
                },
                # Snack
                {
                    "nama": "Keripik Singkong",
                    "modal": 5000,
                    "jual": 8000,
                    "stok": 40,
                    "satuan": "Pack",
                    "kategori": "Snack",
                },
                {
                    "nama": "Kerupuk Udang",
                    "modal": 6000,
                    "jual": 10000,
                    "stok": 35,
                    "satuan": "Pack",
                    "kategori": "Snack",
                },
                # Bahan Baku
                {
                    "nama": "Tepung Terigu",
                    "modal": 8000,
                    "jual": 12000,
                    "stok": 20,
                    "satuan": "Kg",
                    "kategori": "Bahan Baku",
                },
                {
                    "nama": "Gula Pasir",
                    "modal": 12000,
                    "jual": 15000,
                    "stok": 25,
                    "satuan": "Kg",
                    "kategori": "Bahan Baku",
                },
                # Pakaian
                {
                    "nama": "Kaos Polos",
                    "modal": 25000,
                    "jual": 45000,
                    "stok": 15,
                    "satuan": "Pcs",
                    "kategori": "Pakaian",
                },
                {
                    "nama": "Kemeja",
                    "modal": 45000,
                    "jual": 85000,
                    "stok": 10,
                    "satuan": "Pcs",
                    "kategori": "Pakaian",
                },
                # Elektronik
                {
                    "nama": "Charger HP",
                    "modal": 15000,
                    "jual": 25000,
                    "stok": 12,
                    "satuan": "Pcs",
                    "kategori": "Elektronik",
                },
                {
                    "nama": "Earphone",
                    "modal": 20000,
                    "jual": 35000,
                    "stok": 8,
                    "satuan": "Pcs",
                    "kategori": "Elektronik",
                },
                {
                    "nama": "Powerbank",
                    "modal": 65000,
                    "jual": 120000,
                    "stok": 5,
                    "satuan": "Pcs",
                    "kategori": "Elektronik",
                },
            ]

            for data in product_data:
                product = Produk.objects.create(
                    nama=data["nama"],
                    harga_modal=Decimal(str(data["modal"])),
                    harga_jual=Decimal(str(data["jual"])),
                    stok=data["stok"],
                    satuan=data["satuan"],
                    kategori=categories[data["kategori"]],
                    toko=toko,
                )
                products.append(product)
                # Track created product
                created_products.append({
                    "id": product.id,
                    "name": product.nama,
                    "category_id": product.kategori.id
                })
                log_file.write(f"CREATED_PRODUCT: {product.id} {product.nama}\n")

            # Date range from February 1, 2025 to May 21, 2025
            start_date = datetime(2025, 2, 1)
            end_date = datetime(2025, 5, 21)

            # Create transactions with similar patterns to defined_data
            # Create different types of transactions with spread-out dates

            # 1. Completed sales (Pemasukan - Penjualan Barang) - 15 transactions
            for i in range(15):
                # Choose 1-3 products for this transaction
                selected_products = random.sample(products, random.randint(1, 3))
                total_amount = Decimal("0")
                total_modal = Decimal("0")

                # Generate a random date within the range
                days_diff = (end_date - start_date).days
                random_days = random.randint(0, days_diff)
                random_hours = random.randint(0, 23)
                random_minutes = random.randint(0, 59)
                transaction_date = start_date + timedelta(
                    days=random_days, hours=random_hours, minutes=random_minutes
                )

                # Create the transaction
                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pemasukan",
                    category="Penjualan Barang",
                    total_amount=0,
                    total_modal=0,
                    amount=0,
                    status="Lunas",
                )
                
                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                
                # Refresh the object after the update
                transaksi.refresh_from_db()
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pemasukan",
                    "category": "Penjualan Barang"
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pemasukan Penjualan_Barang\n"
                )

                for product in selected_products:
                    quantity = random.randint(1, 3)

                    item = TransaksiItem.objects.create(
                        transaksi=transaksi,
                        product=product,
                        quantity=quantity,
                        harga_jual_saat_transaksi=product.harga_jual,
                        harga_modal_saat_transaksi=product.harga_modal,
                    )
                    
                    # Track transaction item
                    created_transaction_items.append({
                        "id": item.id,
                        "transaction_id": transaksi.id,
                        "product_id": product.id,
                        "quantity": quantity
                    })

                    log_file.write(
                        f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n"
                    )

                    item_total = product.harga_jual * quantity
                    item_modal = product.harga_modal * quantity
                    total_amount += item_total
                    total_modal += item_modal

                    original_stock = product.stok
                    product.stok -= quantity
                    product.save()
                    log_file.write(
                        f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n"
                    )

                transaksi.total_amount = total_amount
                transaksi.total_modal = total_modal
                transaksi.amount = total_amount
                transaksi.save()
                log_file.write(
                    f"UPDATED_TRANSACTION_TOTALS: {transaksi.id} {total_amount} {total_modal}\n"
                )

            # 2. Unpaid sales (status="Belum Lunas") - 8 transactions
            for i in range(8):
                selected_products = random.sample(products, random.randint(1, 2))
                total_amount = Decimal("0")
                total_modal = Decimal("0")

                # Generate a random date within the range, more recent
                later_start = start_date + timedelta(days=70)
                days_diff = (end_date - later_start).days
                random_days = random.randint(0, days_diff) if days_diff > 0 else 0
                transaction_date = later_start + timedelta(days=random_days)

                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pemasukan",
                    category="Penjualan Barang",
                    total_amount=0,
                    total_modal=0,
                    amount=0,
                    status="Belum Lunas",
                )

                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                transaksi.refresh_from_db()
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pemasukan",
                    "category": "Penjualan Barang"
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pemasukan Penjualan_Barang_BelumLunas\n"
                )

                for product in selected_products:
                    quantity = random.randint(1, 2)

                    item = TransaksiItem.objects.create(
                        transaksi=transaksi,
                        product=product,
                        quantity=quantity,
                        harga_jual_saat_transaksi=product.harga_jual,
                        harga_modal_saat_transaksi=product.harga_modal,
                    )
                    
                    # Track transaction item
                    created_transaction_items.append({
                        "id": item.id,
                        "transaction_id": transaksi.id,
                        "product_id": product.id,
                        "quantity": quantity
                    })

                    log_file.write(
                        f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n"
                    )

                    item_total = product.harga_jual * quantity
                    item_modal = product.harga_modal * quantity
                    total_amount += item_total
                    total_modal += item_modal

                    original_stock = product.stok
                    product.stok -= quantity
                    product.save()
                    log_file.write(
                        f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n"
                    )

                transaksi.total_amount = total_amount
                transaksi.total_modal = total_modal
                transaksi.amount = total_amount
                transaksi.save()
                log_file.write(
                    f"UPDATED_TRANSACTION_TOTALS: {transaksi.id} {total_amount} {total_modal}\n"
                )

            # 3. Stock purchases (Pengeluaran - Pembelian Stok) - 12 transactions
            for i in range(12):
                product = random.choice(products)
                quantity = random.randint(5, 15)
                total_amount = product.harga_modal * quantity

                # Generate a random date within the range
                days_diff = (end_date - start_date).days
                random_days = random.randint(0, days_diff)
                transaction_date = start_date + timedelta(days=random_days)

                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pengeluaran",
                    category="Pembelian Stok",
                    total_amount=total_amount,
                    total_modal=0,
                    amount=total_amount,
                    status="Lunas",
                )

                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                transaksi.refresh_from_db()
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pengeluaran",
                    "category": "Pembelian Stok"
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pengeluaran Pembelian_Stok\n"
                )

                item = TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=0,
                    harga_modal_saat_transaksi=product.harga_modal,
                )
                
                # Track transaction item
                created_transaction_items.append({
                    "id": item.id,
                    "transaction_id": transaksi.id,
                    "product_id": product.id,
                    "quantity": quantity
                })

                log_file.write(
                    f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n"
                )

                original_stock = product.stok
                product.stok += quantity
                product.save()
                log_file.write(
                    f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n"
                )

            # 4. Unpaid purchases (Pengeluaran - Pembelian Stok - Belum Lunas) - 6 transactions
            for i in range(6):
                product = random.choice(products)
                quantity = random.randint(10, 20)
                total_amount = product.harga_modal * quantity

                # Generate a random date within the range, more recent
                later_start = start_date + timedelta(days=60)
                days_diff = (end_date - later_start).days
                random_days = random.randint(0, days_diff) if days_diff > 0 else 0
                transaction_date = later_start + timedelta(days=random_days)

                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pengeluaran",
                    category="Pembelian Stok",
                    total_amount=total_amount,
                    total_modal=0,
                    amount=total_amount,
                    status="Belum Lunas",
                )

                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                transaksi.refresh_from_db()
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pengeluaran",
                    "category": "Pembelian Stok"
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pengeluaran Pembelian_Stok_BelumLunas\n"
                )

                item = TransaksiItem.objects.create(
                    transaksi=transaksi,
                    product=product,
                    quantity=quantity,
                    harga_jual_saat_transaksi=0,
                    harga_modal_saat_transaksi=product.harga_modal,
                )
                
                # Track transaction item
                created_transaction_items.append({
                    "id": item.id,
                    "transaction_id": transaksi.id,
                    "product_id": product.id,
                    "quantity": quantity
                })

                log_file.write(
                    f"CREATED_TRANSACTION_ITEM: {item.id} {transaksi.id} {product.id} {quantity}\n"
                )

                original_stock = product.stok
                product.stok += quantity
                product.save()
                log_file.write(
                    f"UPDATED_PRODUCT_STOCK: {product.id} {original_stock} {product.stok}\n"
                )

            # 5. Other expenses (Pengeluaran - various categories) - 10 transactions
            expense_categories = [
                "Biaya Operasional",
                "Biaya Sewa",
                "Biaya Gaji",
                "Biaya Utilitas",
            ]
            for i in range(10):
                category = random.choice(expense_categories)
                amount = Decimal(str(random.randint(50, 300) * 1000))

                # Generate a random date within the range
                days_diff = (end_date - start_date).days
                random_days = random.randint(0, days_diff)
                transaction_date = start_date + timedelta(days=random_days)

                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pengeluaran",
                    category=category,
                    total_amount=amount,
                    total_modal=0,
                    amount=amount,
                    status="Lunas",
                )

                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pengeluaran",
                    "category": category
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pengeluaran {category}\n"
                )

            # 6. Other income (Pemasukan - various categories) - 10 transactions
            income_categories = [
                "Pendapatan Lain-Lain",
                "Pendapatan Pinjaman",
                "Pendapatan Investasi",
            ]
            for i in range(10):
                category = random.choice(income_categories)
                amount = Decimal(str(random.randint(50, 200) * 1000))

                # Generate a random date within the range
                days_diff = (end_date - start_date).days
                random_days = random.randint(0, days_diff)
                transaction_date = start_date + timedelta(days=random_days)

                transaksi = Transaksi.objects.create(
                    toko=toko,
                    created_by=user,
                    transaction_type="pemasukan",
                    category=category,
                    total_amount=amount,
                    total_modal=0,
                    amount=amount,
                    status="Lunas",
                )

                # Update the created_at date
                Transaksi.objects.filter(id=transaksi.id).update(
                    created_at=transaction_date
                )
                
                # Track transaction
                created_transactions.append({
                    "id": transaksi.id,
                    "type": "Pemasukan",
                    "category": category
                })

                log_file.write(
                    f"CREATED_TRANSACTION: {transaksi.id} Pemasukan {category}\n"
                )

            # Create another user (employees) for the same toko
            employees = [
                {
                    "email": f"karyawan1_{seed_id}@example.com",
                    "username": "Karyawan Satu",
                    "role": "Karyawan",
                },
                {
                    "email": f"pengelola1_{seed_id}@example.com",
                    "username": "Pengelola Satu",
                    "role": "Pengelola",
                },
            ]

            for emp_data in employees:
                employee = User.objects.create(
                    email=emp_data["email"],
                    username=emp_data["username"],
                    role=emp_data["role"],
                    toko=toko,
                    is_active=True,
                )

            # Create pending invitations
            invitation_data = [
                {
                    "email": f"invited1_{seed_id}@example.com",
                    "name": "Calon Karyawan",
                    "role": "Karyawan",
                },
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
                    expires_at=expiration,
                )

            log_file.write("---\n")
            log_file.write(
                f"AFTER_PRODUCTS: {Produk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"AFTER_CATEGORIES: {KategoriProduk.objects.filter(toko=toko).count()}\n"
            )
            log_file.write(
                f"AFTER_TRANSACTIONS: {Transaksi.objects.filter(toko=toko).count()}\n"
            )

        # Create detailed rollback file
        try:
            with open(log_path, "a") as log_file:
                # Write some additional stats
                log_file.write(f"TOTAL_PRODUCTS: {len(created_products)}\n")
                log_file.write(f"TOTAL_CATEGORIES: {len(created_categories)}\n")
                log_file.write(f"TOTAL_TRANSACTIONS: {len(created_transactions)}\n")
                log_file.write(f"TOTAL_TRANSACTION_ITEMS: {len(created_transaction_items)}\n")
            
            # Save detailed rollback info to JSON file
            try:
                from core.management.utils import save_rollback_info
                rollback_data = {
                    "user_email": user.email,
                    "toko_id": toko.id,
                    "created_entities": {
                        "categories": created_categories,
                        "products": created_products,
                        "transactions": created_transactions,
                        "transaction_items": created_transaction_items,
                        "units": created_units,
                    }
                }
                save_result, save_error = save_rollback_info(seed_id, json_path, rollback_data)
                if save_result:
                    self.stdout.write(self.style.SUCCESS(f"JSON rollback data saved to: {json_path}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Error saving JSON rollback data: {save_error}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving JSON rollback data: {str(e)}"))
                
            self.stdout.write(
                self.style.SUCCESS(
                    f"Production data seeded with rollback log at: {log_path}"
                )
            )
            
        except IOError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error writing to rollback log: {str(e)}"
                )
            )

    def rollback_seeding(self, seed_id):
        """Rollback a previous seeding operation using detailed entity logs"""
        self.stdout.write(self.style.WARNING(f"Rolling back seed operation: {seed_id}"))

        # Find the rollback log file
        log_dir = settings.SEED_LOGS_DIR
        log_path = os.path.join(log_dir, f"rollback_{seed_id}.log")
        
        self.stdout.write(self.style.SUCCESS(f"Looking for rollback log at: {log_path}"))

        if not os.path.exists(log_path):
            # Try checking for alternative log path formats
            alt_log_path = os.path.join(log_dir, f"rollback_{seed_id.replace('seed_', '')}.log")
            self.stdout.write(self.style.WARNING(f"Log not found. Checking alternative path: {alt_log_path}"))
            
            if os.path.exists(alt_log_path):
                self.stdout.write(self.style.SUCCESS(f"Found alternative log at: {alt_log_path}"))
                log_path = alt_log_path
            else:
                raise CommandError(f"Rollback log not found: {log_path} or {alt_log_path}")

        with transaction.atomic():
            # Parse the log file
            with open(log_path, "r") as log_file:
                lines = log_file.readlines()

                # Extract basic info
                metadata = {}
                created_entities = {
                    "CREATED_TRANSACTION": [],
                    "CREATED_TRANSACTION_ITEM": [],
                    "CREATED_PRODUCT": [],
                    "CREATED_CATEGORY": [],
                    "CREATED_UNIT": [],
                }
                
                # Parse each line of the log file
                for line in lines:
                    line = line.strip()
                    
                    # Extract metadata
                    if ": " in line and not any(prefix in line for prefix in created_entities.keys()):
                        key, value = line.strip().split(": ", 1)
                        metadata[key] = value
                        continue
                        
                    # Extract created entities
                    for entity_type in created_entities.keys():
                        if line.startswith(entity_type):
                            # Extract the ID from the line
                            parts = line[len(entity_type) + 1:].strip().split(" ", 1)
                            if len(parts) > 0:
                                entity_id = parts[0]
                                created_entities[entity_type].append(entity_id)
                            break

                # Check if we have the necessary metadata
                if "USER_EMAIL" not in metadata or "TOKO_ID" not in metadata:
                    raise CommandError("Invalid rollback log: missing metadata")

                user_email = metadata["USER_EMAIL"]
                toko_id = int(metadata["TOKO_ID"])

                # Find the user and toko
                try:
                    user = User.objects.get(email=user_email)
                    toko = Toko.objects.get(id=toko_id)
                except (User.DoesNotExist, Toko.DoesNotExist):
                    raise CommandError(f"User {user_email} or Toko {toko_id} not found")

                self.stdout.write(self.style.SUCCESS(f"Found toko with ID: {toko_id} for user: {user_email}"))
                
                # Delete the created data in reverse order (specific entities)
                transaction_count = 0
                transaction_item_count = 0
                product_count = 0
                category_count = 0
                unit_count = 0
                
                # Try precise deletion first based on stored IDs
                if created_entities["CREATED_TRANSACTION_ITEM"]:
                    for item_id in created_entities["CREATED_TRANSACTION_ITEM"]:
                        try:
                            # Try to extract just the ID if there are additional parts
                            if " " in item_id:
                                item_id = item_id.split(" ")[0]
                            TransaksiItem.objects.filter(id=item_id).delete()
                            transaction_item_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error deleting transaction item {item_id}: {str(e)}"))
                
                if created_entities["CREATED_TRANSACTION"]:
                    for transaction_id in created_entities["CREATED_TRANSACTION"]:
                        try:
                            # Try to extract just the ID if there are additional parts
                            if " " in transaction_id:
                                transaction_id = transaction_id.split(" ")[0]
                            Transaksi.objects.filter(id=transaction_id).delete()
                            transaction_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error deleting transaction {transaction_id}: {str(e)}"))
                
                if created_entities["CREATED_PRODUCT"]:
                    for product_id in created_entities["CREATED_PRODUCT"]:
                        try:
                            # Try to extract just the ID if there are additional parts
                            if " " in product_id:
                                product_id = product_id.split(" ")[0]
                            Produk.objects.filter(id=product_id).delete()
                            product_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error deleting product {product_id}: {str(e)}"))
                
                if created_entities["CREATED_CATEGORY"]:
                    for category_id in created_entities["CREATED_CATEGORY"]:
                        try:
                            # Try to extract just the ID if there are additional parts
                            if " " in category_id:
                                category_id = category_id.split(" ")[0]
                            KategoriProduk.objects.filter(id=category_id).delete()
                            category_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error deleting category {category_id}: {str(e)}"))
                
                if created_entities["CREATED_UNIT"]:
                    for unit_id in created_entities["CREATED_UNIT"]:
                        try:
                            # Try to extract just the ID if there are additional parts
                            if " " in unit_id:
                                unit_id = unit_id.split(" ")[0]
                            Satuan.objects.filter(id=unit_id).delete()
                            unit_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error deleting unit {unit_id}: {str(e)}"))
                
                # If precise deletion didn't delete much, fall back to toko-based deletion
                if transaction_count == 0 and product_count == 0 and category_count == 0:
                    self.stdout.write(self.style.WARNING("Precise deletion failed, falling back to toko-based deletion"))
                    
                    # Fetch counts before deletion
                    transaction_items_before = TransaksiItem.objects.filter(transaksi__toko=toko).count()
                    transactions_before = Transaksi.objects.filter(toko=toko).count()
                    products_before = Produk.objects.filter(toko=toko).count()
                    categories_before = KategoriProduk.objects.filter(toko=toko).count()
                    
                    # Delete related data
                    TransaksiItem.objects.filter(transaksi__toko=toko).delete()
                    Transaksi.objects.filter(toko=toko).delete()
                    Produk.objects.filter(toko=toko).delete()
                    KategoriProduk.objects.filter(toko=toko).delete()
                    
                    # Update counts for reporting
                    transaction_item_count = transaction_items_before
                    transaction_count = transactions_before
                    product_count = products_before
                    category_count = categories_before
                
                # Do not remove units as they are global (we only delete the specifically created ones)
                
                # Report success
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully rolled back seed operation: {seed_id}\n"
                        f"Deleted {transaction_item_count} transaction items\n"
                        f"Deleted {transaction_count} transactions\n"
                        f"Deleted {product_count} products\n"
                        f"Deleted {category_count} categories\n"
                        f"Deleted {unit_count} units"
                    )
                )

                # Rename the log file to indicate it's been rolled back
                os.rename(log_path, log_path + ".rolled_back")