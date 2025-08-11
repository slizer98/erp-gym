from rest_framework import serializers
from .models import CodigoDescuento

class CodigoDescuentoSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.get_full_name", read_only=True)
    usable = serializers.SerializerMethodField()

    class Meta:
        model = CodigoDescuento
        fields = [
            "id", "empresa", "empresa_nombre",
            "codigo", "descuento", "tipo_descuento",
            "cantidad", "restantes",
            "usuario", "usuario_nombre",
            "usable",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "restantes")

    def get_usable(self, obj):
        return obj.is_active and obj.restantes > 0

    def validate(self, attrs):
        tipo = attrs.get("tipo_descuento", getattr(self.instance, "tipo_descuento", None))
        descuento = attrs.get("descuento", getattr(self.instance, "descuento", None))
        cantidad = attrs.get("cantidad", getattr(self.instance, "cantidad", None))

        if descuento is not None and descuento < 0:
            raise serializers.ValidationError("El descuento no puede ser negativo.")

        if tipo == CodigoDescuento.Tipo.PORCENTAJE and descuento is not None:
            # 0 < descuento <= 100 (permitimos 0? normalmente no tiene sentido)
            if descuento <= 0 or descuento > 100:
                raise serializers.ValidationError("Para porcentaje, el descuento debe estar en (0, 100].")

        if cantidad is not None and cantidad < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa.")

        return attrs
