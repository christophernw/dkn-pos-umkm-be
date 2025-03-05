from ninja import NinjaAPI
from produk.api import router as produk_router

api = NinjaAPI()
api.add_router("/produk", produk_router)