from rest_framework.routers import DefaultRouter
from .views import (PlanViewSet, PrecioPlanViewSet, RestriccionPlanViewSet,     ServicioViewSet, BeneficioViewSet, PlanServicioViewSet, PlanBeneficioViewSet,
    DisciplinaViewSet, DisciplinaPlanViewSet, HorarioDisciplinaViewSet,
    AltaPlanViewSet, AccesoViewSet, ServicioBeneficioViewSet)

router = DefaultRouter()
router.register(r"planes/precios", PrecioPlanViewSet, basename="precio-plan")
router.register(r"planes/restricciones", RestriccionPlanViewSet, basename="restriccion-plan")

# Catálogos
router.register(r"servicios/beneficios", ServicioBeneficioViewSet, basename="servicio-beneficio")
router.register(r"servicios", ServicioViewSet, basename="servicio")
router.register(r"beneficios", BeneficioViewSet, basename="beneficio")

# Relaciones Plan
router.register(r"planes/servicios", PlanServicioViewSet, basename="plan-servicio")
router.register(r"planes/beneficios", PlanBeneficioViewSet, basename="plan-beneficio")

# Disciplinas
router.register(r"disciplinas/planes", DisciplinaPlanViewSet, basename="disciplina-plan")
router.register(r"disciplinas/horarios", HorarioDisciplinaViewSet, basename="horario-disciplina")
router.register(r"disciplinas", DisciplinaViewSet, basename="disciplina")

# Operativa
router.register(r"planes/altas", AltaPlanViewSet, basename="alta-plan")
router.register(r"accesos", AccesoViewSet, basename="acceso")
router.register(r"planes", PlanViewSet, basename="plan")

urlpatterns = router.urls
