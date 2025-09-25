from rest_framework import serializers
from .models import Almacen, CategoriaProducto, Producto, MovimientoProducto

class AlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "is_active")

    def validate(self, attrs):
        empresa = attrs.get('empresa') or getattr(self.instance, 'empresa', None)
        sucursal = attrs.get('sucursal') or getattr(self.instance, 'sucursal', None)
        if sucursal and empresa and sucursal.empresa_id != empresa.id:
            raise serializers.ValidationError("La sucursal no pertenece a la empresa indicada.")
        return attrs

class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "is_active")

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Producto
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "is_active")

class MovimientoProductoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    almacen_nombre  = serializers.CharField(source="almacen.nombre", read_only=True)

    class Meta:
        model = MovimientoProducto
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "is_active")
