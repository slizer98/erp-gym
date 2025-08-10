from rest_framework.routers import DefaultRouter
from .views import (
    DatoContactoViewSet, DatosFiscalesViewSet, ConvenioViewSet,
    CaracteristicaViewSet, DatoAdicionalViewSet, ClienteSucursalViewSet,
)

router = DefaultRouter()
router.register(r"clientes/datos-contacto", DatoContactoViewSet, basename="cliente-dato-contacto")
router.register(r"clientes/datos-fiscales", DatosFiscalesViewSet, basename="cliente-datos-fiscales")
router.register(r"clientes/convenios", ConvenioViewSet, basename="cliente-convenio")
router.register(r"clientes/caracteristicas", CaracteristicaViewSet, basename="cliente-caracteristica")
router.register(r"clientes/datos-adicionales", DatoAdicionalViewSet, basename="cliente-dato-adicional")
router.register(r"clientes/sucursales", ClienteSucursalViewSet, basename="cliente-sucursal")

urlpatterns = router.urls
