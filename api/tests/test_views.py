import pytest
from django.urls import reverse
from rest_framework import status
from api.models import Product


@pytest.mark.django_db
def test_hello_world(client):

    url = reverse("api:hello")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "halooo duniaaaaa.......... "}


@pytest.mark.django_db
def test_create_product(client):

    url = reverse("api:create-product")
    data = {
        "name": "Kromium",
        "stock": 100,
        "description": "Premium kroket with chicken and veggies",
    }

    response = client.post(url, data)
    print(response.content)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Product created successfully"
    assert "id" in response.json()

    product = Product.objects.get(id=response.json()["id"])
    assert product.name == data["name"]
    assert product.stock == data["stock"]
    assert product.description == data["description"]


@pytest.mark.django_db
def test_list_products(client):

    product_data = [
        {"name": "Kromium", "stock": 50, "description": "Delicious kroket"},
        {
            "name": "Kromium Spicy",
            "stock": 20,
            "description": "Spicy kroket with chicken",
        },
    ]

    for data in product_data:
        Product.objects.create(**data)

    url = reverse("api:list-products")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(product_data)

    for i, product in enumerate(response.json()):
        assert product["name"] == product_data[i]["name"]
        assert product["stock"] == product_data[i]["stock"]
        assert product["description"] == product_data[i]["description"]
