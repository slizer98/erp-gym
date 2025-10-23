# views.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Case, When, IntegerField, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework import filters as drf_filters
from rest_framework.pagination import PageNumberPagination
from core.mixins import CompanyScopedQuerysetMixin
from core.permissions import IsAuthenticatedInCompany

from .models import CodigoDescuento, Venta, DetalleVenta, MetodoPago
from inventario.models import MovimientoProducto, Almacen
from .serializers import (
    CodigoDescuentoSerializer,
    MetodoPagoSerializer,
    DetalleVentaSerializer,
    # Usa los dos serializers de ventas (list/detail)
    VentaListSerializer,
    VentaDetailSerializer,
)
from .filters import VentaFilter

class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000


class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CodigoDescuentoViewSet(BaseAuthViewSet):
    queryset = (
        CodigoDescuento.objects
        .select_related("empresa", "usuario")
        .all()
        .order_by("-id")
    )
    serializer_class = CodigoDescuentoSerializer
    permission_classes = [IsAuthenticatedInCompany]

    def get_queryset(self):
        # Limitar por empresas asignadas al usuario
        empresas_usuario = self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True)
        qs = super().get_queryset().filter(empresa_id__in=empresas_usuario)

        # Filtros opcionales
        empresa = self.request.query_params.get("empresa")
        codigo = (self.request.query_params.get("codigo") or "").strip()
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        if codigo:
            qs = qs.filter(codigo__iexact=codigo.upper())
        return qs

    @decorators.action(detail=False, methods=["get"], url_path="validar")
    def validar(self, request):
        """
        GET /api/v1/ventas/codigos-descuento/validar/?empresa=<id>&codigo=<ABC>&total=<monto>
        """
        empresa_id = request.query_params.get("empresa")
        codigo = (request.query_params.get("codigo") or "").strip().upper()
        total = request.query_params.get("total")

        if not empresa_id or not codigo:
            return response.Response(
                {"detail": "Parámetros requeridos: empresa, codigo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cd = self.get_queryset().get(empresa_id=empresa_id, codigo=codigo, is_active=True)
        except CodigoDescuento.DoesNotExist:
            return response.Response(
                {"valid": False, "reason": "No existe o no pertenece a tu empresa."}, status=200
            )

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
        """
        cd = self.get_object()
        if not cd.is_active or cd.restantes <= 0:
            return response.Response({"ok": False, "detail": "Código no usable."}, status=400)
        cd.restantes = cd.restantes - 1
        cd.updated_by = request.user
        cd.save(update_fields=["restantes", "updated_by", "updated_at"])
        return response.Response({"ok": True, "restantes": cd.restantes}, status=200)


class VentaViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    - list: 2 etapas -> (1) IDs ya filtrados y ordenados, limit 1000; (2) fetch con annotate(total_pagado).
      Evita escanear tablas completas y duplicados por joins (pagos/detalles).
    - retrieve: serializer completo con prefetch de detalles/pagos.
    """
    permission_classes = [IsAuthenticatedInCompany]
    filter_backends   = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class   = VentaFilter
    ordering_fields   = ["id", "fecha", "importe", "total"]
    ordering          = ["-fecha"]
    pagination_class  = DefaultPagination

    def get_serializer_class(self):
        return VentaListSerializer if self.action == "list" else VentaDetailSerializer

    # QS ligero para list (sin annotate/prefetch). Deja que el filterset trabaje rápido.
    def base_queryset(self):
        return (
            Venta.objects
            .select_related("empresa", "cliente")
            .only(
                "id", "folio", "fecha", "empresa", "cliente",
                "subtotal", "descuento_monto", "impuesto_monto",
                "total", "importe", "tipo_venta"
            )
        )

    # QS para retrieve con relaciones
    def detail_queryset(self):
        return (
            Venta.objects
            .select_related("empresa", "cliente", "sucursal", "usuario")
            .prefetch_related("detalles", "pagos")
        )

    def get_queryset(self):
        # DRF usará este queryset también para retrieve
        if self.action == "retrieve":
            return self.detail_queryset()
        return self.base_queryset()

    def list(self, request, *args, **kwargs):
        """
        1) Aplica filtros/ordering sobre queryset ligero (sin annotate).
        2) Evita duplicados si vienen filtros many-to-one (forma_pago, item_tipo).
        3) Toma solo los 1000 IDs más recientes.
        4) Reconsulta esas ventas con annotate(total_pagado) y responde (paginado).
        """
        # 1) filtros (DjangoFilterBackend + OrderingFilter)
        qs_light = self.filter_queryset(self.base_queryset())

        # 2) ordering por defecto estable si no envían ?ordering=
        if not request.query_params.get("ordering"):
            qs_light = qs_light.order_by("-fecha", "-id")

        # Evitar duplicados si se filtra por relaciones many (pagos/detalles)
        if "forma_pago" in request.query_params or "item_tipo" in request.query_params:
            qs_light = qs_light.distinct()

        # 3) limitar a 1000 IDs ya filtrados/ordenados
        ids_subquery = qs_light.values_list("id", flat=True)[:1000]

        # 4) fetch final de esas ventas + annotate
        qs = (
            Venta.objects.filter(id__in=ids_subquery)
            .select_related("empresa", "cliente")
            .only(
                "id", "folio", "fecha", "empresa", "cliente",
                "subtotal", "descuento_monto", "impuesto_monto",
                "total", "importe", "tipo_venta"
            )
            .annotate( total_pagado=Coalesce(
            Sum("pagos__importe"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ))
            .order_by("-fecha", "-id")
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return response.Response(ser.data)

    @decorators.action(detail=False, methods=["post"], url_path="pos-checkout")
    def pos_checkout(self, request):
        """
        Cierra una venta con múltiples pagos.
        Payload esperado:
        {
          "empresa": 1,
          "cliente": 123,
          "almacen": 5,                 # opcional si hay productos
          "codigo_descuento": "ABC10",  # opcional
          "items": [
            {"producto": 10, "plan": null, "cantidad": 2, "precio_unit": "199.00"},
            {"producto": null, "plan": 3,  "cantidad": 1, "precio_unit": "499.00"}
          ],
          "pagos": [
            {"forma_pago": "efectivo", "importe": "300.00"},
            {"forma_pago": "tarjeta",  "importe": "597.00"}
          ],
          "fecha": null
        }
        """
        data        = request.data
        empresa_id  = data.get("empresa")
        cliente_id  = data.get("cliente")
        almacen_id  = data.get("almacen")
        codigo_str  = (data.get("codigo_descuento") or "").strip().upper()
        items       = data.get("items") or []
        pagos_in    = data.get("pagos") or []
        fecha       = data.get("fecha") or timezone.now()

        if not empresa_id or not cliente_id or not items:
            return response.Response({"detail": "Faltan campos obligatorios (empresa, cliente, items)."}, status=400)

        try:
            almacen = Almacen.objects.get(pk=almacen_id, empresa_id=empresa_id) if almacen_id else None
        except Almacen.DoesNotExist:
            return response.Response({"detail": "Almacén inválido."}, status=400)

        # Subtotal
        subtotal = Decimal("0.00")
        for it in items:
            try:
                qty = int(it.get("cantidad", 0))
                pu  = Decimal(str(it.get("precio_unit", "0")))
            except Exception:
                return response.Response({"detail": "cantidad/precio_unit inválidos."}, status=400)
            if qty <= 0 or pu < 0:
                return response.Response({"detail": "Cantidad o precio inválidos."}, status=400)
            subtotal += (pu * qty)

        # Descuento
        descuento_aplicado = Decimal("0.00")
        cd = None
        if codigo_str:
            try:
                cd = CodigoDescuento.objects.select_for_update().get(
                    empresa_id=empresa_id, codigo=codigo_str, is_active=True
                )
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

        total = (subtotal - descuento_aplicado).quantize(Decimal("0.01"))
        if total < 0:
            total = Decimal("0.00")

        # Validar pagos
        total_pagos = Decimal("0.00")
        for p in pagos_in:
            try:
                imp = Decimal(str(p.get("importe", "0")))
                if imp <= 0:
                    return response.Response({"detail": "Importe de pago debe ser > 0."}, status=400)
                total_pagos += imp
            except Exception:
                return response.Response({"detail": "Importe de pago inválido."}, status=400)

        # Exigir cobertura exacta (opcional)
        if pagos_in and total_pagos != total:
            return response.Response(
                {"detail": f"La suma de pagos ({total_pagos}) debe ser igual al total ({total})."},
                status=400
            )

        # Stock
        for it in items:
            prod_id = it.get("producto")
            qty     = int(it.get("cantidad", 0))
            if prod_id and almacen:
                stock = MovimientoProducto.objects.filter(
                    empresa_id=empresa_id,
                    producto_id=prod_id,
                    almacen_id=almacen.id,
                ).aggregate(
                    s=Sum(
                        Case(
                            When(tipo_movimiento=MovimientoProducto.TipoMovimiento.ENTRADA, then='cantidad'),
                            When(tipo_movimiento=MovimientoProducto.TipoMovimiento.SALIDA,  then=-1 * F('cantidad')),
                            When(tipo_movimiento=MovimientoProducto.TipoMovimiento.AJUSTE,  then='cantidad'),
                            default=0,
                            output_field=IntegerField(),
                        )
                    )
                )["s"] or 0
                if stock < qty:
                    return response.Response(
                        {"detail": f"Stock insuficiente para producto {prod_id}. Disponible: {stock}, requerido: {qty}"},
                        status=400
                    )

        # Transacción
        with transaction.atomic():
            venta = Venta.objects.create(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                fecha=fecha,
                importe=total,
                subtotal=subtotal,
                descuento_monto=descuento_aplicado,
                total=total,
                created_by=request.user,
                updated_by=request.user,
            )

            # Detalles + movimientos
            detalles_out = []
            for it in items:
                prod_id = it.get("producto")
                plan_id = it.get("plan")
                qty     = int(it.get("cantidad", 0))
                pu      = Decimal(str(it.get("precio_unit", "0")))

                line_subtotal = (pu * qty).quantize(Decimal('0.01'))
                det = DetalleVenta.objects.create(
                    venta=venta,
                    producto_id=prod_id or None,
                    plan_id=plan_id or None,
                    cantidad=qty,
                    precio_unitario=pu,
                    descuento_monto=Decimal('0.00'),
                    impuesto_pct=Decimal('0.00'),
                    impuesto_monto=Decimal('0.00'),
                    subtotal=line_subtotal,
                    total=line_subtotal,
                    created_by=request.user,
                    updated_by=request.user,
                )
                detalles_out.append(det.id)

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

            # Pagos
            pagos_out = []
            for p in pagos_in:
                mp = MetodoPago.objects.create(
                    venta=venta,
                    forma_pago=(p.get("forma_pago") or "").strip().lower(),
                    importe=Decimal(str(p.get("importe"))),
                    created_by=request.user,
                    updated_by=request.user,
                )
                pagos_out.append(mp.id)

            # Canjear descuento
            if cd:
                cd.restantes -= 1
                cd.updated_by = request.user
                cd.save(update_fields=["restantes", "updated_by", "updated_at"])

        return response.Response({
            "ok": True,
            "venta_id": venta.id,
            "detalles": detalles_out,
            "pagos": pagos_out,
            "subtotal": str(subtotal),
            "descuento": str(descuento_aplicado),
            "total": str(total),
        }, status=status.HTTP_201_CREATED)

# -----------------------------
# Detalles de venta
# -----------------------------
class DetalleVentaViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = DetalleVentaSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_fields = ["venta", "producto", "plan", "codigo_descuento"]
    ordering_fields = ["id", "total", "precio_unitario", "cantidad"]
    ordering = ["-id"]
    pagination_class = DefaultPagination

    queryset = (
        DetalleVenta.objects
        .select_related("venta", "plan", "producto", "codigo_descuento")
        .all()
    )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        if not request.query_params.get("ordering"):
            qs = qs.order_by("-id")
        qs = qs[:1000]  # límite duro
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return response.Response(ser.data)


# -----------------------------
# Métodos de pago
# -----------------------------
class MetodoPagoViewSet(CompanyScopedQuerysetMixin, BaseAuthViewSet):
    """CRUD de pagos por venta."""
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = MetodoPagoSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_fields = ["venta", "forma_pago"]
    ordering_fields = ["id", "importe"]
    ordering = ["-id"]
    pagination_class = DefaultPagination

    queryset = MetodoPago.objects.select_related("venta").all()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        if not request.query_params.get("ordering"):
            qs = qs.order_by("-id")
        qs = qs[:1000]  # límite duro
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return response.Response(ser.data)