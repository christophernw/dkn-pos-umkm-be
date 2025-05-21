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

            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pemasukan",
                "category": "Penjualan Barang"
            })

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
            
            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pemasukan",
                "category": "Penjualan Barang"
            })

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

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
            
            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pengeluaran",
                "category": "Pembelian Stok"
            })

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

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
            
            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pengeluaran",
                "category": "Pembelian Stok"
            })

            # Update the created_at date
            Transaksi.objects.filter(id=transaksi.id).update(
                created_at=transaction_date
            )
            transaksi.refresh_from_db()

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
            
            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pengeluaran",
                "category": category
            })

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
            
            # Track transaction
            created_transactions.append({
                "id": transaksi.id,
                "type": "Pemasukan",
                "category": category
            })

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
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving JSON rollback data: {str(e)}"))
