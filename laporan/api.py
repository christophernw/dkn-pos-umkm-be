from ninja import Router
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest
from produk.models import Produk, KategoriProduk
from produk.schemas import PaginatedResponseSchema, ProdukSchema, CreateProdukSchema

router = Router()

