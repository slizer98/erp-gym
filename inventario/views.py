# inventario/views.py
from rest_framework import viewsets, filters, permissions, decorators, response, status
from django.db.models import Sum, Case, When, IntegerField, F
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateTimeFromToRangeFilter, NumberFilter
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import Almacen, CategoriaProducto, Producto, MovimientoProducto
from .serializers import (
    AlmacenSerializer, CategoriaProductoSerializer, ProductoSerializer, MovimientoProductoSerializer
)

# Si ya tienes BaseAuthViewSet en otro módulo, usa ese.
class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AlmacenViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Almacen.objects.select_related("empresa", "sucursal").all()
    serializer_class = AlmacenSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["-id"]
    filterset_fields = ["empresa", "sucursal", "is_active"]

    # opcional: si tu mixin no fuerza empresa, aquí puedes hacerlo
    def perform_create(self, serializer):
        obj = serializer.save()
        # Ya validado en serializer: sucursal.empresa == empresa
        return obj

    def perform_update(self, serializer):
        obj = serializer.save()
        return obj


class CategoriaProductoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = CategoriaProducto.objects.select_related("empresa").all()
    serializer_class = CategoriaProductoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["nombre"]
    filterset_fields = ["empresa"]


class ProductoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Producto.objects.select_related("empresa", "categoria").all()
    serializer_class = ProductoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion", "codigo_barras", "categoria__nombre"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["-id"]
    filterset_fields = ["empresa", "categoria"]

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Crea el Producto y, si vienen campos de stock inicial, genera un Movimiento ENTRADA.
        Espera en request.data:
          - stock_inicial: int (>0 para crear ENTRADA)
          - almacen: id del almacén
          - fecha_entrada (opcional, ISO8601)
        """
        producto = serializer.save(created_by=self.request.user, updated_by=self.request.user)

        data = self.request.data
        try:
            stock_inicial = int(data.get('stock_inicial') or 0)
        except (TypeError, ValueError):
            stock_inicial = 0

        if stock_inicial <= 0:
            return  # no hay stock inicial → sin movimiento

        almacen_id = data.get('almacen')
        if not almacen_id:
            raise ValueError("Para capturar stock_inicial debes especificar 'almacen'.")

        fecha_dt = parse_datetime(data.get('fecha_entrada')) if data.get('fecha_entrada') else timezone.now()

        MovimientoProducto.objects.create(
            empresa_id=producto.empresa_id,
            producto_id=producto.id,
            almacen_id=int(almacen_id),
            tipo_movimiento=MovimientoProducto.TipoMovimiento.ENTRADA,
            cantidad=stock_inicial,
            fecha=fecha_dt,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @decorators.action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        """
        Retorna stock actual del producto.
        - Opcional: ?almacen=<id> para stock en ese almacén.
        - Si no se pasa almacen, devuelve total y desglose por almacén.
        """
        producto_id = pk
        empresa_id = getattr(request, 'company_id', None) or request.query_params.get('empresa')
        almacen_id = request.query_params.get('almacen')

        base = MovimientoProducto.objects.filter(producto_id=producto_id)
        if empresa_id:
            base = base.filter(empresa_id=empresa_id)

        agg_expr = Sum(
            Case(
                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.ENTRADA, then=F('cantidad')),
                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.SALIDA,  then=-1 * F('cantidad')),
                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.AJUSTE,  then=F('cantidad')),
                default=0,
                output_field=IntegerField(),
            )
        )

        if almacen_id:
            stock = base.filter(almacen_id=almacen_id).aggregate(s=agg_expr).get('s') or 0
            return response.Response({"producto": int(producto_id), "almacen": int(almacen_id), "stock": int(stock)})

        por_almacen = (
            base.values('almacen_id', 'almacen__nombre')
                .annotate(stock=agg_expr)
                .order_by('almacen__nombre')
        )
        total = sum((row['stock'] or 0) for row in por_almacen)
        return response.Response({
            "producto": int(producto_id),
            "total": int(total),
            "por_almacen": [
                {"almacen": r['almacen_id'], "nombre": r['almacen__nombre'], "stock": int(r['stock'] or 0)}
                for r in por_almacen
            ]
        })


class MovimientoProductoFilter(FilterSet):
    fecha = DateTimeFromToRangeFilter()  # ?fecha_after=...&fecha_before=...
    producto = NumberFilter(field_name="producto_id")
    almacen = NumberFilter(field_name="almacen_id")
    empresa = NumberFilter(field_name="empresa_id")
    class Meta:
        model = MovimientoProducto
        fields = ["empresa", "producto", "almacen", "tipo_movimiento", "fecha"]


class MovimientoProductoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = (MovimientoProducto.objects
                .select_related("empresa", "producto", "almacen")
                .all())
    serializer_class = MovimientoProductoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MovimientoProductoFilter
    ordering_fields = ["id", "fecha", "cantidad"]
    ordering = ["-fecha"]

    @decorators.action(detail=False, methods=["post"], url_path="entrada")
    @transaction.atomic
    def entrada(self, request):
        """
        Crea un Movimiento ENTRADA (para compras/ingresos).
        Body: { empresa, producto, almacen, cantidad, fecha? }
        """
        empresa = request.data.get("empresa")
        producto = request.data.get("producto")
        almacen = request.data.get("almacen")
        cantidad = request.data.get("cantidad")
        fecha = request.data.get("fecha")

        if not all([empresa, producto, almacen, cantidad]):
            return response.Response(
                {"detail": "empresa, producto, almacen y cantidad son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            return response.Response({"detail": "cantidad inválida."}, status=status.HTTP_400_BAD_REQUEST)
        if cantidad <= 0:
            return response.Response({"detail": "cantidad debe ser > 0."}, status=status.HTTP_400_BAD_REQUEST)

        fecha_dt = parse_datetime(fecha) if fecha else timezone.now()

        mov = MovimientoProducto.objects.create(
            empresa_id=int(empresa),
            producto_id=int(producto),
            almacen_id=int(almacen),
            tipo_movimiento=MovimientoProducto.TipoMovimiento.ENTRADA,
            cantidad=cantidad,
            fecha=fecha_dt,
            created_by=request.user,
            updated_by=request.user,
        )
        return response.Response(MovimientoProductoSerializer(mov).data, status=status.HTTP_201_CREATED)
