from django.test import TestCase
from django.conf import settings
from ninja.testing import TestClient
from django.core.files.uploadedfile import SimpleUploadedFile
import jwt
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from authentication.models import User
from produk.models import Produk, KategoriProduk
from transaksi.api import router
from transaksi.models import Transaksi, TransaksiItem
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class TransaksiAPITestCase(TestCase):
    def setUp(self):
        # mount the transaksi router
        self.client = TestClient(router)

        # create a Pemilik user + JWT
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass"
        )
        self.user.role = "Pemilik"
        self.user.save()
        token = jwt.encode(
            {"user_id": self.user.id}, settings.SECRET_KEY, algorithm="HS256"
        )
        self.headers = {"Authorization": f"Bearer {token}"}

        # create a product category and one product with known stock
        self.cat = KategoriProduk.objects.create(nama="TestCat")
        # minimal PNG header for ImageField
        img = SimpleUploadedFile("p.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        self.prod = Produk.objects.create(
            nama="TestProd",
            foto=img,
            harga_modal=5.00,
            harga_jual=10.00,
            stok=10,
            satuan="pcs",
            kategori=self.cat,
            user=self.user,
        )

    def test_create_sale_missing_items(self):
        """Penjualan Barang with no items should 422 via Pydantic validator."""
        payload = {
            "transaction_type": "TXN1",
            "category": "Penjualan Barang",
            "total_amount": 100.0,
            "total_modal": 50.0,
            "amount": 50.0,
            "items": [],  # missing
        }
        r = self.client.post("", json=payload, headers=self.headers)
        self.assertEqual(r.status_code, 422)
        detail = r.json()["detail"][0]
        self.assertIn("Minimal satu item harus ditambahkan untuk penjualan barang", detail["msg"])

    def test_create_sale_success_and_stock_decrement(self):
        """Valid sale decreases stock and returns 201 + correct response schema."""
        initial_stock = self.prod.stok
        payload = {
            "transaction_type": "SALE1",
            "category": "Penjualan Barang",
            "total_amount": 20.0,
            "total_modal": 10.0,
            "amount": 10.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 3.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r = self.client.post("", json=payload, headers=self.headers)
        self.assertEqual(r.status_code, 201)
        body = r.json()
        # response fields
        self.assertEqual(body["category"], "Penjualan Barang")
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["product_id"], self.prod.id)
        # stock reduced
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stok, initial_stock - 3)

    def test_create_sale_insufficient_stock(self):
        """Attempting to sell more than stock yields 422 + proper message."""
        payload = {
            "transaction_type": "SALE2",
            "category": "Penjualan Barang",
            "total_amount": 200.0,
            "total_modal": 100.0,
            "amount": 100.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 999.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r = self.client.post("", json=payload, headers=self.headers)
        self.assertEqual(r.status_code, 422)
        msg = r.json()["message"]
        self.assertIn("Stok tidak cukup untuk produk TestProd", msg)

    def test_create_purchase_and_stock_increment(self):
        """Pembelian Stok increases stock."""
        initial = self.prod.stok
        payload = {
            "transaction_type": "BUY1",
            "category": "Pembelian Stok",
            "total_amount": 30.0,
            "total_modal": 15.0,
            "amount": 15.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 5.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r = self.client.post("", json=payload, headers=self.headers)
        self.assertEqual(r.status_code, 201)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stok, initial + 5)

    def test_list_transactions_and_pagination(self):
        """List endpoint returns created transactions and paginates."""
        # create one generic txn (no items needed)
        create_payload = {
            "transaction_type": "GEN1",
            "category": "Other",
            "total_amount": 10.0,
            "total_modal": 0.0,
            "amount": 10.0,
            "items": [],
        }
        r1 = self.client.post("", json=create_payload, headers=self.headers)
        self.assertEqual(r1.status_code, 201)
        txn_id = r1.json()["id"]

        # default list
        r2 = self.client.get("", headers=self.headers)
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], txn_id)

        # page too big => 404
        r3 = self.client.get("?page=2", headers=self.headers)
        self.assertEqual(r3.status_code, 404)
        self.assertEqual(r3.json()["message"], "Page not found")

    def test_detail_and_not_found(self):
        """Detail returns an existing txn, 404 otherwise."""
        # create
        p = {
            "transaction_type": "GEN2",
            "category": "Other2",
            "total_amount": 5.0,
            "total_modal": 0.0,
            "amount": 5.0,
            "items": [],
        }
        r = self.client.post("", json=p, headers=self.headers)
        tid = r.json()["id"]

        # found
        r2 = self.client.get(f"/{tid}", headers=self.headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["id"], tid)

        # missing
        r3 = self.client.get("/UNKNOWN", headers=self.headers)
        self.assertEqual(r3.status_code, 404)
        self.assertEqual(r3.json()["message"], "Transaksi tidak ditemukan")

    def test_delete_and_stock_restore(self):
        """Deleting a sale txn does a soft delete & restores stock."""
        # first create a sale of 2 units
        orig = self.prod.stok
        sale = {
            "transaction_type": "SALE3",
            "category": "Penjualan Barang",
            "total_amount": 20.0,
            "total_modal": 10.0,
            "amount": 10.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 2.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r1 = self.client.post("", json=sale, headers=self.headers)
        tid = r1.json()["id"]
        # stock down
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stok, orig - 2)

        # delete
        r2 = self.client.delete(f"/{tid}", headers=self.headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["message"], "Transaksi berhasil dihapus")

        # soft-deleted
        txn = Transaksi.objects.get(id=tid)
        self.assertTrue(txn.is_deleted)

        # stock restored
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stok, orig)

    def test_list_filter_category_and_q(self):
        # create two txns with different categories
        p1 = {
            "transaction_type": "T1",
            "category": "Food",
            "total_amount": 10.0,
            "total_modal": 0.0,
            "amount": 10.0,
            "items": [],
        }
        p2 = {
            "transaction_type": "T2",
            "category": "Drink",
            "total_amount": 20.0,
            "total_modal": 0.0,
            "amount": 20.0,
            "items": [],
        }
        r1 = self.client.post("", json=p1, headers=self.headers)
        r2 = self.client.post("", json=p2, headers=self.headers)
        id1, id2 = r1.json()["id"], r2.json()["id"]

        # filter by category=Food
        rf = self.client.get("?category=Food", headers=self.headers)
        self.assertEqual(rf.status_code, 200)
        self.assertEqual(rf.json()["total"], 1)
        self.assertEqual(rf.json()["items"][0]["id"], id1)

        # filter by q using partial ID of second txn
        qstr = id2[:3]
        rq = self.client.get(f"?q={qstr}", headers=self.headers)
        self.assertEqual(rq.status_code, 200)
        self.assertEqual(rq.json()["total"], 1)
        self.assertEqual(rq.json()["items"][0]["id"], id2)

    def test_list_filter_transaction_type_and_status(self):
        # create with custom type and status
        p = {
            "transaction_type": "ABC",
            "category": "X",
            "total_amount": 5.0,
            "total_modal": 0.0,
            "amount": 5.0,
            "items": [],
            "status": "Pending",
        }
        r = self.client.post("", json=p, headers=self.headers)
        tid = r.json()["id"]

        # filter by transaction_type
        rt = self.client.get(f"?transaction_type=ABC", headers=self.headers)
        self.assertEqual(rt.status_code, 200)
        self.assertEqual(rt.json()["total"], 1)

        # filter by status
        rs = self.client.get(f"?status=Pending", headers=self.headers)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json()["total"], 1)

    def test_list_show_deleted_flag(self):
        # create and then delete one txn
        p = {
            "transaction_type": "D1",
            "category": "Any",
            "total_amount": 1.0,
            "total_modal": 0.0,
            "amount": 1.0,
            "items": [],
        }
        r = self.client.post("", json=p, headers=self.headers)
        tid = r.json()["id"]
        # delete it
        self.client.delete(f"/{tid}", headers=self.headers)

        # default list (show_deleted=False) should hide it
        r1 = self.client.get("", headers=self.headers)
        self.assertEqual(r1.json()["total"], 0)

        # show_deleted=True should include it
        r2 = self.client.get("?show_deleted=True", headers=self.headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["total"], 1)
        self.assertEqual(r2.json()["items"][0]["id"], tid)

    def test_delete_purchase_and_insufficient_stock_on_rollback(self):
        # purchase txn of 4 units
        orig = self.prod.stok
        p = {
            "transaction_type": "BUY2",
            "category": "Pembelian Stok",
            "total_amount": 40.0,
            "total_modal": 20.0,
            "amount": 20.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 4.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r = self.client.post("", json=p, headers=self.headers)
        tid = r.json()["id"]
        # stock now increased
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stok, orig + 4)

        # manually drop stock below 4 to trigger rollback failure
        Produk.objects.filter(id=self.prod.id).update(stok=2)

        # attempt delete => 422
        rd = self.client.delete(f"/{tid}", headers=self.headers)
        self.assertEqual(rd.status_code, 422)
        self.assertIn("Stok produk TestProd tidak mencukupi", rd.json()["message"])

    def test_empty_monthly_summary(self):
        """With no transactions at all, summary should be all zeros and 'untung'."""
        r = self.client.get("/summary/monthly", headers=self.headers)
        s = r.json()
        self.assertEqual(s["pemasukan"]["amount"], 0)
        self.assertEqual(s["pemasukan"]["change"], 0)
        self.assertEqual(s["pengeluaran"]["amount"], 0)
        self.assertEqual(s["pengeluaran"]["change"], 0)
        self.assertEqual(s["status"], "untung")
        self.assertEqual(s["amount"], 0)

    def test_unauthorized_access(self):
        """Access without Authorization header returns 401."""
        r = self.client.get("")  # no headers
        self.assertEqual(r.status_code, 401)
        r2 = self.client.post("", json={}, headers={})
        self.assertEqual(r2.status_code, 401)

    def test_invalid_payload_missing_field(self):
        """Submitting a payload missing required fields yields 422."""
        # drop 'category'
        bad = {
            "transaction_type": "X",
            "total_amount": 10.0,
            "total_modal": 0.0,
            "amount": 10.0,
            "items": [],
        }
        r = self.client.post("", json=bad, headers=self.headers)
        self.assertEqual(r.status_code, 422)
        detail = r.json()["detail"][0]
        self.assertIn("Field required", detail["msg"])

    def test_invalid_item_quantity_zero(self):
        """Quantity <=0 in items triggers validation error."""
        payload = {
            "transaction_type": "TX",
            "category": "Penjualan Barang",
            "total_amount": 5.0,
            "total_modal": 0.0,
            "amount": 5.0,
            "items": [
                {
                    "product_id": self.prod.id,
                    "quantity": 0.0,
                    "harga_jual_saat_transaksi": 10.0,
                    "harga_modal_saat_transaksi": 5.0,
                }
            ],
        }
        r = self.client.post("", json=payload, headers=self.headers)
        self.assertEqual(r.status_code, 422)
        detail = r.json()["detail"][0]
        self.assertIn("Quantity harus lebih dari 0", detail["msg"])
