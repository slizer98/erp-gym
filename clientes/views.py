from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django.utils.timezone import now
from django.db.models import Q
from rest_framework.response import Response
from .models import Cliente, DatoContacto, DatosFiscales, Convenio, Caracteristica, DatoAdicional, ClienteSucursal
from planes.models import AltaPlan
from .serializers import ClienteSerializer,     DatoContactoSerializer, DatosFiscalesSerializer, ConvenioSerializer, CaracteristicaSerializer, DatoAdicionalSerializer, ClienteSucursalSerializer
from core.mixins import CompanyScopedQuerysetMixin, ReceptionBranchScopedByClienteMixin
from core.permissions import IsAuthenticatedInCompany
from django.core.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination


class SmallResultsSetPagination(PageNumberPagination):
    page_size = 10                       # default
    page_size_query_param = 'page_size'  # <-- permite ?page_size=10 desde tu front
    max_page_size = 50

# class ClienteViewSet(ReceptionBranchScopedByClienteMixin, viewsets.ModelViewSet):
#     queryset = Cliente.objects.select_related("usuario").all().order_by("id")
#     serializer_class = ClienteSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     # 🔎 habilita búsqueda y orden
#     filter_backends = [SearchFilter, OrderingFilter]
#     search_fields = ["nombre", "apellidos", "email"]  # añade más si quieres
#     ordering_fields = ["id", "nombre", "apellidos", "created_at"]
#     ordering = ["-id"]
#     pagination_class = SmallResultsSetPagination
    
#     def perform_create(self, serializer):
#         serializer.save(created_by=self.request.user, updated_by=self.request.user)

#     def perform_update(self, serializer):
#         serializer.save(updated_by=self.request.user)
      
#     @action(detail=True, methods=["get"])
#     def resumen(self, request, pk=None):
#         c = self.get_object()

#         # ---- Contacto: convierte (tipo, valor) -> dict { email, celular, telefono }
#         contacto = {}
#         if DatoContacto is not None:
#             # Tomamos el último por tipo (email/celular/telefono)
#             def ultimo_val(tipo):
#                 row = (DatoContacto.objects
#                        .filter(cliente=c, tipo__iexact=tipo)
#                        .order_by("-id").values("valor").first())
#                 return (row or {}).get("valor")
#             contacto = {
#                 "email":    ultimo_val("email")    or (getattr(c, "email", None) or ""),
#                 "celular":  ultimo_val("celular")  or "",
#                 "telefono": ultimo_val("telefono") or "",
#             }
#         else:
#             contacto = {
#                 "email":    getattr(c, "email", None) or "",
#                 "celular":  getattr(c, "celular", "") or "",
#                 "telefono": getattr(c, "telefono", "") or "",
#             }

#         # ---- Datos fiscales (si existen)
#         fiscal = {}
#         if DatosFiscales is not None:
#             row = (DatosFiscales.objects
#                    .filter(cliente=c).order_by("-id")
#                    .values("rfc", "razon_social").first()) or {}
#             fiscal = {
#                 "rfc": row.get("rfc") or "",
#                 "razon_social": row.get("razon_social") or "",
#             }

#         # ---- Última asignación de sucursal (si existe)
#         sucursal_nombre = None
#         if ClienteSucursal is not None:
#             cs = (ClienteSucursal.objects
#                   .filter(cliente=c).select_related("sucursal")
#                   .order_by("-id").first())
#             if cs and cs.sucursal:
#                 sucursal_nombre = cs.sucursal.nombre

#         # ---- Plan actual (si manejas Altas de plan)
#         plan_actual = None
#         plan_estado = None
#         proximo_cobro = None
#         ultimo_pago = None  # si luego tienes modelo de pagos, aquí lo rellenas

#         if AltaPlan is not None:
#             # “Vigente” simple: último registro por fecha_alta; puedes afinar con vencimiento >= hoy
#             alta = (AltaPlan.objects
#                     .select_related("plan")
#                     .filter(cliente=c)
#                     .order_by("-fecha_alta", "-id")
#                     .first())
#             if alta:
#                 plan_actual = getattr(getattr(alta, "plan", None), "nombre", None)
#                 # estado: activo si no hay vencimiento o si hoy <= vencimiento
#                 fv = getattr(alta, "fecha_vencimiento", None)
#                 if fv:
#                     plan_estado = "activo" if now().date() <= fv else "vencido"
#                 else:
#                     plan_estado = "activo"
#                 # si manejas fecha_limite_pago, úsala como “próximo cobro”
#                 proximo_cobro = getattr(alta, "fecha_limite_pago", None)

