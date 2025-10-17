from rest_framework import serializers
from .models import CodigoDescuento, Venta, DetalleVenta, MetodoPago
from django.db.models import Sum

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



class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MetodoPago
        fields = ("id", "venta", "forma_pago", "importe", "created_at", "updated_at")
        read_only_fields = ("created_at","updated_at")

class DetalleVentaSerializer(serializers.ModelSerializer):
    plan_nombre     = serializers.CharField(source="plan.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    codigo          = serializers.CharField(source="codigo_descuento.codigo", read_only=True)

    class Meta:
        model = DetalleVenta
        fields = "__all__"
        read_only_fields = ("created_at","updated_at","created_by","updated_by","is_active")

    def validate(self, data):
        if not data.get("plan") and not data.get("producto"):
            raise serializers.ValidationError("Debes indicar un plan o un producto.")
        return data

class VentaSerializer(serializers.ModelSerializer):
    detalles      = DetalleVentaSerializer(many=True, read_only=True)
    pagos         = MetodoPagoSerializer(many=True, read_only=True)
    cliente_nombre = serializers.SerializerMethodField()
    total_pagado   = serializers.SerializerMethodField()
    saldo          = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = "__all__"
        read_only_fields = ("created_at","updated_at","created_by","updated_by","is_active")

    def get_cliente_nombre(self, obj):
        return getattr(obj.cliente, "nombre_completo", None) or str(obj.cliente)

    def get_total_pagado(self, obj):
        # si el queryset viene anotado, úsalo; si no, calcula rápido
        val = getattr(obj, "total_pagado", None)
        if val is not None:
            return str(val)
        return str(obj.pagos.aggregate(s=Sum("importe"))["s"] or 0)

    def get_saldo(self, obj):
        try:
            pagado = getattr(obj, "total_pagado", None)
            if pagado is None:
                pagado = obj.pagos.aggregate(s=Sum("importe"))["s"] or 0
            return str((obj.total or 0) - pagado)
        except Exception:
            return None