from rest_framework.decorators import action
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import transaction
from django.core.cache import cache
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import (Plan, PrecioPlan, RestriccionPlan, Servicio, Beneficio, 
                     PlanServicio, PlanBeneficio, Disciplina, DisciplinaPlan, HorarioDisciplina,
                     AltaPlan, Acceso, ServicioBeneficio, PlanRevision, PrecioPlanRevision, RestriccionPlanRevision,
    PlanServicioRevision, PlanBeneficioRevision, DisciplinaPlanRevision)
from .serializers import (PlanSerializer, PrecioPlanSerializer, RestriccionPlanSerializer, ServicioSerializer, BeneficioSerializer, PlanServicioSerializer, PlanBeneficioSerializer,
    DisciplinaSerializer, DisciplinaPlanSerializer, HorarioDisciplinaSerializer,
    AltaPlanSerializer, AccesoSerializer, ServicioBeneficioSerializer,
    PlanRevisionSerializer, PrecioPlanRevisionSerializer, RestriccionPlanRevisionSerializer,
    PlanServicioRevisionSerializer, PlanBeneficioRevisionSerializer, DisciplinaPlanRevisionSerializer
)
from .services import publish_plan_revision


def _publish_after_commit(plan, vigente_desde=None, vigente_hasta=None):
    @transaction.on_commit
    def _do():
        publish_plan_revision(plan, vigente_desde=vigente_desde or now().date(), vigente_hasta=vigente_hasta)


class PlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Plan.objects.select_related("empresa", "usuario").all().order_by("-id")
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"

    search_fields = ("nombre", "tipo_plan", "descripcion")
    ordering_fields = ("id", "nombre", "desde", "hasta", "updated_at")
    ordering = ("-updated_at",)

    def perform_create(self, serializer):
        plan =serializer.save(created_by=self.request.user, updated_by=self.request.user)
        # _schedule_auto_publish(plan)

    def perform_update(self, serializer):
        plan = serializer.save(updated_by=self.request.user)
        if plan.altas.exists():            # <— solo si ya hay clientes
            _publish_after_commit(plan) 
            
    def perform_destroy(self, instance):
        if instance.altas.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No puedes eliminar este plan: tiene altas activas.")
        super().perform_destroy(instance)
    
        
    @action(detail=True, methods=["post"], url_path="publicar-revision")
    def publicar_revision(self, request, pk=None):
        """
        Congela el estado actual del plan en una nueva PlanRevision y copia hijos.
        Payload opcional:
          - vigente_desde (YYYY-MM-DD)
          - vigente_hasta (YYYY-MM-DD)
        """
        plan = self.get_object()
        vigente_desde = request.data.get("vigente_desde") or None
        vigente_hasta = request.data.get("vigente_hasta") or None

        with transaction.atomic():
            rev = publish_plan_revision(plan, vigente_desde=vigente_desde, vigente_hasta=vigente_hasta)

        return Response(PlanRevisionSerializer(rev).data, status=201)


class PrecioPlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (PrecioPlan.objects
                .select_related("plan", "plan__empresa", "usuario")
                .all().order_by("-id"))
    serializer_class = PrecioPlanSerializer
    permission_classes = [IsAuthenticatedInCompany]
    # El mixin filtrará por empresa a través de plan.empresa.
    # Como el modelo no tiene campo 'empresa' directo, el mixin por defecto no vería el FK.
    # Opción rápida: sobrescribe get_queryset:
    def get_queryset(self):
        qs = super().get_queryset()
        empresas_usuario = self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True)
        return qs.filter(plan__empresa_id__in=empresas_usuario)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
        
    def perform_create(self, serializer):
        obj = serializer.save(
            usuario=self.request.user,            
            created_by=self.request.user,
            updated_by=self.request.user
        )
        if obj.plan.altas.exists():
            _publish_after_commit(obj.plan)

    def perform_update(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        if obj.plan.altas.exists():
            _publish_after_commit(obj.plan)

    def perform_destroy(self, instance):
        plan = instance.plan
        super().perform_destroy(instance)
        if plan.altas.exists():
            _publish_after_commit(plan)


class RestriccionPlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Filtra por la empresa del plan: plan__empresa.
    Permite ?plan=ID y cualquier otro filtro adicional que quieras añadir.
    """
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = RestriccionPlanSerializer

    # clave: el mixin construye ...filter(plan__empresa_id=<company_id>)
    company_fk_name = "plan__empresa"

    queryset = (
        RestriccionPlan.objects
        .select_related("plan", "plan__empresa", "usuario")
        .all()
        .order_by("-id")
    )

    def get_queryset(self):
        qs = super().get_queryset()  # aplica plan__empresa_id
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)




class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)



class ServicioViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    serializer_class = ServicioSerializer
    queryset = Servicio.objects.select_related("empresa").all()

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion", "icono"]
    filterset_fields = ["empresa", "is_active"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["-id"]

    def perform_create(self, serializer):
        empresa = serializer.validated_data.get("empresa") or getattr(self.request.user, "empresa", None)
        if not empresa:
            raise ValidationError({"empresa": "Debe indicar la empresa."})
        serializer.save(empresa=empresa, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        if "empresa" in serializer.validated_data:
            serializer.validated_data.pop("empresa", None)
        super().perform_update(serializer)

class BeneficioViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    """
    Endpoints:
      GET    /beneficios/
      POST   /beneficios/
      GET    /beneficios/{id}/
      PATCH  /beneficios/{id}/
      DELETE /beneficios/{id}/
    """
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    serializer_class = BeneficioSerializer

    queryset = (
        Beneficio.objects
        .select_related("empresa")
        .all()
        .order_by("-id")
    )

    # Filtros, búsqueda y orden
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["empresa", "tipo_descuento", "is_active"]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["id", "nombre", "created_at", "updated_at"]
    ordering = ["-id"]

    def perform_create(self, serializer):
        """
        Híbrido:
        - Si el front manda empresa en el payload, se usa esa.
        - Si NO la manda, intentamos tomarla de self.request.user.empresa (ajusta si tu user se relaciona distinto).
        - Si no hay forma de determinarla, levantamos error claro.
        """
        empresa = serializer.validated_data.get("empresa", None)

        if not empresa:
            # Ajusta esta línea según tu relación real de usuario->empresa
            empresa = getattr(self.request.user, "empresa", None)

        if not empresa:
            raise ValidationError({"empresa": "Debe indicar la empresa."})

        serializer.save(
            empresa=empresa,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        """
        Impide cambiar la empresa en updates.
        """
        if "empresa" in serializer.validated_data:
            serializer.validated_data.pop("empresa", None)
        super().perform_update(serializer)
# Relaciones con Plan (scoped via plan.empresa)
class PlanServicioViewSet(BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = PlanServicio.objects.select_related("plan", "plan__empresa", "servicio").all().order_by("id")
    serializer_class = PlanServicioSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        return qs.filter(plan__empresa_id=emp_id) if emp_id else qs

class PlanBeneficioViewSet(BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = PlanBeneficio.objects.select_related("plan", "plan__empresa", "beneficio").all().order_by("id")
    serializer_class = PlanBeneficioSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        return qs.filter(plan__empresa_id=emp_id) if emp_id else qs

# Disciplinas
class DisciplinaViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    queryset = Disciplina.objects.select_related("empresa", "instructor").all().order_by("id")
    serializer_class = DisciplinaSerializer

class DisciplinaPlanViewSet(BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = DisciplinaPlan.objects.select_related("plan", "plan__empresa", "disciplina").all().order_by("id")
    serializer_class = DisciplinaPlanSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        return qs.filter(plan__empresa_id=emp_id) if emp_id else qs

class HorarioDisciplinaViewSet(BaseAuthViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = HorarioDisciplina.objects.select_related("disciplina", "disciplina__empresa").all().order_by("id")
    serializer_class = HorarioDisciplinaSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        return qs.filter(disciplina__empresa_id=emp_id) if emp_id else qs

# Operativa (Altas/Accesos)
class AltaPlanViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    queryset = AltaPlan.objects.select_related("empresa", "sucursal", "cliente", "plan").all().order_by("-id")
    serializer_class = AltaPlanSerializer

class AccesoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    queryset = Acceso.objects.select_related("empresa", "sucursal", "cliente").all().order_by("-fecha")
    serializer_class = AccesoSerializer
    

class ServicioBeneficioViewSet(viewsets.ModelViewSet):
    """
    CRUD de la relación Servicio-Beneficio.
    Scoping por empresa: X-Empresa-Id debe coincidir con servicio.empresa (o beneficio.empresa).
    Filtros:
      - ?servicio=<id>
      - ?beneficio=<id>
    """
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = ServicioBeneficioSerializer
    queryset = ServicioBeneficio.objects.select_related(
        "servicio", "servicio__empresa", "beneficio"
    ).all().order_by("id")

    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        if emp_id:
            qs = qs.filter(servicio__empresa_id=emp_id)
        # filtros opcionales
        servicio_id = self.request.query_params.get("servicio")
        beneficio_id = self.request.query_params.get("beneficio")
        if servicio_id:
            qs = qs.filter(servicio_id=servicio_id)
        if beneficio_id:
            qs = qs.filter(beneficio_id=beneficio_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    """
    CRUD de la relación Servicio-Beneficio.
    Scoping por empresa: X-Empresa-Id debe coincidir con servicio.empresa (o beneficio.empresa).
    Filtros:
      - ?servicio=<id>
      - ?beneficio=<id>
    """
    # permission_classes = [IsAuthenticatedInCompany]
    serializer_class = ServicioBeneficioSerializer
    queryset = ServicioBeneficio.objects.select_related(
        "servicio", "servicio__empresa", "beneficio"
    ).all().order_by("id")

    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")
        if emp_id:
            qs = qs.filter(servicio__empresa_id=emp_id)
        # filtros opcionales
        servicio_id = self.request.query_params.get("servicio")
        beneficio_id = self.request.query_params.get("beneficio")
        if servicio_id:
            qs = qs.filter(servicio_id=servicio_id)
        if beneficio_id:
            qs = qs.filter(beneficio_id=beneficio_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        
class PlanRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "plan__empresa"
    serializer_class = PlanRevisionSerializer
    queryset = PlanRevision.objects.select_related("plan", "plan__empresa").all().order_by("-version")

    # filtros: ?plan=<id> y/o ?vigentes_a=YYYY-MM-DD
    def get_queryset(self):
        qs = super().get_queryset()
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        vig = self.request.query_params.get("vigentes_a")
        if vig:
            qs = qs.filter(
                Q(vigente_desde__isnull=True) | Q(vigente_desde__lte=vig),
                Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=vig)
            )
        return qs


class PrecioPlanRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "revision__plan__empresa"
    serializer_class = PrecioPlanRevisionSerializer
    queryset = PrecioPlanRevision.objects.select_related("revision", "revision__plan", "revision__plan__empresa").all()


class RestriccionPlanRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "revision__plan__empresa"
    serializer_class = RestriccionPlanRevisionSerializer
    queryset = RestriccionPlanRevision.objects.select_related("revision", "revision__plan", "revision__plan__empresa").all()


class PlanServicioRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "revision__plan__empresa"
    serializer_class = PlanServicioRevisionSerializer
    queryset = PlanServicioRevision.objects.select_related("revision", "revision__plan", "revision__plan__empresa", "servicio").all()


class PlanBeneficioRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "revision__plan__empresa"
    serializer_class = PlanBeneficioRevisionSerializer
    queryset = PlanBeneficioRevision.objects.select_related("revision", "revision__plan", "revision__plan__empresa", "beneficio").all()


class DisciplinaPlanRevisionViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "revision__plan__empresa"
    serializer_class = DisciplinaPlanRevisionSerializer
    queryset = DisciplinaPlanRevision.objects.select_related("revision", "revision__plan", "revision__plan__empresa", "disciplina").all()
