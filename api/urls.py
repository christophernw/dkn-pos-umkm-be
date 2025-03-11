from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import MyViewSet  # Gantilah dengan ViewSet Anda

router = DefaultRouter()
router.register(r'myendpoint', MyViewSet)  # Sesuaikan dengan ViewSet Anda

urlpatterns = [
    path('', include(router.urls)),
]
