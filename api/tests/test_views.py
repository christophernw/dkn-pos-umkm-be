from django.test import TestCase
from django.urls import reverse
from api.models import Product

class ProductTestCase(TestCase):
    def test_create_product(self):
        url = reverse('api:create-product')
        data = {
            "name": "Kromium",
            "stock": 100,
            "description": "Premium kroket with chicken and veggies"
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], "Product created successfully")
        self.assertIn('id', response.json())

    def test_list_products(self):
        # Create some products in the database
        product_data = [
            {"name": "Kromium", "stock": 50, "description": "Delicious kroket"},
            {"name": "Kromium Spicy", "stock": 20, "description": "Spicy kroket with chicken"},
        ]
        
        for data in product_data:
            Product.objects.create(**data)

        url = reverse('api:list-products')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), len(product_data))

    def test_hello_world(self):
        url = reverse('api:hello')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "halooo duniaaaaa.......... "})