#         data = {
#             "id": c.id,
#             "nombre": getattr(c, "nombre", "") or "",
#             "apellidos": getattr(c, "apellidos", "") or "",
#             "email": getattr(c, "email", None),
#             "created": getattr(c, "created_at", None),
#             "estado": getattr(c, "estado", None),  # o is_active si usas booleano
#             "is_active": bool(getattr(c, "is_active", True)),
#             "sucursal_nombre": sucursal_nombre,

#             "contacto": contacto,
#             "fiscal": fiscal,

#             # Ficha extra (para el card lateral)
#             "inscripcion": getattr(c, "fecha_alta", None) or getattr(c, "created_at", None),
#             "proximo_cobro": proximo_cobro,
#             "ultimo_pago": ultimo_pago,

#             # Plan actual/estado para pintar “Activo – <Plan>” en la columna
#             "plan_actual": plan_actual,     # ej. "Plan Premium"
#             "plan_estado": plan_estado,     # "activo" | "vencido" | None
#         }
#         return Response(data)

class ClienteViewSet(ReceptionBranchScopedByClienteMixin, viewsets.ModelViewSet):
    queryset = (
        Cliente.objects
        .select_related("usuario")
        .all()
        .order_by("-id")
    )
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

    # 🔎 Búsqueda/orden (útiles si en algún punto los usas desde el front, pero sin paginar)
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nombre", "apellidos", "email"]  # añade campos si hace falta
    ordering_fields = ["id", "nombre", "apellidos", "created_at"]
    ordering = ["-id"]

    # 🟥 Desactivar paginación SOLO en esta vista (aunque haya paginación global en settings)
    pagination_class = None

    # ⚠️ Forzamos el list a NO usar paginación:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())  # respeta search/order si los mandas
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)  # ← arreglo plano con TODOS los clientes

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        c = self.get_object()

        # ---- Contacto
        contacto = {}
        if DatoContacto is not None:
            def ultimo_val(tipo):
                row = (
                    DatoContacto.objects
                    .filter(cliente=c, tipo__iexact=tipo)
                    .order_by("-id").values("valor").first()
                )
                return (row or {}).get("valor")
            contacto = {
                "email":    ultimo_val("email")    or (getattr(c, "email", None) or ""),
                "celular":  ultimo_val("celular")  or "",
                "telefono": ultimo_val("telefono") or "",
            }
        else:
            contacto = {
                "email":    getattr(c, "email", None) or "",
                "celular":  getattr(c, "celular", "") or "",
                "telefono": getattr(c, "telefono", "") or "",
            }

        # ---- Datos fiscales
        fiscal = {}
        if DatosFiscales is not None:
            row = (
                DatosFiscales.objects
                .filter(cliente=c).order_by("-id")
                .values("rfc", "razon_social").first()
            ) or {}
            fiscal = {
                "rfc": row.get("rfc") or "",
                "razon_social": row.get("razon_social") or "",
            }

        # ---- Última sucursal
        sucursal_nombre = None
        if ClienteSucursal is not None:
            cs = (
                ClienteSucursal.objects
                .filter(cliente=c).select_related("sucursal")
                .order_by("-id").first()
            )
            if cs and cs.sucursal:
                sucursal_nombre = cs.sucursal.nombre

        # ---- Plan / AltaPlan
        plan_actual = None
        plan_estado = None
        proximo_cobro = None
        ultimo_pago = None   # reservar para cuando tengas pagos
        fecha_alta = getattr(c, "created_at", None)
        fecha_limite = None
        costo_inscripcion = None
        plan_id = None

        plan_fecha_limite = None  # posible respaldo desde Plan

        if AltaPlan is not None:
            alta = (
                AltaPlan.objects
                .select_related("plan")
                .filter(cliente=c)               # si quieres, añade .filter(empresa=request.headers.get("X-Empresa-Id"))
                .order_by("-fecha_alta", "-id")
                .first()
            )
            if alta:
                plan = getattr(alta, "plan", None)
                plan_id = getattr(plan, "id", None)
                plan_actual = getattr(plan, "nombre", None)
                costo_inscripcion = getattr(plan, "costo_inscripcion", None)
                plan_fecha_limite = getattr(plan, "fecha_limite_pago", None)

                # estado por vencimiento
                fv = getattr(alta, "fecha_vencimiento", None)
                if fv:
                    plan_estado = "activo" if now().date() <= fv else "vencido"
                else:
                    plan_estado = "activo"

                # fechas clave
                fecha_alta = getattr(alta, "fecha_alta", None) or fecha_alta
                proximo_cobro = getattr(alta, "fecha_limite_pago", None) or plan_fecha_limite
                fecha_limite = getattr(alta, "fecha_limite_pago", None) or plan_fecha_limite

        # si no hubo AltaPlan pero sí plan_fecha_limite (poco común), úsalo
        if not proximo_cobro and plan_fecha_limite:
            proximo_cobro = plan_fecha_limite
        if not fecha_limite and plan_fecha_limite:
            fecha_limite = plan_fecha_limite

        data = {
            "id": c.id,
            "nombre": getattr(c, "nombre", "") or "",
            "apellidos": getattr(c, "apellidos", "") or "",
            "email": contacto.get("email") or None,   # el card mostrará sólo si existe
            "created": getattr(c, "created_at", None),
            "estado": getattr(c, "estado", None),
            "is_active": bool(getattr(c, "is_active", True)),
            "sucursal_nombre": sucursal_nombre,

            "contacto": contacto,
            "fiscal": { "rfc": fiscal.get("rfc") or "" },  # el card mostrará sólo si existe

            # Fechas para el card
            "fecha_alta": fecha_alta,            # costo_inscripcion(fecha de alta) -> FECHA
            "proximo_cobro": proximo_cobro,
            "fecha_limite": fecha_limite,        # adicional a proximo_cobro

            # Plan
            "plan_id": plan_id,
            "plan_actual": plan_actual,          # texto ("Plan Premium")
            "plan_estado": plan_estado,          # "activo"/"vencido"/None
            "costo_inscripcion": costo_inscripcion,  # MXN (Decimal)

            # opcional
            "ultimo_pago": ultimo_pago,
        }
        return Response(data)

