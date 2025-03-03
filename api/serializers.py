from ninja import Schema

class ProductUpdateSchema(Schema):
    name: str
    price: float
    stock: int
    category: str
