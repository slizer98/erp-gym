from rest_framework.routers import DefaultRouter
from .views import AlmacenViewSet, CategoriaProductoViewSet, ProductoViewSet, MovimientoProductoViewSet

router = DefaultRouter()
router.register(r"almacenes", AlmacenViewSet, basename="almacen")
router.register(r"categorias-producto", CategoriaProductoViewSet, basename="categoria-producto")
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"movimientos-producto", MovimientoProductoViewSet, basename="movimiento-producto")
urlpatterns = router.urls
