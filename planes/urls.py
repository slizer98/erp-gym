from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, PrecioPlanViewSet, RestriccionPlanViewSet

router = DefaultRouter()
router.register(r"planes/precios", PrecioPlanViewSet, basename="precio-plan")
router.register(r"planes/restricciones", RestriccionPlanViewSet, basename="restriccion-plan")
router.register(r"planes", PlanViewSet, basename="plan")

urlpatterns = router.urls
