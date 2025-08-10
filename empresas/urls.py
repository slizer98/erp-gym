from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmpresaViewSet, SucursalViewSet, ConfiguracionViewSet, ValorConfiguracionViewSet

router = DefaultRouter()
router.register(r"empresas", EmpresaViewSet, basename="empresa")
router.register(r"sucursales", SucursalViewSet, basename="sucursal")
router.register(r"configuraciones", ConfiguracionViewSet, basename="configuracion")
router.register(r"valores-configuracion", ValorConfiguracionViewSet, basename="valor-configuracion")

urlpatterns = [
    path("", include(router.urls)),
]
