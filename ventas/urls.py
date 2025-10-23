from rest_framework.routers import DefaultRouter
from .views import CodigoDescuentoViewSet, VentaViewSet, DetalleVentaViewSet, MetodoPagoViewSet

router = DefaultRouter()
router.register(r"ventas/codigos-descuento", CodigoDescuentoViewSet, basename="codigo-descuento")
router.register(r"ventas/detalles", DetalleVentaViewSet, basename="detalle-venta")
router.register(r"ventas/pagos", MetodoPagoViewSet, basename="metodo-pago")
router.register(r"ventas", VentaViewSet, basename="venta")
urlpatterns = router.urls
