import os
from ninja import NinjaAPI
from authentication.api import router as auth_router
from transaksi.api import router as transaksi_router
from laporan.api import router as laporan_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)
api.add_router("/transaksi", transaksi_router)
api.add_router("/laporan", laporan_router)

@api.get("/version")
def get_version(request):
    return {"version": os.environ.get("APP_VERSION", "unknown")}
