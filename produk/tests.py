from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
import json
from unittest.mock import patch

from produk.models import Produk, KategoriProduk
from produk.schemas import ProdukResponseSchema, CreateProdukSchema, PaginatedResponseSchema


class KategoriProdukModelTest(TestCase):
    def test_string_representation(self):
        kategori = KategoriProduk(nama="Minuman")
        self.assertEqual(str(kategori), "Minuman")
        
    def test_create_kategori(self):
        kategori = KategoriProduk.objects.create(nama="Makanan")
        self.assertEqual(kategori.nama, "Makanan")


class ProdukModelTest(TestCase):
    def setUp(self):
        self.kategori = KategoriProduk.objects.create(nama="Minuman")
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'',
            content_type='image/jpeg'
        )
        
    def test_string_representation(self):
        produk = Produk(
            nama="Coca Cola",
            foto=self.test_image,
            harga_modal=Decimal('5000'),
            harga_jual=Decimal('7000'),
            stok=Decimal('10'),
            satuan="Botol",
            kategori=self.kategori
        )
        self.assertEqual(str(produk), "Coca Cola")
        
    def test_create_produk(self):
        produk = Produk.objects.create(
            nama="Sprite",
            foto=self.test_image,
            harga_modal=Decimal('4500'),
            harga_jual=Decimal('6500'),
            stok=Decimal('15'),
            satuan="Botol",
            kategori=self.kategori
        )
        self.assertEqual(produk.nama, "Sprite")
        self.assertEqual(produk.harga_modal, Decimal('4500'))
        self.assertEqual(produk.kategori, self.kategori)


class SchemasTest(TestCase):
    def setUp(self):
        self.kategori = KategoriProduk.objects.create(nama="Snack")
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'',
            content_type='image/jpeg'
        )
        self.produk = Produk.objects.create(
            nama="Chitato",
            foto=self.test_image,
            harga_modal=Decimal('8000'),
            harga_jual=Decimal('10000'),
            stok=Decimal('20'),
            satuan="Bungkus",
            kategori=self.kategori
        )
        
    def test_produk_response_schema_from_orm(self):
        schema = ProdukResponseSchema.from_orm(self.produk)
        self.assertEqual(schema.nama, "Chitato")
        self.assertEqual(schema.harga_modal, float(8000))
        self.assertEqual(schema.kategori, "Snack")
        
    def test_create_produk_schema_validators(self):
        # Valid schema
        schema = CreateProdukSchema(
            nama="Test Product",
            harga_modal=5000,
            harga_jual=7000,
            stok=10,
            satuan="Pcs",
            kategori="Test"
        )
        self.assertEqual(schema.nama, "Test Product")
        
        # Invalid harga_modal
        with self.assertRaises(ValueError):
            CreateProdukSchema(
                nama="Test Product",
                harga_modal=-5000,
                harga_jual=7000,
                stok=10,
                satuan="Pcs",
                kategori="Test"
            )
            
        # Invalid harga_jual
        with self.assertRaises(ValueError):
            CreateProdukSchema(
                nama="Test Product",
                harga_modal=5000,
                harga_jual=-7000,
                stok=10,
                satuan="Pcs",
                kategori="Test"
            )
            
        # Invalid stok
        with self.assertRaises(ValueError):
            CreateProdukSchema(
                nama="Test Product",
                harga_modal=5000,
                harga_jual=7000,
                stok=-10,
                satuan="Pcs",
                kategori="Test"
            )


class ProdukAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_url = "/api/produk"  # Adjust based on your actual URL configuration
        
        self.kategori1 = KategoriProduk.objects.create(nama="Minuman")
        self.kategori2 = KategoriProduk.objects.create(nama="Makanan")
        
        # Create test products
        for i in range(1, 16):  # Create 15 products for pagination testing
            stok = 5 if i <= 3 else 20  # Create some products with low stock
            Produk.objects.create(
                nama=f"Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f'{i}000'),
                harga_jual=Decimal(f'{i+2}000'),
                stok=Decimal(stok),
                satuan="Pcs",
                kategori=self.kategori1 if i % 2 == 0 else self.kategori2
            )
        
        # Get a specific product for testing
        self.test_product = Produk.objects.first()
            
    def test_get_produk_default(self):
        response = self.client.get(f"{self.api_url}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['page'], 1)
        self.assertEqual(len(data['items']), 7)  # default per_page is 7
        
    def test_get_produk_default_with_sort_asc(self):
        response = self.client.get(f"{self.api_url}?sort=asc")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Check that products are sorted by stok ascending
        for i in range(len(data['items']) - 1):
            self.assertTrue(data['items'][i]['stok'] <= data['items'][i+1]['stok'])
            
    def test_get_produk_default_with_sort_desc(self):
        response = self.client.get(f"{self.api_url}?sort=desc")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Check that products are sorted by stok descending
        for i in range(len(data['items']) - 1):
            self.assertTrue(data['items'][i]['stok'] >= data['items'][i+1]['stok'])
    
    def test_get_produk_default_with_invalid_sort(self):
        response = self.client.get(f"{self.api_url}?sort=invalid")
        self.assertEqual(response.status_code, 400)
        
    def test_get_produk_paginated(self):
        response = self.client.get(f"{self.api_url}/page/2")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['page'], 2)
        
    def test_get_produk_paginated_with_per_page(self):
        response = self.client.get(f"{self.api_url}/page/1?per_page=5")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 5)
        self.assertEqual(data['per_page'], 5)
        
    def test_get_produk_paginated_with_invalid_per_page(self):
        response = self.client.get(f"{self.api_url}/page/1?per_page=invalid")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['per_page'], 7)  # Default value
        
    def test_get_produk_paginated_page_not_found(self):
        response = self.client.get(f"{self.api_url}/page/100")
        self.assertEqual(response.status_code, 404)
        
    def test_create_produk(self):
        payload = {
            "nama": "New Product",
            "foto": "new_product.jpg",
            "harga_modal": 15000,
            "harga_jual": 20000,
            "stok": 25,
            "satuan": "Box",
            "kategori": "New Category"
        }
        response = self.client.post(
            f"{self.api_url}/create", 
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['nama'], "New Product")
        self.assertEqual(data['kategori'], "New Category")
        
        # Check that the category was created
        self.assertTrue(KategoriProduk.objects.filter(nama="New Category").exists())
        
    def test_delete_produk(self):
        product_id = self.test_product.id
        response = self.client.delete(f"{self.api_url}/delete/{product_id}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['message'], "Produk berhasil dihapus")
        self.assertFalse(Produk.objects.filter(id=product_id).exists())
        
    def test_delete_produk_not_found(self):
        response = self.client.delete(f"{self.api_url}/delete/9999")
        self.assertEqual(response.status_code, 404)
        
    def test_search_produk(self):
        # Search with a term that should match
        response = self.client.get(f"{self.api_url}/search?q=Produk")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(len(data) > 0)
        
        # Search with a term that shouldn't match
        response = self.client.get(f"{self.api_url}/search?q=NonExistingProduct")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)
        
    def test_get_low_stock_products(self):
        response = self.client.get(f"{self.api_url}/low-stock")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(len(data) > 0)
        # Check that all returned products have stock less than 10
        for product in data:
            self.assertTrue(product['stok'] < 10)


class PaginationEdgeCasesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_url = "/api/produk"
        
    def test_empty_database_pagination(self):
        # Test pagination when no products exist
        response = self.client.get(f"{self.api_url}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['total_pages'], 0)
        self.assertEqual(len(data['items']), 0)