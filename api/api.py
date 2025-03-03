from ninja import NinjaAPI
from api.views import router as product_router

api = NinjaAPI()
api.add_router("/products/", product_router)
