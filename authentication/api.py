from django.contrib.auth.models import User
from ninja import Router, Schema
from django.contrib.auth.hashers import make_password

router = Router()

class RegisterSchema(Schema):
    username: str
    password: str
    email: str

@router.post("/register")
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        return {"error": "Username already exists"}
    
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password)  # Hash the password
    )
    return {"message": "User registered successfully", "user_id": user.id}