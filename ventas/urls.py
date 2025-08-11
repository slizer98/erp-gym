from rest_framework.routers import DefaultRouter
from .views import CodigoDescuentoViewSet

router = DefaultRouter()
router.register(r"ventas/codigos-descuento", CodigoDescuentoViewSet, basename="codigo-descuento")

urlpatterns = router.urls
