from rest_framework.decorators import action
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch
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


# class PlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
#     queryset = Plan.objects.select_related("empresa", "usuario").all().order_by("-id")
#     serializer_class = PlanSerializer
#     permission_classes = [IsAuthenticatedInCompany]
#     company_fk_name = "empresa"

#     search_fields = ("nombre", "tipo_plan", "descripcion")
#     ordering_fields = ("id", "nombre", "desde", "hasta", "updated_at")
#     ordering = ("-updated_at",)

#     def perform_create(self, serializer):
#         plan =serializer.save(created_by=self.request.user, updated_by=self.request.user)
#         # _schedule_auto_publish(plan)

#     def perform_update(self, serializer):
#         plan = serializer.save(updated_by=self.request.user)
#         if plan.altas.exists():            # <— solo si ya hay clientes
#             _publish_after_commit(plan) 
            
#     def perform_destroy(self, instance):
#         if instance.altas.exists():
#             from rest_framework.exceptions import ValidationError
#             raise ValidationError("No puedes eliminar este plan: tiene altas activas.")
#         super().perform_destroy(instance)
    
        
#     @action(detail=True, methods=["post"], url_path="publicar-revision")
#     def publicar_revision(self, request, pk=None):
#         """
#         Congela el estado actual del plan en una nueva PlanRevision y copia hijos.
#         Payload opcional:
#           - vigente_desde (YYYY-MM-DD)
#           - vigente_hasta (YYYY-MM-DD)
#         """
#         plan = self.get_object()
#         vigente_desde = request.data.get("vigente_desde") or None
#         vigente_hasta = request.data.get("vigente_hasta") or None

#         with transaction.atomic():
#             rev = publish_plan_revision(plan, vigente_desde=vigente_desde, vigente_hasta=vigente_hasta)

#         return Response(PlanRevisionSerializer(rev).data, status=201)

class PlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        Plan.objects
            .select_related("empresa", "usuario")
            .all()
            .order_by("-id")
    )
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"

    search_fields = ("nombre", "tipo_plan", "descripcion")
    ordering_fields = ("id", "nombre", "desde", "hasta", "updated_at")
    ordering = ("-updated_at",)

    def get_queryset(self):
        qs = super().get_queryset()
        include = self.request.query_params.get("include", "")

        if "servicios" in include.split(","):
            # Descubre el nombre correcto del related_name hacia Plan
            accessor = PlanServicio._meta.get_field("plan").remote_field.get_accessor_name()
            ps_qs = PlanServicio.objects.select_related("servicio").order_by("id")

            qs = qs.prefetch_related(
                Prefetch(
                    accessor,                    # <- en lugar de 'planservicio_set'
                    queryset=ps_qs,
                    to_attr="_prefetched_planservicios",
                )
            )
        return qs

    def perform_create(self, serializer):
        plan = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user
        )

    def perform_update(self, serializer):
        plan = serializer.save(updated_by=self.request.user)
        if plan.altas.exists():
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
            rev = publish_plan_revision(
                plan,
                vigente_desde=vigente_desde,
                vigente_hasta=vigente_hasta,
            )

        return Response(PlanRevisionSerializer(rev).data, status=201)

