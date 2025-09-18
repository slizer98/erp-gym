from decimal import Decimal
from rest_framework import viewsets, permissions, decorators, response, status
from core.permissions import IsAuthenticatedInCompany
from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, DateTimeFromToRangeFilter, NumberFilter
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Case, When, IntegerField, F
from .models import CodigoDescuento, Venta, DetalleVenta
from inventario.models import MovimientoProducto, Producto, Almacen
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
    @decorators.action(detail=False, methods=["post"], url_path="pos-checkout")
    def pos_checkout(self, request):
        """
        Cierra una venta en UNA transacción:
        - Crea Venta y Detalles
        - Genera movimientos de inventario (SALIDA)
        - Aplica y canjea código de descuento (opcional)

        Payload esperado (ejemplo):
        {
          "empresa": 1,
          "cliente": 123,                 # id de usuario/cliente
          "metodo_pago": "efectivo",      # efectivo/tarjeta/transferencia/mixto
          "almacen": 5,                   # almacén desde donde salen productos
          "codigo_descuento": "ABC10",    # opcional
          "items": [
            {"producto": 10, "plan": null, "cantidad": 2, "precio_unit": "199.00"},
            {"producto": null, "plan": 3,  "cantidad": 1, "precio_unit": "499.00"}
          ],
          "fecha": null                    # opcional (server now)
        }
        """
        data = request.data
        empresa_id = data.get("empresa")
        cliente_id = data.get("cliente")
        metodo_pago = data.get("metodo_pago")
        almacen_id = data.get("almacen")
        codigo_str = (data.get("codigo_descuento") or "").strip().upper()
        items = data.get("items") or []
        fecha = data.get("fecha")

        if not empresa_id or not cliente_id or not metodo_pago or not items:
            return response.Response({"detail": "Faltan campos obligatorios (empresa, cliente, metodo_pago, items)."}, status=400)

        try:
            almacen = Almacen.objects.get(pk=almacen_id, empresa_id=empresa_id) if almacen_id else None
        except Almacen.DoesNotExist:
            return response.Response({"detail": "Almacén inválido."}, status=400)

        # Totales
        subtotal = Decimal("0.00")
        for it in items:
            try:
                qty = int(it.get("cantidad", 0))
                pu  = Decimal(str(it.get("precio_unit", "0")))
            except Exception:
                return response.Response({"detail": "cantidad/precio_unit inválidos."}, status=400)
            if qty <= 0 or pu < 0:
                return response.Response({"detail": "Cantidad o precio inválidos."}, status=400)
            subtotal += pu * qty

        descuento_aplicado = Decimal("0.00")
        cd = None
        if codigo_str:
            try:
                cd = CodigoDescuento.objects.select_for_update().get(empresa_id=empresa_id, codigo=codigo_str, is_active=True)
            except CodigoDescuento.DoesNotExist:
                return response.Response({"detail": "Código de descuento inválido."}, status=400)
            if cd.restantes <= 0:
                return response.Response({"detail": "El código no tiene usos disponibles."}, status=400)

            if cd.tipo_descuento == CodigoDescuento.Tipo.PORCENTAJE:
                descuento_aplicado = (subtotal * cd.descuento) / Decimal("100")
            else:
                descuento_aplicado = cd.descuento

            if descuento_aplicado > subtotal:
                descuento_aplicado = subtotal

        total = (subtotal - descuento_aplicado).quantize(Decimal('0.01'))
        if total < 0:
            total = Decimal("0.00")

        now = timezone.now()
        fecha = fecha or now

        # Validación de stock y creación atómica
        with transaction.atomic():
            # Validar stock de productos y preparar líneas
            for it in items:
                prod_id = it.get("producto")
                qty = int(it.get("cantidad", 0))
                if prod_id and almacen:
                    # stock = entradas - salidas + ajustes
                    stock = MovimientoProducto.objects.filter(
                        empresa_id=empresa_id,
                        producto_id=prod_id,
                        almacen_id=almacen.id,
                    ).aggregate(
                        s=Sum(
                            Case(
                                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.ENTRADA, then='cantidad'),
                                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.SALIDA,  then=-1*F('cantidad')),
                                When(tipo_movimiento=MovimientoProducto.TipoMovimiento.AJUSTE,  then='cantidad'),
                                default=0,
                                output_field=IntegerField(),
                            )
                        )
                    )["s"] or 0
                    if stock < qty:
                        return response.Response({"detail": f"Stock insuficiente para producto {prod_id} en almacén {almacen.id}. Disponible: {stock}, requerido: {qty}"}, status=400)

            # Crear venta
            venta = Venta.objects.create(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                fecha=fecha,
                importe=total,
                metodo_pago=metodo_pago,
                created_by=request.user,
                updated_by=request.user,
            )

            # Crear detalles y movimientos
            detalles_out = []
            for it in items:
                prod_id = it.get("producto")
                plan_id = it.get("plan")
                qty = int(it.get("cantidad", 0))
                pu  = Decimal(str(it.get("precio_unit", "0")))
                det = DetalleVenta.objects.create(
                    venta=venta,
                    producto_id=prod_id or None,
                    plan_id=plan_id or None,
                    cantidad=qty,
                    importe=(pu * qty).quantize(Decimal('0.01')),
                    created_by=request.user,
                    updated_by=request.user,
                )
                detalles_out.append(det.id)

                # Movimiento de inventario (solo productos)
                if prod_id and almacen:
                    MovimientoProducto.objects.create(
                        empresa_id=empresa_id,
                        producto_id=prod_id,
                        almacen_id=almacen.id,
                        tipo_movimiento=MovimientoProducto.TipoMovimiento.SALIDA,
                        cantidad=qty,
                        fecha=fecha,
                        created_by=request.user,
                        updated_by=request.user,
                    )

            # Canjear descuento (si procede)
            if cd:
                cd.restantes = cd.restantes - 1
                cd.updated_by = request.user
                cd.save(update_fields=["restantes", "updated_by", "updated_at"])

        return response.Response({
            "ok": True,
            "venta_id": venta.id,
            "importe": str(venta.importe),
            "detalles": detalles_out,
            "subtotal": str(subtotal.quantize(Decimal('0.01'))),
            "descuento": str(descuento_aplicado.quantize(Decimal('0.01'))),
            "total": str(total),
        }, status=status.HTTP_201_CREATED)

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