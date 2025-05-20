from rest_framework import serializers
from .models import Produk

class ProdukSerializer(serializers.ModelSerializer):
    foto = serializers.SerializerMethodField()

    class Meta:
        model = Produk
        fields = "__all__"

    def get_foto(self, obj):
        if obj.foto and hasattr(obj.foto, "url"):
            return obj.foto.url
        return ""