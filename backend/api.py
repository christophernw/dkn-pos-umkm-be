import os
from ninja import NinjaAPI
from authentication.api import router as auth_router

api = NinjaAPI()
api.add_router("/auth/", auth_router)

@api.get("/version")
def get_version(request):
    return {"version": os.environ.get("APP_VERSION", "unknown")}