class PrecioPlanViewSet(viewsets.ModelViewSet):
    """
    /api/v1/planes/precios/
    - Scoping por empresa a través de plan__empresa_id (usando X-Empresa-Id).
    - Filtro por ?plan=ID, tipo, esquema, etc.
    """
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = PrecioPlanSerializer
    queryset = (PrecioPlan.objects
                .select_related("plan", "plan__empresa", "usuario")
                .all())

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # OJO: 'empresa' NO es campo directo en PrecioPlan → se filtra con plan__empresa en get_queryset
    filterset_fields = ["plan", "tipo", "esquema", "numero_visitas", "is_active"]
    ordering_fields = ["id", "precio", "created_at", "updated_at"]
    ordering = ["id"]

    def get_queryset(self):
        qs = super().get_queryset()
        # scope por empresa desde cabecera (tu patrón actual)
        emp_id = self.request.headers.get("X-Empresa-Id")
        if emp_id:
            qs = qs.filter(plan__empresa_id=emp_id)

        # respeta parámetro ?plan=ID
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs

    def perform_create(self, serializer):
        plan = serializer.validated_data.get("plan")
        emp_id = self.request.headers.get("X-Empresa-Id")

        # seguridad: el plan debe pertenecer a la empresa del request
        if emp_id and plan and str(plan.empresa_id) != str(emp_id):
            raise ValidationError("El plan no pertenece a tu empresa.")

        obj = serializer.save(
            usuario=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

        # Si ya tiene altas, dispara publicación si usas ese flujo
        if hasattr(plan, "altas") and plan.altas.exists():
            # _publish_after_commit(plan)
            pass

    def perform_update(self, serializer):
        obj = serializer.save(updated_by=self.request.user)
        plan = obj.plan
        if hasattr(plan, "altas") and plan.altas.exists():
            # _publish_after_commit(plan)
            pass

    def perform_destroy(self, instance):
        plan = instance.plan
        super().perform_destroy(instance)
        if hasattr(plan, "altas") and plan.altas.exists():
            # _publish_after_commit(plan)
            pass



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
class PlanServicioViewSet(viewsets.ModelViewSet):
    """
    /api/v1/planes/servicios/
    Lista/crea relaciones Servicio <-> Plan.
    - LIST exige ?plan=ID y sólo devuelve servicios de ese plan.
    - CREATE/PATCH/PUT validan que plan y servicio pertenezcan a la empresa del request.
    """
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = PlanServicioSerializer
    queryset = (PlanServicio.objects
                .select_related("plan", "plan__empresa", "servicio")
                .all())

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    # Nota: aunque agregamos filterset_fields, LIST no devolverá nada si no pasas ?plan
    filterset_fields = ["plan", "servicio", "is_active"]
    ordering_fields = ["id", "created_at", "updated_at"]
    ordering = ["id"]

    # === Forzamos que LIST siempre sea por plan ===
    def list(self, request, *args, **kwargs):
        plan_id = request.query_params.get("plan")
        if not plan_id:
            # evita que accidentalmente devuelvas todo
            return Response(
                {"detail": "Debes enviar ?plan=ID para listar servicios del plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        emp_id = self.request.headers.get("X-Empresa-Id")

        # scope empresa del plan
        if emp_id:
            qs = qs.filter(plan__empresa_id=emp_id)

        # scope por plan (si viene lo aplicamos aquí también)
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)

        return qs

    def perform_create(self, serializer):
        emp_id = self.request.headers.get("X-Empresa-Id")
        plan = serializer.validated_data.get("plan")
        servicio = serializer.validated_data.get("servicio")

        if not plan:
            raise ValidationError({"plan": "Es obligatorio."})
        if not servicio:
            raise ValidationError({"servicio": "Es obligatorio."})

        if emp_id and str(plan.empresa_id) != str(emp_id):
            raise ValidationError("El plan no pertenece a tu empresa.")
        if plan.empresa_id != servicio.empresa_id:
            raise ValidationError("El servicio y el plan deben pertenecer a la misma empresa.")

        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        # Mismas validaciones en update
        emp_id = self.request.headers.get("X-Empresa-Id")
        plan = serializer.validated_data.get("plan") or getattr(self.get_object(), "plan", None)
        servicio = serializer.validated_data.get("servicio") or getattr(self.get_object(), "servicio", None)

        if emp_id and plan and str(plan.empresa_id) != str(emp_id):
            raise ValidationError("El plan no pertenece a tu empresa.")
        if plan and servicio and plan.empresa_id != servicio.empresa_id:
            raise ValidationError("El servicio y el plan deben pertenecer a la misma empresa.")

        serializer.save(updated_by=self.request.user)

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
