# filters.py
import django_filters
from django_filters import rest_framework as filters
from .models import Venta, DetalleVenta

class VentaFilter(filters.FilterSet):
    fecha   = filters.DateTimeFromToRangeFilter()
    empresa = filters.NumberFilter(field_name="empresa_id")
    cliente = filters.NumberFilter(field_name="cliente_id")
    # nuevo: filtrar por forma de pago (relación reverse a MetodoPago)
    forma_pago = filters.CharFilter(field_name="pagos__forma_pago", lookup_expr="iexact")
    item_tipo = filters.CharFilter(field_name="detalles__item_tipo", lookup_expr="iexact")

    class Meta:
        model  = Venta
        fields = ["empresa", "cliente", "fecha", "forma_pago", "item_tipo"]
        
class DetalleVentaFilter(filters.FilterSet):
    item_tipo = filters.CharFilter(field_name="item_tipo", lookup_expr="iexact")

    class Meta:
        model  = DetalleVenta
        fields = ["venta", "producto", "plan", "codigo_descuento", "item_tipo"]