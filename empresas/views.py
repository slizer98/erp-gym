from rest_framework import viewsets, permissions, decorators, response
from .models import Empresa, Sucursal, Configuracion, ValorConfiguracion
from .serializers import EmpresaSerializer, SucursalSerializer, ConfiguracionSerializer, ValorConfiguracionSerializer
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
class IsAuth(permissions.IsAuthenticated):
    pass

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all().order_by("id")
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuth]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class SucursalViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sucursal.objects.select_related("empresa").all().order_by("id")
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticatedInCompany]
    permission_classes = [IsAuth]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ConfiguracionViewSet(viewsets.ModelViewSet):
    """
    CRUD del catálogo de configuraciones (global).
    Puedes restringir a superusuarios si quieres.
    """
    queryset = Configuracion.objects.all().order_by("id")
    serializer_class = ConfiguracionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ("nombre", "tipo_dato")
    ordering_fields = ("id", "nombre")
    ordering = ("id",)


class ValorConfiguracionViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    CRUD de valores por empresa (scoped).
    """
    queryset = ValorConfiguracion.objects.select_related("empresa", "configuracion").all().order_by("id")
    serializer_class = ValorConfiguracionSerializer
    permission_classes = [IsAuthenticatedInCompany]
    search_fields = ("configuracion__nombre", "empresa__nombre", "valor")
    ordering_fields = ("id", "updated_at")
    ordering = ("-updated_at",)
    company_fk_name = "empresa"

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @decorators.action(detail=False, methods=["get"], url_path="por-empresa/(?P<empresa_id>[^/.]+)")
    def por_empresa(self, request, empresa_id=None):
        """
        Devuelve un diccionario {nombre_config: valor_parseado} para la empresa.
        """
        qs = self.filter_queryset(self.get_queryset()).filter(empresa_id=empresa_id, is_active=True)
        data = {}
        for vc in qs:
            key = vc.configuracion.nombre
            tipo = (vc.configuracion.tipo_dato or "").strip().lower()
            val = vc.valor
            # parseo ligero para entregar typed
            try:
                if tipo in ("int", "integer"):
                    data[key] = int(val)
                elif tipo in ("decimal", "float", "number"):
                    data[key] = float(val)
                elif tipo in ("bool", "boolean"):
                    data[key] = str(val).lower() in ("true", "1", "yes", "si")
                elif tipo in ("json",):
                    import json
                    data[key] = json.loads(val)
                else:
                    data[key] = val
            except Exception:
                data[key] = val
        return response.Response(data)