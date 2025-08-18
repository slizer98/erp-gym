from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from empleados.models import UsuarioEmpresa
from .serializers import UsuarioPerfilSerializer

class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Prefetch de asignaciones con empresa y sucursal para minimizar queries
        asignaciones = (UsuarioEmpresa.objects
                        .select_related("empresa", "sucursal")
                        .filter(usuario=user)
                        .order_by("id"))

        # Elegir asignación activa:
        # - Si viene ?empresa=ID, usa la primera asignación activa de esa empresa
        # - Si viene ?sucursal=ID, usa esa sucursal (si existe)
        # - Si no, la primera activa o la primera disponible
        empresa_id = request.query_params.get("empresa")
        sucursal_id = request.query_params.get("sucursal")
        asignacion_activa = None

        if sucursal_id:
            asignacion_activa = next((a for a in asignaciones if a.sucursal_id == int(sucursal_id)), None)

        if not asignacion_activa and empresa_id:
            asignacion_activa = next((a for a in asignaciones if a.empresa_id == int(empresa_id) and a.is_active), None)

        if not asignacion_activa:
            asignacion_activa = next((a for a in asignaciones if a.is_active), None) or (asignaciones[0] if asignaciones else None)

        # Serializar
        user.prefetch_asignaciones = list(asignaciones)  # para usar en el serializer sin reconsultar
        serializer = UsuarioPerfilSerializer(user, context={"asignacion_activa": asignacion_activa})
        return Response(serializer.data)


from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q

from .serializers import UsuarioListSerializer, UsuarioCreateUpdateSerializer
from core.permissions import CanAccessERP  # ya lo tienes
# from core.mixins import IsAuthenticatedInCompany  # ya lo tienes

Usuario = get_user_model()

def get_header_empresa_id(request):
    v = request.META.get('HTTP_X_EMPRESA_ID') or request.headers.get('X-Empresa-Id')
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

class UsuarioViewSet(viewsets.ModelViewSet):
    """
    CRUD básico de usuarios (empleados). Requiere rol alto para crear/editar.
    Scoping por empresa: si no es superuser, filtra por empresa del usuario autenticado
    o por X-Empresa-Id cuando aplique.
    """
    queryset = Usuario.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticated, CanAccessERP]
    filterset_fields = ['empresa','is_active','is_staff']
    search_fields = ['username','email','first_name','last_name','telefono','cargo']
    ordering_fields = ['id','username','email','first_name','last_name','date_joined','last_login']

    def get_serializer_class(self):
        if self.action in ('create','update','partial_update'):
            return UsuarioCreateUpdateSerializer
        return UsuarioListSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # Superuser ve todo
        u = self.request.user
        if getattr(u, 'is_superuser', False):
            return qs

        # Si el usuario tiene empresa en su perfil, filtra por ahí
        user_empresa_id = getattr(u, 'empresa_id', None)
        header_emp_id = get_header_empresa_id(self.request)

        if user_empresa_id:
            qs = qs.filter(empresa_id=user_empresa_id)
        elif header_emp_id:
            qs = qs.filter(empresa_id=header_emp_id)
        else:
            qs = qs.none()

        return qs

    def perform_create(self, serializer):
        # Inyecta empresa si no la mandaron
        empresa_id = serializer.validated_data.get('empresa_id') or get_header_empresa_id(self.request) or getattr(self.request.user, 'empresa_id', None)
        if empresa_id:
            serializer.validated_data['empresa_id'] = empresa_id

        # Solo superuser puede setear is_superuser; bloquea desde aquí por seguridad
        if not getattr(self.request.user, 'is_superuser', False):
            serializer.validated_data.pop('is_superuser', None)

        serializer.save()

    def perform_update(self, serializer):
        if not getattr(self.request.user, 'is_superuser', False):
            serializer.validated_data.pop('is_superuser', None)
        serializer.save()

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Devuelve tu propio perfil de usuario (útil en UI)."""
        ser = UsuarioListSerializer(request.user)
        return Response(ser.data)