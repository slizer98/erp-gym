from rest_framework.routers import DefaultRouter
from .views import UsuarioEmpresaViewSet

router = DefaultRouter()
router.register(r"usuarios-empresa", UsuarioEmpresaViewSet, basename="usuario-empresa")

urlpatterns = router.urls
