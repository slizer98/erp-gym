from rest_framework import viewsets, permissions
from .models import Cliente, DatoContacto, DatosFiscales, Convenio, Caracteristica, DatoAdicional, ClienteSucursal
from .serializers import ClienteSerializer,     DatoContactoSerializer, DatosFiscalesSerializer, ConvenioSerializer, CaracteristicaSerializer, DatoAdicionalSerializer, ClienteSucursalSerializer
from core.mixins import CompanyScopedQuerysetMixin, ReceptionBranchScopedByClienteMixin
from core.permissions import IsAuthenticatedInCompany

class ClienteViewSet(ReceptionBranchScopedByClienteMixin, viewsets.ModelViewSet):
    queryset = Cliente.objects.select_related("usuario").all().order_by("id")
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class BaseAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DatoContactoViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    queryset = DatoContacto.objects.select_related("cliente").all()
    serializer_class = DatoContactoSerializer


class DatosFiscalesViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    queryset = DatosFiscales.objects.select_related("cliente").all()
    serializer_class = DatosFiscalesSerializer


class ConvenioViewSet(CompanyScopedQuerysetMixin, ReceptionBranchScopedByClienteMixin,BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Convenio.objects.select_related("cliente", "empresa").all()
    serializer_class = ConvenioSerializer


class CaracteristicaViewSet(CompanyScopedQuerysetMixin,BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = Caracteristica.objects.select_related("empresa").all()
    serializer_class = CaracteristicaSerializer


class DatoAdicionalViewSet(ReceptionBranchScopedByClienteMixin, BaseAuthViewSet):
    queryset = DatoAdicional.objects.select_related("cliente", "caracteristica").all()
    serializer_class = DatoAdicionalSerializer


class ClienteSucursalViewSet(CompanyScopedQuerysetMixin, ReceptionBranchScopedByClienteMixin,BaseAuthViewSet):
    permission_classes = [IsAuthenticatedInCompany]
    queryset = ClienteSucursal.objects.select_related("cliente", "sucursal", "empresa").all()
    serializer_class = ClienteSucursalSerializer