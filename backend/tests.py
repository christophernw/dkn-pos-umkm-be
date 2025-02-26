import pytest

@pytest.fixture
def sample_produk():
    return[
        {
            "id": 1,
            "nama": "Produk A",
            "hargaJual": 10000.0,
            "hargaModal": 7000.0,
            "stok": 5,
            "satuan": "pcs",
            "kategori": "Elektronik",
            "foto": "https://example.com/produk_a.jpg"
        },
        {
            "id": 2,
            "nama": "Produk B",
            "hargaJual": 20000.0,
            "hargaModal": 15000.0,
            "stok": 10,
            "satuan": "kg",
            "kategori": "Makanan",
            "foto": "https://example.com/produk_b.jpg"
        },
        {
            "id": 3,
            "nama": "Produk C",
            "hargaJual": 15000.0,
            "hargaModal": 12000.0,
            "stok": 3,
            "satuan": "liter",
            "kategori": "Minuman",
            "foto": "https://example.com/produk_c.jpg"
        },
    ]

def test_sort_produk_by_stock_descending(sample_produk):
    sorted_produk = sort_produk_by_stock_descending(sample_produk)
    sorted_id = [p["id"] for p in sorted_produk]
    assert sorted_id == [2,1,3]

def test_sort_produk_by_stock_ascending(sample_produk):
    sorted_produk = sort_produk_by_stock_ascending(sample_produk)
    sorted_id = [p["id"] for p in sorted_produk]
    assert sorted_id == [3,1,2]

def test_sort_produk_