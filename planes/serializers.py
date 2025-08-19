from rest_framework import serializers
from .models import (
    Plan, PrecioPlan, RestriccionPlan,
    Servicio, Beneficio, PlanServicio, PlanBeneficio,
    Disciplina, DisciplinaPlan, HorarioDisciplina,
    AltaPlan, Acceso
)

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



class ServicioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = Servicio
        fields = ["id", "empresa", "empresa_nombre", "nombre", "descripcion",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class BeneficioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = Beneficio
        fields = ["id", "empresa", "empresa_nombre", "nombre", "descripcion",
                  "tipo_descuento", "valor", "unidad",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class PlanServicioSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)
    class Meta:
        model = PlanServicio
        fields = ["id", "plan", "plan_nombre", "servicio", "servicio_nombre",
                  "precio", "icono", "fecha_baja",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        plan = attrs.get("plan") or getattr(self.instance, "plan", None)
        servicio = attrs.get("servicio") or getattr(self.instance, "servicio", None)
        if plan and servicio and plan.empresa_id != servicio.empresa_id:
            raise serializers.ValidationError("El servicio y el plan deben pertenecer a la misma empresa.")
        return attrs


class PlanBeneficioSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    beneficio_nombre = serializers.CharField(source="beneficio.nombre", read_only=True)
    class Meta:
        model = PlanBeneficio
        fields = ["id", "plan", "plan_nombre", "beneficio", "beneficio_nombre",
                  "vigencia_inicio", "vigencia_fin",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        plan = attrs.get("plan") or getattr(self.instance, "plan", None)
        beneficio = attrs.get("beneficio") or getattr(self.instance, "beneficio", None)
        if plan and beneficio and plan.empresa_id != beneficio.empresa_id:
            raise serializers.ValidationError("El beneficio y el plan deben pertenecer a la misma empresa.")
        return attrs


class DisciplinaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    instructor_nombre = serializers.CharField(source="instructor.get_full_name", read_only=True)
    class Meta:
        model = Disciplina
        fields = ["id", "empresa", "empresa_nombre", "nombre", "instructor", "instructor_nombre",
                  "limite_personas", "recomendaciones",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class DisciplinaPlanSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    disciplina_nombre = serializers.CharField(source="disciplina.nombre", read_only=True)
    class Meta:
        model = DisciplinaPlan
        fields = ["id", "plan", "plan_nombre", "disciplina", "disciplina_nombre",
                  "tipo_acceso", "numero_accesos",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        plan = attrs.get("plan") or getattr(self.instance, "plan", None)
        disciplina = attrs.get("disciplina") or getattr(self.instance, "disciplina", None)
        if plan and disciplina and plan.empresa_id != disciplina.empresa_id:
            raise serializers.ValidationError("La disciplina y el plan deben pertenecer a la misma empresa.")
        return attrs


class HorarioDisciplinaSerializer(serializers.ModelSerializer):
    disciplina_nombre = serializers.CharField(source="disciplina.nombre", read_only=True)
    class Meta:
        model = HorarioDisciplina
        fields = ["id", "disciplina", "disciplina_nombre", "hora_inicio", "hora_fin",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class AltaPlanSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    class Meta:
        model = AltaPlan
        fields = ["id", "empresa", "empresa_nombre", "sucursal", "sucursal_nombre",
                  "cliente", "cliente_nombre", "plan", "plan_nombre",
                  "fecha_alta", "fecha_vencimiento", "renovacion",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        sucursal = attrs.get("sucursal") or getattr(self.instance, "sucursal", None)
        plan = attrs.get("plan") or getattr(self.instance, "plan", None)
        if sucursal and empresa and sucursal.empresa_id != empresa.id:
            raise serializers.ValidationError("La sucursal no pertenece a la empresa.")
        if plan and empresa and plan.empresa_id != empresa.id:
            raise serializers.ValidationError("El plan no pertenece a la empresa.")
        return attrs


class AccesoSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)
    class Meta:
        model = Acceso
        fields = ["id", "cliente", "cliente_nombre", "empresa", "empresa_nombre",
                  "sucursal", "sucursal_nombre", "tipo_acceso", "puerta", "temperatura", "fecha",
                  "is_active", "created_at", "updated_at", "created_by", "updated_by"]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
