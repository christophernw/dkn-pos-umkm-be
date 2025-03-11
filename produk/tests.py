from django.test import TestCase, RequestFactory
from produk.api import get_produk_paginated
from produk.models import Produk, KategoriProduk

class GetProdukPaginatedTest(TestCase):
    def setUp(self):
        # Create a request factory for testing
        self.factory = RequestFactory()
        
        # Create a category for test products
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")
        
        # Create 20 test products
        for i in range(20):
            Produk.objects.create(
                nama=f"Produk {i}",
                foto=f"https://example.com/produk{i}.jpg" if i % 2 == 0 else "",
                harga_modal=100000 * (i + 1),
                harga_jual=150000 * (i + 1),
                stok=i + 5,
                satuan="Pcs",
                kategori=self.kategori
            )

    def test_default_pagination(self):
        """Test default pagination with 7 items per page"""
        request = self.factory.get('/produk/page/1')
        status, response = get_produk_paginated(request, page=1)
        
        self.assertEqual(status, 200)
        self.assertEqual(len(response["items"]), 7)
        self.assertEqual(response["total"], 20)
        self.assertEqual(response["page"], 1)
        self.assertEqual(response["per_page"], 7)
        self.assertEqual(response["total_pages"], 3)

    def test_custom_per_page(self):
        """Test custom per_page parameter"""
        request = self.factory.get('/produk/page/1', {'per_page': '5'})
        status, response = get_produk_paginated(request, page=1)
        
        self.assertEqual(status, 200)
        self.assertEqual(len(response["items"]), 5)
        self.assertEqual(response["per_page"], 5)
        self.assertEqual(response["total_pages"], 4)

    def test_invalid_per_page(self):
        """Test invalid per_page parameter (should default to 7)"""
        request = self.factory.get('/produk/page/1', {'per_page': 'invalid'})
        status, response = get_produk_paginated(request, page=1)
        
        self.assertEqual(status, 200)
        self.assertEqual(len(response["items"]), 7)
        self.assertEqual(response["per_page"], 7)

    def test_last_page(self):
        """Test last page with fewer items than per_page"""
        request = self.factory.get('/produk/page/3')
        status, response = get_produk_paginated(request, page=3)
        
        self.assertEqual(status, 200)
        self.assertEqual(len(response["items"]), 6)  # 20 items total, 7+7+6
        self.assertEqual(response["page"], 3)
        
    def test_page_out_of_range(self):
        """Test page number out of range"""
        request = self.factory.get('/produk/page/10')
        status, response = get_produk_paginated(request, page=10)
        
        self.assertEqual(status, 404)
        self.assertEqual(response["message"], "Page not found")
    
    def test_empty_database(self):
        """Test with empty database"""
        Produk.objects.all().delete()
        request = self.factory.get('/produk/page/1')
        status, response = get_produk_paginated(request, page=1)
        
        self.assertEqual(status, 200)
        self.assertEqual(len(response["items"]), 0)
        self.assertEqual(response["total"], 0)
        self.assertEqual(response["total_pages"], 0)
    
    def test_sorting_asc(self):
        """Test ascending sort parameter"""
        request = self.factory.get('/produk/page/1')
        status, response = get_produk_paginated(request, page=1, sort="asc")
        
        self.assertEqual(status, 200)
        # Verify first item has lowest stock
        if len(response["items"]) > 1:
            self.assertTrue(response["items"][0].stok <= response["items"][1].stok)
        
    def test_sorting_desc(self):
        """Test descending sort parameter"""
        request = self.factory.get('/produk/page/1')
        status, response = get_produk_paginated(request, page=1, sort="desc")
        
        self.assertEqual(status, 200)
        # Verify first item has highest stock
        if len(response["items"]) > 1:
            self.assertTrue(response["items"][0].stok >= response["items"][1].stok)
            
    def test_invalid_sort(self):
        """Test invalid sort parameter"""
        request = self.factory.get('/produk/page/1')
        response = get_produk_paginated(request, page=1, sort="invalid")
        
        self.assertEqual(response.status_code, 400)