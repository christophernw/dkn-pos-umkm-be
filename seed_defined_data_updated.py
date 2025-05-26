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
