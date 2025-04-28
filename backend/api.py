import os
from ninja import NinjaAPI
from authentication.api import router as auth_router, produk_router, transaksi_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)
api.add_router("/produk", produk_router)
api.add_router("/transaksi", transaksi_router)

@api.get("/version")
def get_version(request):
    return {"version": os.environ.get("APP_VERSION", "unknown")}
