from django.urls import path
from .views import hello_world, create_product, list_products

app_name = 'api'  

urlpatterns = [
    path('hello/', hello_world, name='hello'),
    path('products/', list_products, name='list-products'),  
    path('products/create', create_product, name='create-product'),  
]
