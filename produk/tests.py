from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock

import jwt
from pydantic import ValidationError

from backend import settings
from .api import (
    AuthBearer,
    get_produk_by_id,
    get_produk_default,
    router,
    get_produk_paginated,
    create_produk,
    delete_produk,
    get_low_stock_products,
    update_produk,
    update_produk_stock,
)
from .models import Produk, KategoriProduk
from .schemas import ProdukResponseSchema, CreateProdukSchema, UpdateProdukStokSchema


class MockAuthenticatedRequest:
    """Mock request with authentication for testing"""

    def __init__(self, user_id=1, method="get_params", body=None, get_params=None):
        self.auth = user_id  # Simulating authenticated user
        self.method = method
        self._body = json.dumps(body).encode() if body else None
        self.GET = get_params or {}


class TestProductAPI(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(
            username="testuser1", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", password="password123"
        )

        # Create categories
        self.kategori1 = KategoriProduk.objects.create(nama="Minuman")
        self.kategori2 = KategoriProduk.objects.create(nama="Makanan")

        # Create test products for user1
        for i in range(1, 11):
            stok = 5 if i <= 3 else 20  # Create some products with low stock
            Produk.objects.create(
                nama=f"User1 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f"{i}000"),
                harga_jual=Decimal(f"{i+2}000"),
                stok=Decimal(stok),
                satuan="Pcs",
                kategori=self.kategori1 if i % 2 == 0 else self.kategori2,
                user=self.user1,
            )

        # Create test products for user2
        for i in range(1, 6):
            Produk.objects.create(
                nama=f"User2 Produk {i}",
                foto="test.jpg",
                harga_modal=Decimal(f"{i}000"),
                harga_jual=Decimal(f"{i+2}000"),
                stok=Decimal(15),
                satuan="Pcs",
                kategori=self.kategori1,
                user=self.user2,
            )

        self.factory = RequestFactory()

    def test_get_produk_with_sort_asc(self):
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = get_produk_paginated(request, page=1, sort="asc", q="User1")

        self.assertEqual(status, 200)
        # Check that products are sorted by stok ascending
        for i in range(len(response["items"]) - 1):
            self.assertTrue(response["items"][i].stok <= response["items"][i + 1].stok)

    def test_get_produk_with_sort_desc(self):
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = get_produk_paginated(request, page=1, sort="desc")

        self.assertEqual(status, 200)
        # Check that products are sorted by stok descending
        for i in range(len(response["items"]) - 1):
            self.assertTrue(response["items"][i].stok >= response["items"][i + 1].stok)

    def test_get_produk_with_invalid_sort(self):
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        response = get_produk_paginated(request, page=1, sort="invalid")

        # Should return HttpResponseBadRequest
        self.assertEqual(response.status_code, 400)

    def test_get_produk_pagination(self):
        request = MockAuthenticatedRequest(
            user_id=self.user1.id, get_params={"per_page": "3"}
        )
        status, response = get_produk_paginated(request, page=2)

        self.assertEqual(status, 200)
        self.assertEqual(response["page"], 2)
        self.assertEqual(response["per_page"], 3)
        self.assertEqual(len(response["items"]), 3)
        self.assertEqual(response["total_pages"], 4)  # 10 items, 3 per page = 4 pages

    def test_page_not_found(self):
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = get_produk_paginated(request, page=5)

        self.assertEqual(status, 404)
        self.assertEqual(response["message"], "Page not found")

    def test_create_produk(self):
        payload = CreateProdukSchema(
            nama="New Product",
            harga_modal=15000,
            harga_jual=20000,
            stok=25,
            satuan="Box",
            kategori="New Category",
        )

        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = create_produk(request, payload=payload)

        self.assertEqual(status, 201)
        self.assertEqual(response.nama, "New Product")
        self.assertEqual(response.kategori, "New Category")

        # Check that product was created in DB
        self.assertTrue(
            Produk.objects.filter(nama="New Product", user=self.user1).exists()
        )
        # Check that the category was created
        self.assertTrue(KategoriProduk.objects.filter(nama="New Category").exists())

    def test_update_product_stock(self):
        produk = Produk.objects.filter(user=self.user1).first()
        payload = UpdateProdukStokSchema(stok=50)

        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = update_produk_stock(request, id=produk.id, payload=payload)

        self.assertEqual(status, 200)
        self.assertEqual(response.stok, 50.0)

        # Check DB was updated
        updated_produk = Produk.objects.get(id=produk.id)
        self.assertEqual(updated_produk.stok, 50)

    def test_update_product_not_found(self):
        payload = UpdateProdukStokSchema(stok=50)
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        # Use a non-existent ID
        status, response = update_produk_stock(request, id=9999, payload=payload)

        # Should return 422 error response, not raise exception
        self.assertEqual(status, 422)
        self.assertIn("message", response)

    def test_delete_produk(self):
        produk = Produk.objects.filter(user=self.user1).first()
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        response = delete_produk(request, id=produk.id)

        self.assertEqual(response["message"], "Produk berhasil dihapus")
        self.assertFalse(Produk.objects.filter(id=produk.id).exists())

    def test_delete_other_users_produk(self):
        # Try to delete user2's product as user1
        produk = Produk.objects.filter(user=self.user2).first()
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        # Should raise exception because get_object_or_404 will fail
        with self.assertRaises(Exception):
            delete_produk(request, id=produk.id)

    def test_low_stock_products(self):
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        result = get_low_stock_products(request)

        self.assertEqual(len(result), 3)  # We created 3 products with stok=5

        # Check that all returned products have stock less than 10
        for product in result:
            self.assertTrue(product.stok < 10)
            # Ensure products belong to user1
            self.assertTrue("User1" in product.nama)

    def test_create_produk_negative_harga_modal(self):
        """Test that creating a product with negative harga_modal is rejected"""
        # Test that validation occurs during model creation
        with self.assertRaises(ValidationError) as context:
            CreateProdukSchema(
                nama="Invalid Product",
                harga_modal=-1000,  # Negative value should be rejected
                harga_jual=20000,
                stok=10,
                satuan="Box",
                kategori="Test Category",
            )

        # Verify the error message
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
                kategori="Test Category",
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
                kategori="Test Category",
            )

        error_detail = str(context.exception)
        self.assertIn("Stok minus seharusnya invalid", error_detail)

    def test_update_produk_negative_stok(self):
        """Test that updating a product with negative stok is rejected"""
        with self.assertRaises(ValidationError) as context:
            UpdateProdukStokSchema(stok=-10)  # Negative value should be rejected

        error_detail = str(context.exception)
        self.assertIn("Stok minus tidak valid", error_detail)

    def test_auth_bearer_valid_token(self):
        """Test that AuthBearer authenticates with valid token"""
        auth = AuthBearer()

        # Create a valid token
        token = jwt.encode(
            {"user_id": self.user1.id}, settings.SECRET_KEY, algorithm="HS256"
        )

        # Create a mock request with the token
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

        # Test authentication
        user_id = auth.authenticate(request, token)
        self.assertEqual(user_id, self.user1.id)

    def test_auth_bearer_invalid_token(self):
        """Test that AuthBearer rejects invalid token"""
        auth = AuthBearer()

        # Create an invalid token with wrong secret
        token = jwt.encode(
            {"user_id": self.user1.id}, "wrong_secret", algorithm="HS256"
        )

        # Test authentication
        user_id = auth.authenticate(None, token)
        self.assertIsNone(user_id)

    def test_auth_bearer_missing_user_id(self):
        """Test that AuthBearer rejects token without user_id"""
        auth = AuthBearer()

        # Create token without user_id
        token = jwt.encode(
            {"some_field": "value"}, settings.SECRET_KEY, algorithm="HS256"
        )

        # Test authentication
        user_id = auth.authenticate(None, token)
        self.assertIsNone(user_id)

    def test_get_produk_default(self):
        """Test that get_produk_default calls get_produk_paginated with page=1"""
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        # Mock get_produk_paginated to verify it's called with correct parameters
        with patch("produk.api.get_produk_paginated") as mock_paginated:
            mock_paginated.return_value = (200, {"items": [], "total": 0, "page": 1})

            # Call the default endpoint
            get_produk_default(request, sort="asc")

            # Verify get_produk_paginated was called with page=1 and sort="asc"
            mock_paginated.assert_called_once_with(request, page=1, sort="asc")

    def test_get_produk_invalid_per_page(self):
        """Test that get_produk_paginated handles invalid per_page parameter"""
        # Create a request with invalid per_page (not an integer)
        request = MockAuthenticatedRequest(
            user_id=self.user1.id, get_params={"per_page": "invalid"}
        )

        # Call the function
        status, response = get_produk_paginated(request, page=1)

        # Verify default per_page was used (7)
        self.assertEqual(status, 200)
        self.assertEqual(response["per_page"], 7)

    def test_get_produk_by_id_success(self):
        """Test successfully retrieving a product by ID"""
        produk = Produk.objects.filter(user=self.user1).first()
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        status, response = get_produk_by_id(request, id=produk.id)

        self.assertEqual(status, 200)
        self.assertEqual(response.id, produk.id)
        self.assertEqual(response.nama, produk.nama)
        self.assertEqual(float(response.harga_modal), float(produk.harga_modal))
        self.assertEqual(float(response.harga_jual), float(produk.harga_jual))

    def test_get_produk_by_id_not_found(self):
        """Test retrieving a non-existent product"""
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        status, response = get_produk_by_id(request, id=99999)

        self.assertEqual(status, 404)
        self.assertEqual(response["message"], "Produk tidak ditemukan")

    def test_get_produk_by_id_wrong_user(self):
        """Test retrieving another user's product"""
        # Get product owned by user2
        produk = Produk.objects.filter(user=self.user2).first()
        # Try to access as user1
        request = MockAuthenticatedRequest(user_id=self.user1.id)

        status, response = get_produk_by_id(request, id=produk.id)

        self.assertEqual(status, 404)
        self.assertEqual(response["message"], "Produk tidak ditemukan")

    def test_update_produk_success(self):
        """Test successfully updating a product"""
        produk = Produk.objects.filter(user=self.user1).first()

        payload = CreateProdukSchema(
            nama="Updated Product Name",
            harga_modal=12500,
            harga_jual=15000,
            stok=30,
            satuan="Botol",
            kategori="Updated Category",
        )

        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = update_produk(request, id=produk.id, payload=payload)

        self.assertEqual(status, 200)
        self.assertEqual(response.nama, "Updated Product Name")
        self.assertEqual(float(response.harga_modal), 12500.0)
        self.assertEqual(float(response.harga_jual), 15000.0)
        self.assertEqual(float(response.stok), 30.0)
        self.assertEqual(response.satuan, "Botol")
        self.assertEqual(response.kategori, "Updated Category")

        # Check DB was updated
        updated_produk = Produk.objects.get(id=produk.id)
        self.assertEqual(updated_produk.nama, "Updated Product Name")
        self.assertEqual(updated_produk.kategori.nama, "Updated Category")

    def test_update_produk_not_found(self):
        """Test updating a non-existent product"""
        payload = CreateProdukSchema(
            nama="Test Product",
            harga_modal=10000,
            harga_jual=15000,
            stok=20,
            satuan="Box",
            kategori="Test Category",
        )

        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = update_produk(request, id=99999, payload=payload)

        self.assertEqual(status, 422)
        self.assertIn("message", response)

    def test_update_produk_wrong_user(self):
        """Test updating another user's product"""
        # Get product owned by user2
        produk = Produk.objects.filter(user=self.user2).first()

        payload = CreateProdukSchema(
            nama="This Should Fail",
            harga_modal=10000,
            harga_jual=15000,
            stok=20,
            satuan="Box",
            kategori="Test Category",
        )

        # Try to update as user1
        request = MockAuthenticatedRequest(user_id=self.user1.id)
        status, response = update_produk(request, id=produk.id, payload=payload)

        self.assertEqual(status, 422)
        self.assertIn("message", response)

        # Verify product wasn't modified
        unchanged_produk = Produk.objects.get(id=produk.id)
        self.assertNotEqual(unchanged_produk.nama, "This Should Fail")

    def test_update_produk_with_foto(self):
        """Test updating a product with a new photo"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        produk = Produk.objects.filter(user=self.user1).first()
        payload = CreateProdukSchema(
            nama="Product With Photo",
            harga_modal=10000,
            harga_jual=15000,
            stok=20,
            satuan="Box",
            kategori="Test Category",
        )

        # Create a mock file
        mock_file = SimpleUploadedFile(
            "new_image.jpg", b"file_content", content_type="image/jpeg"
        )

        request = MockAuthenticatedRequest(user_id=self.user1.id)
        # We're mocking the file upload - in a real API call this would be handled by the framework
        status, response = update_produk(
            request, id=produk.id, payload=payload, foto=mock_file
        )

        self.assertEqual(status, 200)
        self.assertEqual(response.nama, "Product With Photo")

        # Check DB was updated with new photo
        updated_produk = Produk.objects.get(id=produk.id)
        self.assertIsNotNone(updated_produk.foto)
        self.assertNotEqual(updated_produk.foto.name, "test.jpg")
