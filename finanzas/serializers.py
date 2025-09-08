from rest_framework import serializers
from .models import Proveedor, CategoriaEgreso, Egreso

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"
        read_only_fields = ("created_at","updated_at","created_by","updated_by","is_active")

class CategoriaEgresoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaEgreso
        fields = "__all__"
        read_only_fields = ("created_at","updated_at","created_by","updated_by","is_active")

class EgresoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Egreso
        fields = "__all__"
        read_only_fields = ("created_at","updated_at","created_by","updated_by","is_active")
