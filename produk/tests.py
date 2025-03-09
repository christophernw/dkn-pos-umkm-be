from django.test import TestCase, Client
from produk.models import Produk, KategoriProduk
import json

class ProdukAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")

        self.produk_dengan_foto = Produk.objects.create(
            nama="Laptop",
            foto="https://example.com/laptop.jpg",
            harga_modal=5000000,
            harga_jual=7000000,
            stok=10,
            satuan="Pcs",
            kategori=self.kategori
        )

        self.produk_tanpa_foto = Produk.objects.create(
            nama="Keyboard",
            foto="",
            harga_modal=300000,
            harga_jual=500000,
            stok=20,
            satuan="Pcs",
            kategori=self.kategori
        )

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori), "Elektronik")

    def test_produk_str(self):
        self.assertEqual(str(self.produk_dengan_foto), "Laptop")
        self.assertEqual(str(self.produk_tanpa_foto), "Keyboard")

    def test_get_produk_success(self):
        response = self.client.get("/api/produk")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)

        data = sorted(data, key=lambda x: x["id"])

        self.assertEqual(data[0]["id"], self.produk_dengan_foto.id)
        self.assertEqual(data[0]["nama"], "Laptop")
        self.assertEqual(data[0]["foto"], "https://example.com/laptop.jpg")
        self.assertEqual(data[0]["harga_modal"], float(self.produk_dengan_foto.harga_modal))
        self.assertEqual(data[0]["harga_jual"], float(self.produk_dengan_foto.harga_jual))
        self.assertEqual(data[0]["stok"], float(self.produk_dengan_foto.stok))
        self.assertEqual(data[0]["satuan"], self.produk_dengan_foto.satuan)
        self.assertEqual(data[0]["kategori"], "Elektronik")

        self.assertEqual(data[1]["id"], self.produk_tanpa_foto.id)
        self.assertEqual(data[1]["nama"], "Keyboard")
        self.assertEqual(data[1]["foto"], "")
        self.assertEqual(data[1]["harga_modal"], float(self.produk_tanpa_foto.harga_modal))
        self.assertEqual(data[1]["harga_jual"], float(self.produk_tanpa_foto.harga_jual))
        self.assertEqual(data[1]["stok"], float(self.produk_tanpa_foto.stok))
        self.assertEqual(data[1]["satuan"], self.produk_tanpa_foto.satuan)
        self.assertEqual(data[1]["kategori"], "Elektronik")

    def test_get_produk_not_found(self):
        Produk.objects.all().delete()
        response = self.client.get("/api/produk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_produk_invalid_url(self):
        response = self.client.get("/api/produk-salah")
        self.assertEqual(response.status_code, 404)

class ProdukSortingAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")

        self.produk_1 = Produk.objects.create(nama="Laptop", foto="", harga_modal=5000000, harga_jual=7000000, stok=5, satuan="PCS", kategori=self.kategori)
        self.produk_2 = Produk.objects.create(nama="Keyboard", foto="", harga_modal=300000, harga_jual=500000, stok=20, satuan="PCS", kategori=self.kategori)
        self.produk_3 = Produk.objects.create(nama="Mouse", foto="", harga_modal=150000, harga_jual=250000, stok=10, satuan="PCS", kategori=self.kategori)

    def test_get_produk_sorted_ascending(self):
        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["nama"], "Laptop")
        self.assertEqual(data[1]["nama"], "Mouse")
        self.assertEqual(data[2]["nama"], "Keyboard")

    def test_get_produk_sorted_descending(self):
        response = self.client.get("/api/produk?sort=desc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["nama"], "Keyboard")
        self.assertEqual(data[1]["nama"], "Mouse")
        self.assertEqual(data[2]["nama"], "Laptop")

    def test_get_produk_invalid_sort_param(self):
        response = self.client.get("/api/produk?sort=invalid")
        self.assertEqual(response.status_code, 400)

    def test_get_produk_no_data(self):
        Produk.objects.all().delete()
        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_produk_same_stock(self):
        Produk.objects.all().delete()
        Produk.objects.create(nama="Item A", foto="", stok=10, harga_modal=100, harga_jual=200, satuan="PCS", kategori=self.kategori)
        Produk.objects.create(nama="Item B", foto="", stok=10, harga_modal=150, harga_jual=250, satuan="PCS", kategori=self.kategori)

        response = self.client.get("/api/produk?sort=asc")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]["id"] < data[1]["id"])

class ProdukCreateAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")
        self.url = "/api/produk/create"  

    def test_create_produk_success(self):
        payload = {
            "nama": "Monitor",
            "foto": "https://example.com/monitor.jpg",
            "harga_modal": 1200000,
            "harga_jual": 1500000,
            "stok": 15,
            "satuan": "PCS",
            "kategori": "Elektronik"  
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload), 
            content_type="application/json" 
        )
        self.assertEqual(response.status_code, 201, "Seharusnya berhasil membuat produk")

        data = response.json()
        self.assertEqual(data["nama"], "Monitor")
        self.assertEqual(data["kategori"], "Elektronik")
        self.assertTrue(Produk.objects.filter(nama="Monitor").exists())

    def test_create_produk_missing_required_field(self):
        payload = {
            "foto": "https://example.com/item.jpg",
            "harga_modal": 50000,
            "harga_jual": 80000,
            "stok": 5,
            "satuan": "PCS"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Seharusnya gagal karena field wajib hilang")

    def test_create_produk_new_category(self):

        payload = {
            "nama": "Smartphone",
            "foto": '',
            "harga_modal": 3000000,
            "harga_jual": 4500000,
            "stok": 8,
            "satuan": "PCS",
            "kategori": "Gadget" 
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertEqual(data["kategori"], "Gadget")
        self.assertTrue(KategoriProduk.objects.filter(nama="Gadget").exists())

    def test_create_produk_negative_price(self):
        payload = {
            "nama": "Test Negative Price",
            "foto": '',
            "harga_modal": -100000,
            "harga_jual": -150000,
            "stok": 10,
            "satuan": "PCS",
            "kategori": "Elektronik"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Harga minus seharusnya invalid")

    def test_create_produk_invalid_stock(self):
        payload = {
            "nama": "Test Negative Stock",
            "foto": '',
            "harga_modal": 100000,
            "harga_jual": 150000,
            "stok": -5, 
            "satuan": "PCS",
            "kategori": "Elektronik"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, "Stok minus seharusnya invalid")

    def test_create_produk_zero_values(self):
        payload = {
            "nama": "Test Zero Values",
            "foto": '',
            "harga_modal": 0,
            "harga_jual": 0,
            "stok": 0,
            "satuan": "PCS",
            "kategori": "Elektronik"
        }
        response = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
    
class DeleteAPITest(TestCase):
    def setUp(self):
        self.client = Client()

        self.kategori_makanan = KategoriProduk.objects.create(nama="Makanan")
        self.kategori_minuman = KategoriProduk.objects.create(nama="Minuman")

        self.burger = Produk.objects.create(
            nama="Burger Keju",
            foto="burger_keju.png",
            harga_modal=18000,
            harga_jual=25000,
            stok=40,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        self.jus = Produk.objects.create(
            nama="Jus Alpukat",
            foto="jus_alpukat.png",
            harga_modal=5000,
            harga_jual=10000,
            stok=80,
            satuan="gelas",
            kategori=self.kategori_minuman,
        )
        self.pizza = Produk.objects.create(
            nama="Pizza Pepperoni",
            foto="pizza_pepperoni.png",
            harga_modal=30000,
            harga_jual=45000,
            stok=15,
            satuan="porsi",
            kategori=self.kategori_makanan,
        )
        
    def test_produk_str(self):
        self.assertEqual(str(self.jus), "Jus Alpukat")

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori_minuman), "Minuman")
    
    def test_delete_produk_success(self):
        response = self.client.delete(f"/api/produk/delete/{1}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Produk berhasil dihapus"})
        self.assertFalse(Produk.objects.filter(id=1).exists())

    def test_delete_produk_not_found(self):
        response = self.client.delete(f"/api/produk/delete/{20}")
        self.assertEqual(response.status_code, 404)
    
    def test_delete_produk_invalid_id(self):
        response = self.client.delete("/api/produk/delete/invalid")
        self.assertEqual(response.status_code, 422)

class ProdukPaginationAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")
        
        for i in range(1, 21):
            Produk.objects.create(
                nama=f"Produk {i}",
                foto="",
                harga_modal=i * 10000,
                harga_jual=i * 15000,
                stok=i,
                satuan="PCS",
                kategori=self.kategori
            )
    
    def test_get_produk_with_pagination(self):
        response = self.client.get("/api/produk/page/1")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("per_page", data)
        self.assertIn("total_pages", data)
        
        self.assertEqual(len(data["items"]), 7)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["per_page"], 7)
        self.assertEqual(data["total"], 20)
        self.assertEqual(data["total_pages"], 3)  # Total 20 items, 7 per page = 3 pages
        
    def test_get_produk_with_pagination_last_page(self):
        response = self.client.get("/api/produk/page/3")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data["items"]), 6)
        self.assertEqual(data["page"], 3)
    
    def test_get_produk_with_pagination_invalid_page(self):
        response = self.client.get("/api/produk/page/10")
        self.assertEqual(response.status_code, 404)
        
    def test_get_produk_with_custom_per_page(self):
        response = self.client.get("/api/produk/page/1?per_page=5")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["per_page"], 5)
        self.assertEqual(data["total_pages"], 4)

    def test_get_produk_pagination_invalid_sort(self):
        response = self.client.get("/api/produk/page/1?sort=invalid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode('utf-8'), "Invalid sort parameter. Use 'asc' or 'desc'.")

    def test_get_produk_pagination_invalid_per_page(self):
        response = self.client.get("/api/produk/page/1?per_page=abc")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["per_page"], 7)
        self.assertEqual(len(data["items"]), 7)

class LowStockAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.kategori = KategoriProduk.objects.create(nama="Elektronik")

        self.produk_stok_rendah_1 = Produk.objects.create(
            nama="Mouse",
            foto="https://example.com/mouse.jpg",
            harga_modal=50000,
            harga_jual=80000,
            stok=5,
            satuan="Pcs",
            kategori=self.kategori
        )

        self.produk_stok_rendah_2 = Produk.objects.create(
            nama="Headset",
            foto="https://example.com/headset.jpg",
            harga_modal=150000,
            harga_jual=250000,
            stok=9.5,
            satuan="Pcs",
            kategori=self.kategori
        )
        
        self.produk_stok_kosong = Produk.objects.create(
            nama="Webcam",
            foto="https://example.com/webcam.jpg",
            harga_modal=120000,
            harga_jual=200000,
            stok=0,
            satuan="Pcs",
            kategori=self.kategori
        )

        self.produk_stok_batas = Produk.objects.create(
            nama="Laptop",
            foto="https://example.com/laptop.jpg",
            harga_modal=5000000,
            harga_jual=7000000,
            stok=10,
            satuan="Pcs",
            kategori=self.kategori
        )

        self.produk_stok_aman = Produk.objects.create(
            nama="Keyboard",
            foto="",
            harga_modal=300000,
            harga_jual=500000,
            stok=20,
            satuan="Pcs",
            kategori=self.kategori
        )

    def test_get_low_stock_products_success(self):
        response = self.client.get("/api/produk/low-stock")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 3)

        data = sorted(data, key=lambda x: x["id"])
        
        product_ids = [item["id"] for item in data]
        self.assertIn(self.produk_stok_rendah_1.id, product_ids)
        self.assertIn(self.produk_stok_rendah_2.id, product_ids)
        self.assertIn(self.produk_stok_kosong.id, product_ids)
        
        self.assertNotIn(self.produk_stok_batas.id, product_ids)
        self.assertNotIn(self.produk_stok_aman.id, product_ids)
        
        self.assertEqual(data[0]["nama"], "Mouse")
        self.assertEqual(data[0]["foto"], "https://example.com/mouse.jpg")
        self.assertEqual(data[0]["harga_modal"], float(self.produk_stok_rendah_1.harga_modal))
        self.assertEqual(data[0]["harga_jual"], float(self.produk_stok_rendah_1.harga_jual))
        self.assertEqual(data[0]["stok"], float(self.produk_stok_rendah_1.stok))
        self.assertEqual(data[0]["satuan"], self.produk_stok_rendah_1.satuan)
        self.assertEqual(data[0]["kategori"], "Elektronik")

    def test_get_low_stock_products_empty(self):
        Produk.objects.filter(stok__lt=10).delete()
        
        response = self.client.get("/api/produk/low-stock")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_low_stock_products_no_products(self):
        Produk.objects.all().delete()
        
        response = self.client.get("/api/produk/low-stock")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_low_stock_products_invalid_url(self):
        response = self.client.get("/api/produk/low-stok")
        self.assertEqual(response.status_code, 404)

    def test_get_low_stock_products_invalid_method(self):
        response = self.client.post("/api/produk/low-stock")
        self.assertEqual(response.status_code, 405) 