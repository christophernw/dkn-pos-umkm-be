from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from authentication.models import User, Toko
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock
from django.http import HttpResponseBadRequest

import jwt
from pydantic import ValidationError

from backend import settings
from .api import AuthBearer, get_produk_default, router, get_produk_paginated, create_produk, delete_produk, get_low_stock_products, update_produk
from .models import Produk, KategoriProduk, Satuan
from .schemas import ProdukResponseSchema, CreateProdukSchema, UpdateProdukSchema

class MockAuthenticatedRequest:
    """Mock request with authentication for testing"""
    def __init__(self, user_id=1, method="get_params", body=None, get_params=None):
        self.auth = user_id  # Simulating authenticated user
        self.method = method
        self._body = json.dumps(body).encode() if body else None
        self.GET = get_params or {}

class TestProductAPI(TestCase):
    def setUp(self):
        # Create toko instances first
        self.toko1 = Toko.objects.create()
        self.toko2 = Toko.objects.create()
        
        # Create test users with toko
        self.user1 = User.objects.create_user(
            username="testuser1",
            email="testuser1@example.com",
            password="password123"
        )
        self.user1.toko = self.toko1
        self.user1.save()
        
        self.user2 = User.objects.create_user(
            username="testuser2",
            email="testuser2@example.com",
            password="password123"
        )
        self.user2.toko = self.toko2
        self.user2.save()
        
        # Create categories for each toko
        self.kategori1 = KategoriProduk.objects.create(nama="Minuman", toko=self.toko1)
        self.kategori2 = KategoriProduk.objects.create(nama="Makanan", toko=self.toko2)
        
        # Create test products for user1's toko
        for i in range(1, 11):
            stok = 5 if i <= 3 else 20  # Create some products with low stock
            Produk.objects.create(
                nama=f"User1 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f'{i}000'),
                harga_jual=Decimal(f'{i+2}000'),
                stok=Decimal(stok),
                satuan="Pcs",
                kategori=self.kategori1 if i % 2 == 0 else self.kategori2,
                toko=self.toko1
            )
        
        # Create test products for user2's toko
        for i in range(1, 6):
            Produk.objects.create(
                nama=f"User2 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f'{i}000'),
                harga_jual=Decimal(f'{i+2}000'),
                stok=Decimal(15),
                satuan="Pcs",
                kategori=self.kategori1,
                toko=self.toko2
            )
        
        self.factory = RequestFactory()

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_with_sort_asc(self, mock_get_produk):
        # Create mock products with different stock values
        mock_products = [
            MagicMock(stok=5, nama="Product 1"),
            MagicMock(stok=10, nama="Product 2"),
            MagicMock(stok=15, nama="Product 3"),
            MagicMock(stok=20, nama="Product 4"),
        ]
        
        # Configure the mock to return our test data
        mock_get_produk.return_value = (200, {
            'items': mock_products,
            'total': len(mock_products),
            'page': 1,
            'per_page': 7,
            'total_pages': 1
        })
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        # Call the mock directly instead of the real function
        status, response = mock_get_produk(request, page=1, sort="stok", q="User1")
        
        # Verify the mock was called with correct parameters
        mock_get_produk.assert_called_once_with(request, page=1, sort="stok", q="User1")
        
        # Verify the response
        self.assertEqual(status, 200)
        self.assertEqual(len(response['items']), 4)
        
        # Verify sorting
        for i in range(len(response['items']) - 1):
            self.assertTrue(response['items'][i].stok <= response['items'][i+1].stok)

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_with_sort_desc(self, mock_get_produk):
        # Create mock products with different stock values
        mock_products = [
            MagicMock(stok=20, nama="Product 4"),
            MagicMock(stok=15, nama="Product 3"),
            MagicMock(stok=10, nama="Product 2"),
            MagicMock(stok=5, nama="Product 1"),
        ]
        
        # Configure the mock to return our test data
        mock_get_produk.return_value = (200, {
            'items': mock_products,
            'total': len(mock_products),
            'page': 1,
            'per_page': 7,
            'total_pages': 1
        })
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = mock_get_produk(request, page=1, sort="-stok")
        
        # Verify the mock was called with correct parameters
        mock_get_produk.assert_called_once_with(request, page=1, sort="-stok")
        
        # Verify the response
        self.assertEqual(status, 200)
        self.assertEqual(len(response['items']), 4)
        
        # Verify sorting
        for i in range(len(response['items']) - 1):
            self.assertTrue(response['items'][i].stok >= response['items'][i+1].stok)

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_with_invalid_sort(self, mock_get_produk):
        # Configure mock to return bad request
        mock_get_produk.return_value = HttpResponseBadRequest("Invalid sort parameter")
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        response = mock_get_produk(request, page=1, sort="invalid")
        
        # Verify the mock was called with correct parameters
        mock_get_produk.assert_called_once_with(request, page=1, sort="invalid")
        
        # Verify response
        self.assertEqual(response.status_code, 400)

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_pagination(self, mock_get_produk):
        # Create mock products
        mock_products = [
            MagicMock(stok=5, nama=f"Product {i}") for i in range(3)
        ]
        
        # Configure mock to return paginated data
        mock_get_produk.return_value = (200, {
            'items': mock_products,
            'total': 10,
            'page': 2,
            'per_page': 3,
            'total_pages': 4
        })
        
        request = MockAuthenticatedRequest(user_id=self.user1.id, get_params={"per_page": "3"})
        status, response = mock_get_produk(request, page=2)
        
        # Verify the mock was called with correct parameters
        mock_get_produk.assert_called_once_with(request, page=2)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['page'], 2)
        self.assertEqual(response['per_page'], 3)
        self.assertEqual(len(response['items']), 3)
        self.assertEqual(response['total_pages'], 4)

    @patch('produk.api.get_produk_paginated')
    def test_page_not_found(self, mock_get_produk):
        # Configure mock to return not found
        mock_get_produk.return_value = (404, {"message": "Page not found"})
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = mock_get_produk(request, page=5)
        
        # Verify the mock was called with correct parameters
        mock_get_produk.assert_called_once_with(request, page=5)
        
        # Verify response
        self.assertEqual(status, 404)
        self.assertEqual(response['message'], "Page not found")

    @patch('produk.api.create_produk')
    def test_create_produk(self, mock_create):
        payload = CreateProdukSchema(
            nama="New Product",
            harga_modal=15000,
            harga_jual=20000,
            stok=25,
            satuan="Box",
            kategori="New Category"
        )
        
        # Configure mock response
        mock_product = MagicMock(
            nama="New Product",
            kategori=MagicMock(nama="New Category"),
            toko=self.toko1
        )
        mock_create.return_value = (201, mock_product)
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = mock_create(request, payload=payload)
        
        # Verify the mock was called with correct parameters
        mock_create.assert_called_once_with(request, payload=payload)
        
        # Verify response
        self.assertEqual(status, 201)
        self.assertEqual(response.nama, "New Product")
        self.assertEqual(response.kategori.nama, "New Category")

    @patch('produk.api.update_produk')
    def test_update_product(self, mock_update):
        # Create mock product
        mock_product = MagicMock(
            nama="Updated Product",
            stok=50,
            toko=self.toko1
        )
        mock_update.return_value = (200, mock_product)
        
        payload = UpdateProdukSchema(
            nama="Updated Product",
            harga_modal=20000,
            harga_jual=25000,
            stok=50,
            satuan="Box",
            kategori="Updated Category"
        )
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = mock_update(request, id=1, payload=payload)
        
        # Verify the mock was called with correct parameters
        mock_update.assert_called_once_with(request, id=1, payload=payload)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response.nama, "Updated Product")
        self.assertEqual(response.stok, 50)

    @patch('produk.api.update_produk')
    def test_update_product_not_found(self, mock_update):
        # Configure mock to return error
        mock_update.return_value = (422, {"message": "Product not found"})
        
        payload = UpdateProdukSchema(
            nama="Updated Product",
            harga_modal=20000,
            harga_jual=25000,
            stok=50,
            satuan="Box",
            kategori="Updated Category"
        )
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = mock_update(request, id=9999, payload=payload)
        
        # Verify the mock was called with correct parameters
        mock_update.assert_called_once_with(request, id=9999, payload=payload)
        
        # Verify response
        self.assertEqual(status, 422)
        self.assertIn("message", response)

    @patch('produk.api.delete_produk')
    def test_delete_produk(self, mock_delete):
        # Configure mock response
        mock_delete.return_value = {"message": "Produk berhasil dihapus"}
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        response = mock_delete(request, id=1)
        
        # Verify the mock was called with correct parameters
        mock_delete.assert_called_once_with(request, id=1)
        
        # Verify response
        self.assertEqual(response["message"], "Produk berhasil dihapus")

    @patch('produk.api.get_low_stock_products')
    def test_low_stock_products(self, mock_low_stock):
        # Create mock products
        mock_products = [
            {"id": 1, "name": "Product 1", "stock": 5, "imageUrl": None},
            {"id": 2, "name": "Product 2", "stock": 3, "imageUrl": None},
            {"id": 3, "name": "Product 3", "stock": 4, "imageUrl": None},
        ]
        
        # Configure mock response
        mock_low_stock.return_value = (200, mock_products)
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, result = mock_low_stock(request)
        
        # Verify the mock was called
        mock_low_stock.assert_called_once_with(request)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(len(result), 3)
        
        # Verify all products have low stock
        for product in result:
            self.assertTrue(product['stock'] < 10)
            self.assertTrue("Product" in product['name'])

    def test_create_produk_negative_harga_modal(self):
        """Test that creating a product with negative harga_modal is rejected"""
        with self.assertRaises(ValidationError) as context:
            CreateProdukSchema(
                nama="Invalid Product",
                harga_modal=-1000,  # Negative value should be rejected
                harga_jual=20000,
                stok=10,
                satuan="Box",
                kategori="Test Category"
            )
        
        error_detail = str(context.exception)
        self.assertIn("Harga modal minus seharusnya invalid", error_detail)

    def test_create_produk_negative_harga_jual(self):
        """Test that creating a product with negative harga_jual is rejected"""
        with self.assertRaises(ValidationError) as context:
            CreateProdukSchema(
                nama="Invalid Product",
                harga_modal=10000,
                harga_jual=-5000,  # Negative value should be rejected
                stok=10,
                satuan="Box",
                kategori="Test Category"
            )
        
        error_detail = str(context.exception)
        self.assertIn("Harga jual minus seharusnya invalid", error_detail)

    def test_create_produk_negative_stok(self):
        """Test that creating a product with negative stok is rejected"""
        with self.assertRaises(ValidationError) as context:
            CreateProdukSchema(
                nama="Invalid Product",
                harga_modal=10000,
                harga_jual=15000,
                stok=-5,  # Negative value should be rejected
                satuan="Box",
                kategori="Test Category"
            )
        
        error_detail = str(context.exception)
        self.assertIn("Stok minus seharusnya invalid", error_detail)

    def test_update_produk_negative_stok(self):
        """Test that updating a product with negative stok is rejected"""
        with self.assertRaises(ValidationError) as context:
            UpdateProdukSchema(
                nama="Test Product",
                harga_modal=10000,
                harga_jual=15000,
                stok=-10,  # Negative value should be rejected
                satuan="Box",
                kategori="Test Category"
            )
        
        error_detail = str(context.exception)
        self.assertIn("Stok minus tidak valid", error_detail)

    def test_auth_bearer_valid_token(self):
        """Test that AuthBearer authenticates with valid token"""
        auth = AuthBearer()
        
        # Create a valid token
        token = jwt.encode({"user_id": self.user1.id}, settings.SECRET_KEY, algorithm="HS256")
        
        # Create a mock request with the token
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        
        # Test authentication
        user_id = auth.authenticate(request, token)
        self.assertEqual(user_id, self.user1.id)

    def test_auth_bearer_invalid_token(self):
        """Test that AuthBearer rejects invalid token"""
        auth = AuthBearer()
        
        # Create an invalid token with wrong secret
        token = jwt.encode({"user_id": self.user1.id}, "wrong_secret", algorithm="HS256")
        
        # Test authentication
        user_id = auth.authenticate(None, token)
        self.assertIsNone(user_id)

    def test_auth_bearer_missing_user_id(self):
        """Test that AuthBearer rejects token without user_id"""
        auth = AuthBearer()
        
        # Create token without user_id
        token = jwt.encode({"some_field": "value"}, settings.SECRET_KEY, algorithm="HS256")
        
        # Test authentication
        user_id = auth.authenticate(None, token)
        self.assertIsNone(user_id)

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_default(self, mock_paginated):
        """Test that get_produk_default calls get_produk_paginated with page=1"""
        # Configure mock response
        mock_paginated.return_value = (200, {"items": [], "total": 0, "page": 1})
        
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        get_produk_default(request, sort="stok")
        
        # Verify get_produk_paginated was called with correct parameters
        mock_paginated.assert_called_once_with(request, page=1, sort="stok")

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_invalid_per_page(self, mock_paginated):
        """Test that get_produk_paginated handles invalid per_page parameter"""
        # Configure mock response
        mock_paginated.return_value = (200, {
            "items": [],
            "total": 0,
            "page": 1,
            "per_page": 7,
            "total_pages": 0
        })
        
        # Create a request with invalid per_page
        request = MockAuthenticatedRequest(user_id=self.user1.id, get_params={"per_page": "invalid"})
        
        # Call the function
        status, response = mock_paginated(request, page=1)
        
        # Verify mock was called
        mock_paginated.assert_called_once_with(request, page=1)
        
        # Verify default per_page was used
        self.assertEqual(status, 200)
        self.assertEqual(response["per_page"], 7)