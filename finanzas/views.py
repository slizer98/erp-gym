from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateTimeFromToRangeFilter, NumberFilter
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from .models import Proveedor, CategoriaEgreso, Egreso
from .serializers import ProveedorSerializer, CategoriaEgresoSerializer, EgresoSerializer

class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class ProveedorViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Proveedor.objects.select_related("empresa").all()
    serializer_class = ProveedorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "correo", "telefono"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["nombre"]
    filterset_fields = ["empresa"]

class CategoriaEgresoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = CategoriaEgreso.objects.select_related("empresa").all()
    serializer_class = CategoriaEgresoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre"]
    ordering_fields = ["id", "nombre", "created_at"]
    ordering = ["nombre"]
    filterset_fields = ["empresa"]

class EgresoFilter(FilterSet):
    fecha = DateTimeFromToRangeFilter()
    empresa = NumberFilter(field_name="empresa_id")
    proveedor = NumberFilter(field_name="proveedor_id")
    categoria = NumberFilter(field_name="categoria_id")
    class Meta:
        model = Egreso
        fields = ["empresa", "proveedor", "categoria", "fecha", "forma_pago", "sucursal"]

class EgresoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = (Egreso.objects
                .select_related("empresa", "proveedor", "categoria")
                .all())
    serializer_class = EgresoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EgresoFilter
    search_fields = ["concepto", "descripcion", "sucursal"]
    ordering_fields = ["id", "fecha", "total", "created_at"]
    ordering = ["-fecha"]
