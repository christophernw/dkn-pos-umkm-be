from django.test import TestCase, RequestFactory
from django.http import HttpResponseBadRequest
from authentication.models import User, Toko
from produk.models import Produk, KategoriProduk, Satuan
from produk.api import (
    AuthBearer,
    get_produk_default,
    get_produk_paginated,
    create_produk,
    update_produk,
    delete_produk,
    get_low_stock_products,
    get_categories,
    get_units,
    get_most_popular_products,
    get_produk_by_id,
    get_top_selling_products,
)
from produk.schemas import CreateProdukSchema, UpdateProdukSchema
from decimal import Decimal
import jwt
from backend import settings
from unittest.mock import patch, MagicMock
from pydantic import ValidationError


class MockRequest:
    def __init__(self, user_id, get_params=None):
        self.auth = user_id
        self.GET = get_params or {}


class TestProductAPI(TestCase):
    def setUp(self):
        # Create users with email
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='pass')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='pass')
        # Create toko and link to users
        self.toko1 = Toko.objects.create()
        self.toko2 = Toko.objects.create()
        self.user1.toko = self.toko1
        self.user1.save()
        self.user2.toko = self.toko2
        self.user2.save()

        # Create categories and units for toko1
        self.cat1 = KategoriProduk.objects.create(nama='CatA', toko=self.toko1)
        self.cat2 = KategoriProduk.objects.create(nama='CatB', toko=self.toko1)
        self.unit = Satuan.objects.create(nama='Pcs', toko=self.toko1)

        # Create products for toko1
        for i in range(5):
            Produk.objects.create(
                nama=f'Prod{i}',
                foto=None,
                harga_modal=Decimal('1000'),
                harga_jual=Decimal('1500'),
                stok=i,
                satuan=self.unit.nama,
                kategori=self.cat1,
                toko=self.toko1
            )
        # One product for toko2
        Produk.objects.create(
            nama='ProdX',
            foto=None,
            harga_modal=Decimal('2000'),
            harga_jual=Decimal('2500'),
            stok=10,
            satuan=self.unit.nama,
            kategori=self.cat2,
            toko=self.toko2
        )
        # Reference for mocking
        self.sample_prod = Produk.objects.filter(toko=self.toko1).first()
        self.prod_id = self.sample_prod.id
        self.factory = RequestFactory()

        # User without toko
        self.user_no_toko = User.objects.create_user(username='user3', email='user3@example.com', password='pass')

    def test_get_categories(self):
        request = MockRequest(user_id=self.user1.id)
        status, data = get_categories(request)
        self.assertEqual(status, 200)
        self.assertCountEqual(data, ['CatA', 'CatB'])

    def test_get_units(self):
        request = MockRequest(user_id=self.user1.id)
        status, data = get_units(request)
        self.assertEqual(status, 200)
        self.assertEqual(data, ['Pcs'])

    def test_get_units_no_toko(self):
        request = MockRequest(user_id=self.user_no_toko.id)
        status, resp = get_units(request)
        self.assertEqual(status, 404)
        self.assertEqual(resp['message'], "User doesn't have a toko")

    def test_get_produk_paginated_sort_stok(self):
        request = MockRequest(user_id=self.user1.id, get_params={'per_page': '5'})
        status, resp = get_produk_paginated(request, page=1, sort='stok')
        self.assertEqual(status, 200)
        stocks = [item.stok for item in resp['items']]
        self.assertEqual(stocks, sorted(stocks))

    def test_get_produk_paginated_sort_minus_stok(self):
        request = MockRequest(user_id=self.user1.id)
        status, resp = get_produk_paginated(request, page=1, sort='-stok')
        self.assertEqual(status, 200)
        stocks = [item.stok for item in resp['items']]
        self.assertEqual(stocks, sorted(stocks, reverse=True))

    def test_invalid_sort(self):
        request = MockRequest(user_id=self.user1.id)
        result = get_produk_paginated(request, page=1, sort='invalid')
        self.assertIsInstance(result, HttpResponseBadRequest)
        self.assertEqual(result.status_code, 400)

    def test_page_not_found(self):
        request = MockRequest(user_id=self.user1.id)
        status, data = get_produk_paginated(request, page=10, sort='stok')
        self.assertEqual(status, 404)
        self.assertEqual(data['message'], 'Page not found')

    def test_get_produk_by_id_success(self):
        request = MockRequest(user_id=self.user1.id)
        status, resp = get_produk_by_id(request, id=self.sample_prod.id)
        self.assertEqual(status, 200)
        self.assertEqual(resp.id, self.sample_prod.id)
        self.assertEqual(resp.nama, self.sample_prod.nama)

    def test_get_produk_by_id_not_found(self):
        request = MockRequest(user_id=self.user1.id)
        status, resp = get_produk_by_id(request, id=9999)
        self.assertEqual(status, 404)
        self.assertEqual(resp['message'], 'Produk tidak ditemukan')

    def test_create_produk(self):
        payload = CreateProdukSchema(
            nama='NewProd',
            harga_modal=500,
            harga_jual=800,
            stok=3,
            satuan='Box',
            kategori='CatC'
        )
        request = MockRequest(user_id=self.user1.id)
        status, resp = create_produk(request, payload=payload)
        self.assertEqual(status, 201)
        self.assertEqual(resp.nama, 'NewProd')
        self.assertEqual(resp.kategori, 'CatC')
        self.assertTrue(KategoriProduk.objects.filter(nama='CatC', toko=self.toko1).exists())

    def test_create_produk_no_toko(self):
        payload = CreateProdukSchema(
            nama='X', harga_modal=100, harga_jual=150, stok=1, satuan='Box', kategori='Y'
        )
        request = MockRequest(user_id=self.user_no_toko.id)
        status, resp = create_produk(request, payload=payload)
        self.assertEqual(status, 422)
        self.assertEqual(resp['message'], "User doesn't have a toko")

    def test_update_produk(self):
        payload = UpdateProdukSchema(
            nama=None,
            harga_modal=None,
            harga_jual=None,
            stok=99,
            satuan=None,
            kategori=None
        )
        request = MockRequest(user_id=self.user1.id)
        status, resp = update_produk(request, id=self.sample_prod.id, payload=payload)
        self.assertEqual(status, 200)
        self.assertEqual(resp.stok, 99.0)

    def test_update_no_toko(self):
        payload = UpdateProdukSchema(
            nama=None, harga_modal=None, harga_jual=None, stok=5, satuan=None, kategori=None
        )
        request = MockRequest(user_id=self.user_no_toko.id)
        status, resp = update_produk(request, id=self.sample_prod.id, payload=payload)
        self.assertEqual(status, 422)
        self.assertEqual(resp['message'], "User doesn't have a toko")

    def test_update_invalid_negative(self):
        with self.assertRaises(ValidationError):
            UpdateProdukSchema(
                nama=None, harga_modal=None, harga_jual=None, stok=-5, satuan=None, kategori=None
            )

    def test_delete_produk(self):
        request = MockRequest(user_id=self.user1.id)
        data = delete_produk(request, id=self.sample_prod.id)
        self.assertEqual(data['message'], 'Produk berhasil dihapus')

    def test_delete_other_users_produk(self):
        other_prod = Produk.objects.filter(toko=self.toko2).first()
        request = MockRequest(user_id=self.user1.id)
        with self.assertRaises(Exception):
            delete_produk(request, id=other_prod.id)

    def test_low_stock_products(self):
        request = MockRequest(user_id=self.user1.id)
        status, items = get_low_stock_products(request)
        self.assertEqual(status, 200)
        stocks = [item['stock'] for item in items]
        self.assertTrue(all(item['stock'] < 10 for item in items))

    @patch('produk.api.TransaksiItem.objects.filter')
    def test_get_most_popular_products(self, mock_filter):
        mock_qs = MagicMock()
        mock_qs.values.return_value = mock_qs
        mock_qs.annotate.return_value = mock_qs
        mock_qs.order_by.return_value = [
            {'product__id': self.prod_id, 'product__nama': 'Fake', 'total_sold': 10}
        ]
        mock_filter.return_value = mock_qs
        fake_prod = MagicMock()
        fake_prod.id = self.prod_id
        fake_prod.nama = 'Fake'
        fake_prod.foto.url = 'url'
        with patch('produk.api.Produk.objects.get', return_value=fake_prod):
            request = MockRequest(user_id=self.user1.id)
            status, result = get_most_popular_products(request)
            self.assertEqual(status, 200)
            self.assertEqual(result[0]['sold'], 10)

    @patch('produk.api.TransaksiItem.objects.filter')
    @patch('produk.api.Produk.objects.get')
    def test_get_top_selling_products(self, mock_prod_get, mock_filter):
        mock_qs = MagicMock()
        mock_qs.values.return_value = mock_qs
        mock_qs.annotate.return_value = mock_qs
        mock_qs.order_by.return_value = [
            {'product__id': self.prod_id, 'product__nama': 'Hot', 'product__foto': 'img', 'sold': 5}
        ]
        mock_filter.return_value = mock_qs
        fake_prod = MagicMock(id=self.prod_id, nama='Hot', foto='img')
        mock_prod_get.return_value = fake_prod
        request = MockRequest(user_id=self.user1.id)
        status, result = get_top_selling_products(request, year=2025, month=5)
        self.assertEqual(status, 200)
        self.assertEqual(result[0]['sold'], 5)

    def test_auth_bearer(self):
        auth = AuthBearer()
        valid_token = jwt.encode({'user_id': self.user1.id}, settings.SECRET_KEY, algorithm='HS256')
        req = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {valid_token}')
        self.assertEqual(auth.authenticate(req, valid_token), self.user1.id)
        invalid_token = jwt.encode({'user_id': self.user1.id}, 'wrong', algorithm='HS256')
        self.assertIsNone(auth.authenticate(None, invalid_token))

    @patch('produk.api.get_produk_paginated')
    def test_get_produk_default(self, mock_paginated):
        mock_paginated.return_value = (200, {'items': [], 'total':0, 'page':1, 'per_page':7, 'total_pages':0})
        request = MockRequest(user_id=self.user1.id)
        get_produk_default(request, sort='-id')
        mock_paginated.assert_called_once_with(request, page=1, sort='-id')

    def test_invalid_per_page(self):
        request = MockRequest(user_id=self.user1.id, get_params={'per_page': 'abc'})
        status, resp = get_produk_paginated(request, page=1, sort='stok')
        self.assertEqual(status, 200)
        self.assertEqual(resp['per_page'], 7)
