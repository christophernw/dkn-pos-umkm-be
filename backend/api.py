import os
from ninja import NinjaAPI
from produk.api import router as produk_router
from authentication.api import router as auth_router
from transaksi.api import router as transaksi_router
from laporan.views import router as laporan_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)
api.add_router("/produk", produk_router)
api.add_router("/transaksi", transaksi_router)

@api.get("/version")
def get_version(request):
    return {"version": os.environ.get("APP_VERSION", "unknown")}
