from ninja import Router, Query
from typing import List, Optional, Dict, Any, Tuple, Union
from django.db.models import Q, QuerySet
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from .models import Pemasukan, Pengeluaran, Produk, Transaksi
from .schemas import (
    PemasukanCreate,
    PemasukanRead,
    PengeluaranCreate,
    PengeluaranRead,
    TransaksiUpdate,
    PaginatedPemasukanResponseSchema,
)

router = Router()


# Helper functions
