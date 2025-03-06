from ninja import NinjaAPI
from produk.api import router as produk_router, create_router as produk_create_router
from authentication.api import router as auth_router
from search.api import router as search_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)
api.add_router("/search/", search_router)
api.add_router("/produk", produk_router)
api.add_router("/produk/create", produk_create_router)