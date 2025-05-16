from locust import HttpUser, task, between
import json
import random

class ProductUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        self.created_product_ids = []  # Store created product IDs per user
        # Simulate Google OAuth session data
        random_int = random.randint(1, 1000)
        session_data = {
            "user": {
                "email": f"testuser{random_int}@gmail.com",
                "name": f"Test User {random_int}",
                "picture": "https://example.com/profile.jpg",
                "sub": f"google_id_{random_int}"
            }
        }

        with self.client.post("/api/auth/process-session", json=session_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                # Mark the request as failed
                response.failure(f"Failed to login: {response.status_code}, {response.text}")
                self.token = None
                self.headers = {}

    @task(3)
    def get_products(self):
        # Test getting paginated products
        page = random.randint(1, 5)
        sort_options = ["stok", "-stok", "-id", None]
        sort = random.choice(sort_options)
        
        params = {"page": page}
        if sort:
            params["sort"] = sort
        
        self.client.get("/api/produk/page/1", 
                        params=params,
                        headers=self.headers)

    @task(1)
    def create_product(self):
        # Test creating a new product
        payload = {
            "nama": f"Test Product {random.randint(1, 1000)}",
            "harga_modal": random.uniform(1000.0, 10000.0),
            "harga_jual": random.uniform(11000.0, 20000.0),
            "stok": random.uniform(1.0, 100.0),
            "satuan": random.choice(["Pcs", "Box", "Kg"]),
            "kategori": random.choice(["Makanan", "Minuman", "Snack"]), 
        }
        form_data = {"payload": json.dumps(payload)}
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        with self.client.post("/api/produk/create",
                        data=form_data,
                        headers=headers,
                        catch_response=True) as response:
            print(f"CREATE RESPONSE: {response.status_code} {response.text}")
            if response.status_code == 201:
                data = response.json()
                product_id = data.get("id")
                print(f"Created product ID: {product_id}")
                if product_id:
                    self.created_product_ids.append(product_id)
            else:
                response.failure(f"Failed to create product: {response.status_code}, {response.text}")
    @task(1)
    def update_product(self):
        # Test updating a product using created product IDs
        if not self.created_product_ids:
            print("No products to update!")
            return
        product_id = random.choice(self.created_product_ids)
        update_data = {
            "nama": f"Updated Product {random.randint(1, 1000)}",
            "harga_modal": round(random.uniform(1000.0, 10000.0), 2),
            "harga_jual": round(random.uniform(11000.0, 20000.0), 2),
            "stok": round(random.uniform(1.0, 100.0), 2),
            "satuan": random.choice(["Pcs", "Box", "Kg"]),
            "kategori": random.choice(["Makanan", "Minuman", "Snack"]),
        }
        form_data = {"payload": json.dumps(update_data)}
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        with self.client.post(f"/api/produk/update/{product_id}",
                        data=form_data,
                        headers=headers,
                        catch_response=True) as response:
            print(f"UPDATE RESPONSE for {product_id}: {response.status_code} {response.text}")
            if response.status_code != 200:
                response.failure(f"Failed to update product: {response.status_code}, {response.text}")

    @task(2)
    def get_low_stock_products(self):
        # Test getting low stock products
        self.client.get("/api/produk/low-stock",
                       headers=self.headers)

    @task(2)
    def get_most_popular_products(self):
        # Test getting most popular products
        self.client.get("/api/produk/most-popular",
                       headers=self.headers)

    @task(1)
    def get_categories(self):
        # Test getting product categories
        self.client.get("/api/produk/categories",
                       headers=self.headers)

    @task(1)
    def get_units(self):
        # Test getting product units
        self.client.get("/api/produk/units",
                       headers=self.headers)
