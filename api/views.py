from django.shortcuts import render

# Create your views here.
from ninja import Router

router = Router()

# izin coba staginggg

@router.get("/hello")
def hello_world(request):
    return {"message": "halooo duniaaaaa.......... "}