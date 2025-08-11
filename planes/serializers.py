from rest_framework import serializers
from .models import Plan, PrecioPlan, RestriccionPlan

class PlanSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.get_full_name", read_only=True)

    class Meta:
        model = Plan
        fields = [
            "id", "empresa", "empresa_nombre",
            "nombre", "descripcion", "acceso_multisucursal",
            "tipo_plan", "preventa", "desde", "hasta",
            "visitas_gratis", "usuario", "usuario_nombre",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        desde = attrs.get("desde", getattr(self.instance, "desde", None))
        hasta = attrs.get("hasta", getattr(self.instance, "hasta", None))
        preventa = attrs.get("preventa", getattr(self.instance, "preventa", False))

        # Fechas coherentes
        if desde and hasta and desde > hasta:
            raise serializers.ValidationError("La fecha 'desde' no puede ser posterior a 'hasta'.")

        # Si es preventa, sugiere que existan fechas
        if preventa and (not desde or not hasta):
            raise serializers.ValidationError("Para planes en preventa, proporciona 'desde' y 'hasta'.")
        return attrs


class PrecioPlanSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(
        source="plan.empresa", read_only=True
    )  # útil para scoping de empresa en la vista

    class Meta:
        model = PrecioPlan
        fields = [
            "id", "plan", "plan_nombre",
            "esquema", "tipo", "precio", "numero_visitas",
            "usuario",
            "empresa",  # read-only derivado del plan
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "empresa")

    def validate_precio(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value


class RestriccionPlanSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(
        source="plan.empresa", read_only=True
    )

    class Meta:
        model = RestriccionPlan
        fields = [
            "id", "plan", "plan_nombre",
            "dia", "hora_inicio", "hora_fin",
            "usuario",
            "empresa",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by", "empresa")

    def validate(self, attrs):
        hi = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        hf = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if hi and hf and hi >= hf:
            raise serializers.ValidationError("La hora de inicio debe ser menor que la hora de fin.")
        return attrs
