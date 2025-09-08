from rest_framework import serializers
from django.db.models import Q
from .models import (
    Plan, PrecioPlan, RestriccionPlan,
    Servicio, Beneficio, PlanServicio, PlanBeneficio,
    Disciplina, DisciplinaPlan, HorarioDisciplina,
    AltaPlan, Acceso, ServicioBeneficio
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
    dia_display = serializers.SerializerMethodField()

    class Meta:
        model = RestriccionPlan
        fields = [
            "id", "plan", "dia", "dia_display",
            "hora_inicio", "hora_fin",
            "is_active", "created_at", "updated_at",
            "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def get_dia_display(self, obj):
        nombres = {1:"Lunes",2:"Martes",3:"Miércoles",4:"Jueves",5:"Viernes",6:"Sábado",7:"Domingo"}
        return nombres.get(getattr(obj, "dia", None))

    def validate(self, attrs):
        """
        Opcional: valida que si se informan horas haya ambas y que no traslapen con otras del mismo día/plan.
        """
        dia = attrs.get("dia", getattr(self.instance, "dia", None))
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        hi = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        hf = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))

        if not dia or not plan:
            return attrs

        # Si una hora viene, deben venir ambas
        if bool(hi) ^ bool(hf):
            raise serializers.ValidationError({"hora_inicio": "Indica inicio y fin (o deja ambas vacías)"})

        if hi and hf and hi >= hf:
            raise serializers.ValidationError({"hora_inicio": "La hora de inicio debe ser menor que la hora fin"})

        # Anti-traslape (si hay horas)
        if hi and hf:
            qs = RestriccionPlan.objects.filter(plan=plan, dia=dia)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            # traslape si (aStart < bEnd) && (bStart < aEnd)
            overlap = qs.filter(Q(hora_inicio__lt=hf) & Q(hora_fin__gt=hi)).exists()
            if overlap:
                raise serializers.ValidationError({"hora_inicio": "Traslapa con otra restricción existente para ese día"})
        return attrs



class ServicioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Servicio
        fields = [
            "id", "empresa", "empresa_nombre",
            "nombre", "descripcion", "icono",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at","updated_at","created_by","updated_by")
        extra_kwargs = {
            "empresa": {"required": False},
            "descripcion": {"required": False, "allow_blank": True},
            "icono": {"required": False, "allow_blank": True},
        }

    def validate_nombre(self, v):
        v = (v or "").strip()
        if not v:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return v


class BeneficioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Beneficio
        fields = [
            "id", "empresa", "empresa_nombre",
            "nombre", "descripcion",
            "tipo_descuento", "valor", "unidad",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
        extra_kwargs = {
            "empresa": {"required": False},          # la pondremos en el ViewSet si falta
            "valor":   {"required": False, "allow_null": True},
            "unidad":  {"required": False, "allow_null": True},
            "descripcion": {"required": False, "allow_blank": True},
        }

    # Normalizaciones ligeras
    def validate_nombre(self, v: str):
        v = (v or "").strip()
        if not v:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return v

    def validate_tipo_descuento(self, v: str):
        v = (v or "").strip().lower()
        # valores válidos en tu modelo: '', 'porcentaje', 'monto'
        if v not in ("", "porcentaje", "monto"):
            raise serializers.ValidationError("Tipo de descuento inválido.")
        return v

    def validate(self, data):
        """
        Reglas:
        - si hay tipo_descuento -> valor es obligatorio (unidad sigue siendo opcional)
        - si NO hay tipo_descuento -> ignoramos valor/unidad (el ViewSet/Frontend ya los limpia)
        """
        tipo = data.get("tipo_descuento", getattr(self.instance, "tipo_descuento", "")) or ""
        if tipo in ("porcentaje", "monto"):
            valor = data.get("valor", getattr(self.instance, "valor", None))
            if valor in (None, ""):
                raise serializers.ValidationError({"valor": "Indica el valor del descuento."})
        return data


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


class ServicioBeneficioSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)
    beneficio_nombre = serializers.CharField(source="beneficio.nombre", read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(
        source="servicio.empresa", read_only=True
    )  # útil para filtrar/inspección

    class Meta:
        model = ServicioBeneficio
        fields = [
            "id",
            "servicio", "servicio_nombre",
            "beneficio", "beneficio_nombre",
            "vigencia_inicio", "vigencia_fin",
            "notas", "usuario",
            "empresa",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at","updated_at","created_by","updated_by","empresa")

    def validate(self, attrs):
        servicio = attrs.get("servicio") or getattr(self.instance, "servicio", None)
        beneficio = attrs.get("beneficio") or getattr(self.instance, "beneficio", None)
        if servicio and beneficio:
            s_emp = getattr(servicio, "empresa_id", None)
            b_emp = getattr(beneficio, "empresa_id", None)
            if s_emp and b_emp and s_emp != b_emp:
                raise serializers.ValidationError("Servicio y beneficio deben pertenecer a la misma empresa.")
        # Vigencia coherente
        vi = attrs.get("vigencia_inicio") or getattr(self.instance, "vigencia_inicio", None)
        vf = attrs.get("vigencia_fin") or getattr(self.instance, "vigencia_fin", None)
        if vi and vf and vi > vf:
            raise serializers.ValidationError("La vigencia de inicio no puede ser mayor a la vigencia fin.")
        return attrs
      
      
