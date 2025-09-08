from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet, CategoriaEgresoViewSet, EgresoViewSet

router = DefaultRouter()
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")
router.register(r"categorias-egresos", CategoriaEgresoViewSet, basename="categoria-egreso")
router.register(r"egresos", EgresoViewSet, basename="egreso")
urlpatterns = router.urls
