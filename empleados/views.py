from rest_framework import viewsets, permissions
from .models import UsuarioEmpresa
from .serializers import UsuarioEmpresaSerializer
from core.mixins import CompanyScopedQuerysetMixin

class UsuarioEmpresaViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = UsuarioEmpresa.objects.select_related("usuario", "empresa", "sucursal").all()
    serializer_class = UsuarioEmpresaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
