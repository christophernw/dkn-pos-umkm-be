from ninja import NinjaAPI
from authentication.api import router as auth_router
from search.api import router as search_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)
api.add_router("/search/", search_router)