from rest_framework import viewsets, permissions
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import (Plan, PrecioPlan, RestriccionPlan, Servicio, Beneficio, 
                     PlanServicio, PlanBeneficio, Disciplina, DisciplinaPlan, HorarioDisciplina,
                     AltaPlan, Acceso)
from .serializers import (PlanSerializer, PrecioPlanSerializer, RestriccionPlanSerializer, ServicioSerializer, BeneficioSerializer, PlanServicioSerializer, PlanBeneficioSerializer,
    DisciplinaSerializer, DisciplinaPlanSerializer, HorarioDisciplinaSerializer,
    AltaPlanSerializer, AccesoSerializer)

class PlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Plan.objects.select_related("empresa", "usuario").all().order_by("-id")
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"

    search_fields = ("nombre", "tipo_plan", "descripcion")
    ordering_fields = ("id", "nombre", "desde", "hasta", "updated_at")
    ordering = ("-updated_at",)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


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

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RestriccionPlanViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (RestriccionPlan.objects
                .select_related("plan", "plan__empresa", "usuario")
                .all().order_by("-id"))
    serializer_class = RestriccionPlanSerializer
    permission_classes = [IsAuthenticatedInCompany]

    def get_queryset(self):
        qs = super().get_queryset()
        empresas_usuario = self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True)
        return qs.filter(plan__empresa_id__in=empresas_usuario)

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
    queryset = Servicio.objects.select_related("empresa").all().order_by("id")
    serializer_class = ServicioSerializer

class BeneficioViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    company_fk_name = "empresa"
    queryset = Beneficio.objects.select_related("empresa").all().order_by("id")
    serializer_class = BeneficioSerializer

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