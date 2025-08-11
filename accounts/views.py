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
