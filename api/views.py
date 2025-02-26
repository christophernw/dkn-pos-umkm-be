from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def hello_world(request):
    return JsonResponse({"message": "halooo duniaaaaa.......... "})


@csrf_exempt
def create_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        stock = request.POST.get("stock")
        description = request.POST.get("description")

        product = Product.objects.create(
            name=name, stock=stock, description=description
        )
        return JsonResponse(
            {"id": product.id, "message": "Product created successfully"}
        )

    return JsonResponse({"message": "Only POST method is allowed."}, status=400)


def list_products(request):
    if request.method == "GET":
        products = Product.objects.all()
        product_list = [
            {
                "name": product.name,
                "stock": product.stock,
                "description": product.description,
            }
            for product in products
        ]
        return JsonResponse(product_list, safe=False)

    return JsonResponse({"message": "Only GET method is allowed."}, status=400)
