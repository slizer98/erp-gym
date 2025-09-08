from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateTimeFromToRangeFilter, NumberFilter
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import Almacen, CategoriaProducto, Producto, MovimientoProducto
from .serializers import (
    AlmacenSerializer, CategoriaProductoSerializer, ProductoSerializer, MovimientoProductoSerializer
)

# Si ya tienes BaseAuthViewSet úsalo; si no:
class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class AlmacenViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Almacen.objects.select_related("empresa").all()
    serializer_class = AlmacenSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["-id"]
    filterset_fields = ["empresa"]

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
