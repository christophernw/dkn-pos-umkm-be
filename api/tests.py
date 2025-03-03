from django.test import TestCase
from api.models import Product
from django.urls import reverse

class ProductUpdateTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Produk A",
            price=10000,
            stock=10,
            category="Elektronik"
        )

    def test_update_product(self):
        response = self.client.put(
            f"/api/products/{self.product.id}",
            {"name": "Produk A - Update", "price": 12000, "stock": 8, "category": "Gadget"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Produk A - Update")
        self.assertEqual(self.product.price, 12000)
        self.assertEqual(self.product.stock, 8)

class ProductUpdateNegativeTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Produk A",
            price=10000,
            stock=10,
            category="Elektronik"
        )

    def test_update_product_not_found(self):
        """ Coba update produk yang tidak ada, harus gagal dengan 404 """
        response = self.client.put(
            f"/api/products/999/",
            {"name": "Produk Tidak Ada", "price": 5000, "stock": 5, "category": "Gadget"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

    def test_update_product_invalid_price(self):
        """ Coba update dengan harga negatif, harus gagal dengan 400 """
        response = self.client.put(
            f"/api/products/{self.product.id}/",
            {"name": "Produk A", "price": -5000, "stock": 5, "category": "Gadget"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_update_product_invalid_stock(self):
        """ Coba update dengan stok negatif, harus gagal dengan 400 """
        response = self.client.put(
            f"/api/products/{self.product.id}/",
            {"name": "Produk A", "price": 5000, "stock": -5, "category": "Gadget"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)