from rest_framework import viewsets, permissions
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import Plan, PrecioPlan, RestriccionPlan
from .serializers import PlanSerializer, PrecioPlanSerializer, RestriccionPlanSerializer

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
