from rest_framework.routers import DefaultRouter
from .views import CodigoDescuentoViewSet, VentaViewSet, DetalleVentaViewSet

router = DefaultRouter()
router.register(r"ventas/codigos-descuento", CodigoDescuentoViewSet, basename="codigo-descuento")
router.register(r"ventas/detalles", DetalleVentaViewSet, basename="detalle-venta")
router.register(r"ventas/ventas", VentaViewSet, basename="venta")
urlpatterns = router.urls
