from decimal import Decimal
from rest_framework import viewsets, permissions, decorators, response, status
from core.permissions import IsAuthenticatedInCompany
from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateTimeFromToRangeFilter, NumberFilter
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import CodigoDescuento, Venta, DetalleVenta
from .serializers import CodigoDescuentoSerializer, VentaSerializer, DetalleVentaSerializer

class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class CodigoDescuentoViewSet(viewsets.ModelViewSet):
    queryset = CodigoDescuento.objects.select_related("empresa", "usuario").all().order_by("-id")
    serializer_class = CodigoDescuentoSerializer
    permission_classes = [IsAuthenticatedInCompany]

    # Filtra por las empresas del usuario
    def get_queryset(self):
        empresas_usuario = self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True)
        qs = super().get_queryset().filter(empresa_id__in=empresas_usuario)
        # filtros opcionales por query param
        empresa = self.request.query_params.get("empresa")
        codigo = self.request.query_params.get("codigo")
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        if codigo:
            qs = qs.filter(codigo__iexact=codigo.strip().upper())
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @decorators.action(detail=False, methods=["get"], url_path="validar")
    def validar(self, request):
        """
        GET /api/v1/ventas/codigos-descuento/validar/?empresa=<id>&codigo=<ABC>&total=<monto>
        Responde si es usable y cómo quedaría el total.
        """
        empresa_id = request.query_params.get("empresa")
        codigo = request.query_params.get("codigo", "").strip().upper()
        total = request.query_params.get("total")

        if not empresa_id or not codigo:
            return response.Response(
                {"detail": "Parámetros requeridos: empresa, codigo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cd = self.get_queryset().get(empresa_id=empresa_id, codigo=codigo, is_active=True)
        except CodigoDescuento.DoesNotExist:
            return response.Response({"valid": False, "reason": "No existe o no pertenece a tu empresa."}, status=200)

        if cd.restantes <= 0:
            return response.Response({"valid": False, "reason": "Sin usos restantes."}, status=200)

        data = {"valid": True, "codigo": cd.codigo, "tipo": cd.tipo_descuento, "descuento": str(cd.descuento)}
        if total is not None:
            try:
                total_dec = Decimal(total)
                if total_dec < 0:
                    raise ValueError()
            except Exception:
                return response.Response({"detail": "total inválido."}, status=400)

            if cd.tipo_descuento == CodigoDescuento.Tipo.PORCENTAJE:
                rebaja = (total_dec * cd.descuento) / Decimal("100")
            else:
                rebaja = cd.descuento

            nuevo_total = total_dec - rebaja
            if nuevo_total < 0:
                nuevo_total = Decimal("0.00")

            data.update({
                "total_original": str(total_dec),
                "rebaja": str(rebaja.quantize(Decimal('0.01'))),
                "total_final": str(nuevo_total.quantize(Decimal('0.01'))),
            })
        return response.Response(data, status=200)

    @decorators.action(detail=True, methods=["post"], url_path="canjear")
    def canjear(self, request, pk=None):
        """
        POST /api/v1/ventas/codigos-descuento/{id}/canjear/
        Disminuye 'restantes' en 1 si es usable. (Transacción simple.)
        """
        cd = self.get_object()
        if not cd.is_active or cd.restantes <= 0:
            return response.Response({"ok": False, "detail": "Código no usable."}, status=400)
        cd.restantes = cd.restantes - 1
        cd.updated_by = request.user
        cd.save(update_fields=["restantes", "updated_by", "updated_at"])
        return response.Response({"ok": True, "restantes": cd.restantes}, status=200)


class VentaFilter(FilterSet):
    fecha = DateTimeFromToRangeFilter()
    empresa = NumberFilter(field_name="empresa_id")
    cliente = NumberFilter(field_name="cliente_id")
    class Meta:
        model = Venta
        fields = ["empresa", "cliente", "fecha", "metodo_pago"]

class VentaViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = (Venta.objects
                .select_related("empresa", "cliente")
                .prefetch_related("detalles")
                .all())
    serializer_class = VentaSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VentaFilter
    ordering_fields = ["id", "fecha", "importe"]
    ordering = ["-fecha"]

class DetalleVentaViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    """
    Nota: si tu CompanyScopedQuerysetMixin filtra por request.company,
    asegúrate que Venta->empresa esté alineado.
    """
    permission_classes = [IsAuthenticatedInCompany]
    queryset = (DetalleVenta.objects
                .select_related("venta", "plan", "producto", "codigo_descuento")
                .all())
    serializer_class = DetalleVentaSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["venta", "producto", "plan", "codigo_descuento"]
    ordering_fields = ["id", "importe", "cantidad"]
    ordering = ["-id"]