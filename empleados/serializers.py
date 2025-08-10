from rest_framework import serializers
from .models import UsuarioEmpresa

class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.get_full_name", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)

    class Meta:
        model = UsuarioEmpresa
        fields = [
            "id",
            "usuario", "usuario_nombre",
            "empresa", "empresa_nombre",
            "sucursal", "sucursal_nombre",
            "rol", "permisos",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
