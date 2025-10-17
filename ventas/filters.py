# filters.py
import django_filters
from django_filters import rest_framework as filters
from .models import Venta

class VentaFilter(filters.FilterSet):
    fecha   = filters.DateTimeFromToRangeFilter()
    empresa = filters.NumberFilter(field_name="empresa_id")
    cliente = filters.NumberFilter(field_name="cliente_id")
    # nuevo: filtrar por forma de pago (relación reverse a MetodoPago)
    forma_pago = filters.CharFilter(field_name="pagos__forma_pago", lookup_expr="iexact")

    class Meta:
        model  = Venta
        fields = ["empresa", "cliente", "fecha", "forma_pago"]