class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DatoContactoViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    serializer_class = DatoContactoSerializer

    def get_queryset(self):
        qs = DatoContacto.objects.select_related("cliente").all()
        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id) 
        return qs



class DatosFiscalesViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    serializer_class = DatosFiscalesSerializer

    def get_queryset(self):
        qs = DatosFiscales.objects.select_related("cliente").all()
        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        return qs


# views.py
class ConvenioViewSet(CompanyScopedQuerysetMixin,
                      ReceptionBranchScopedByClienteMixin,
                      BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = ConvenioSerializer
    queryset = Convenio.objects.select_related("cliente","empresa").all()

    def get_queryset(self):
        qs = super().get_queryset()
        # CompanyScopedQuerysetMixin suele aplicar empresa por header; si no,
        # asegúralo manualmente:
        empresa_id = getattr(self.request, "empresa_id", None) or self.request.headers.get("X-Empresa-Id")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        cliente = self.request.query_params.get("cliente")
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return qs.order_by("-id")

    def perform_create(self, serializer):
        empresa_id = getattr(self.request, "empresa_id", None) or self.request.headers.get("X-Empresa-Id")
        if not empresa_id:
            raise ValidationError({"empresa": "Falta X-Empresa-Id en encabezado"})
        serializer.save(empresa_id=empresa_id)



class CaracteristicaViewSet(CompanyScopedQuerysetMixin,BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Caracteristica.objects.select_related("empresa").all()
    serializer_class = CaracteristicaSerializer


class DatoAdicionalViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    queryset = DatoAdicional.objects.select_related("cliente", "caracteristica").all()
    serializer_class = DatoAdicionalSerializer


# class ClienteSucursalViewSet(CompanyScopedQuerysetMixin, ReceptionBranchScopedByClienteMixin,BaseAuthViewSet):
#     permission_classes = [IsAuthenticatedInCompany]
#     queryset = ClienteSucursal.objects.select_related("cliente", "sucursal", "empresa").all()
#     serializer_class = ClienteSucursalSerializer

class ClienteSucursalViewSet(CompanyScopedQuerysetMixin,
                             ReceptionBranchScopedByClienteMixin,
                             BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    serializer_class = ClienteSucursalSerializer
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["id", "fecha_inicio", "fecha_fin", "sucursal__nombre"]
    ordering = ["-id"]

    def get_queryset(self):
        qs = (ClienteSucursal.objects
              .select_related("cliente", "sucursal", "empresa"))

        empresa_id = getattr(getattr(self.request, "company", None), "id", None)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        # Filtro por ?cliente=ID (usa *_id para entero)
        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        # Si más parámetros (p.ej. ?sucursal=ID):
        sucursal_id = self.request.query_params.get("sucursal")
        if sucursal_id:
            qs = qs.filter(sucursal_id=sucursal_id)

        qs = qs.distinct()

        return qs