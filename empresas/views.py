from django.db import transaction
from rest_framework import viewsets, permissions, decorators, response, status
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
    queryset = (ValorConfiguracion.objects
                .select_related("empresa", "configuracion")
                .all().order_by("id"))
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
        qs = self.filter_queryset(self.get_queryset()).filter(empresa_id=empresa_id, is_active=True)
        data = {}
        for vc in qs:
            key = vc.configuracion.nombre
            tipo = (vc.configuracion.tipo_dato or "").strip().lower()
            val = vc.valor
            try:
                if tipo in ("int","integer"):
                    data[key] = int(val)
                elif tipo in ("decimal","float","number"):
                    data[key] = float(val)
                elif tipo in ("bool","boolean"):
                    data[key] = str(val).lower() in ("true","1","yes","si")
                elif tipo == "json":
                    import json
                    data[key] = json.loads(val)
                else:
                    data[key] = val
            except Exception:
                data[key] = val
        return response.Response(data)

    # ---- NUEVO: guardar/actualizar una clave ----
    @decorators.action(detail=False, methods=["post"], url_path="upsert")
    @transaction.atomic
    def upsert(self, request):
        """
        body: { empresa: ID, nombre: 'ui.app_name', valor: 'Mi App' }
        Crea Configuracion si no existe, y hace upsert del ValorConfiguracion.
        """
        empresa_id = request.data.get("empresa")
        nombre     = request.data.get("nombre")
        valor      = request.data.get("valor", "")

        if not empresa_id or not nombre:
            return response.Response(
                {"detail": "empresa y nombre son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Inferencia simple de tipo_dato por nombre
        defaults_map = {
            "ui.nav":              ("json", "JSON con el menú del sidebar"),
            "ui.app_name":         ("text", "Nombre visible de la app"),
            "ui.logo_url":         ("text", "URL del logo"),
            "ui.primary":          ("text", "Color primario (hex)"),
            "ui.secondary":        ("text", "Color secundario (hex)"),
            "ui.dashboard.widgets":("json", "Listado de widgets del dashboard"),
        }
        tipo, desc = defaults_map.get(nombre, ("text", nombre))

        cfg, _ = Configuracion.objects.get_or_create(
            nombre=nombre,
            defaults={"tipo_dato": tipo, "descripcion": desc}
        )

        vc, _created = ValorConfiguracion.objects.update_or_create(
            empresa_id=empresa_id,
            configuracion=cfg,
            defaults={
                "valor": str(valor),
                "updated_by": request.user,
                "created_by": request.user,
                "is_active": True,
            },
        )
        ser = self.get_serializer(vc)
        return response.Response(ser.data, status=status.HTTP_200_OK)

    # ---- NUEVO: guardar varias de una sola vez ----
    @decorators.action(detail=False, methods=["post"], url_path="upsert-many")
    @transaction.atomic
    def upsert_many(self, request):
        """
        body: { empresa: ID, pares: [{nombre:'ui.app_name', valor:'X'}, ...] }
        """
        empresa_id = request.data.get("empresa")
        pares = request.data.get("pares", [])
        if not empresa_id or not isinstance(pares, list):
            return response.Response({"detail": "empresa y pares[] requeridos"},
                                     status=status.HTTP_400_BAD_REQUEST)

        results = []
        for p in pares:
            nombre = p.get("nombre")
            valor  = p.get("valor", "")
            if not nombre:
                continue
            # mismos defaults del upsert normal
            defaults_map = {
                "ui.nav":              ("json", "JSON con el menú del sidebar"),
                "ui.app_name":         ("text", "Nombre visible de la app"),
                "ui.logo_url":         ("text", "URL del logo"),
                "ui.primary":          ("text", "Color primario (hex)"),
                "ui.secondary":        ("text", "Color secundario (hex)"),
                "ui.dashboard.widgets":("json", "Listado de widgets del dashboard"),
            }
            tipo, desc = defaults_map.get(nombre, ("text", nombre))
            cfg, _ = Configuracion.objects.get_or_create(
                nombre=nombre, defaults={"tipo_dato": tipo, "descripcion": desc}
            )
            vc, _ = ValorConfiguracion.objects.update_or_create(
                empresa_id=empresa_id, configuracion=cfg,
                defaults={
                    "valor": str(valor),
                    "updated_by": request.user,
                    "created_by": request.user,
                    "is_active": True,
                },
            )
            results.append(self.get_serializer(vc).data)

        return response.Response(results, status=status.HTTP_200_OK)