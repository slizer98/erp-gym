# planes/services.py
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Q

from .models import (
    Plan, PlanRevision,
    PrecioPlanRevision, RestriccionPlanRevision,
    PlanServicioRevision, PlanBeneficioRevision, DisciplinaPlanRevision,
)

def publish_plan_revision(plan: Plan, vigente_desde=None, vigente_hasta=None) -> PlanRevision:
    """Crea una nueva PlanRevision copiando el estado actual del plan e hijos."""
    last = plan.revisiones.order_by("-version").first()
    next_version = (last.version + 1) if last else 1

    rev = PlanRevision.objects.create(
        plan=plan,
        version=next_version,
        nombre=plan.nombre,
        descripcion=plan.descripcion,
        acceso_multisucursal=plan.acceso_multisucursal,
        tipo_plan=plan.tipo_plan,
        preventa=plan.preventa,
        visitas_gratis=plan.visitas_gratis,
        vigente_desde=vigente_desde,
        vigente_hasta=vigente_hasta,
    )

    PrecioPlanRevision.objects.bulk_create([
        PrecioPlanRevision(revision=rev, esquema=p.esquema, tipo=p.tipo,
                           precio=p.precio, numero_visitas=p.numero_visitas)
        for p in plan.precios.all()
    ])
    RestriccionPlanRevision.objects.bulk_create([
        RestriccionPlanRevision(revision=rev, dia=r.dia, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin)
        for r in plan.restricciones.all()
    ])
    PlanServicioRevision.objects.bulk_create([
        PlanServicioRevision(revision=rev, servicio=ps.servicio, precio=ps.precio, icono=ps.icono)
        for ps in plan.servicios_incluidos.all()
    ])
    PlanBeneficioRevision.objects.bulk_create([
        PlanBeneficioRevision(revision=rev, beneficio=pb.beneficio,
                              vigencia_inicio=pb.vigencia_inicio, vigencia_fin=pb.vigencia_fin)
        for pb in plan.beneficios_incluidos.all()
    ])
    DisciplinaPlanRevision.objects.bulk_create([
        DisciplinaPlanRevision(revision=rev, disciplina=dp.disciplina,
                               tipo_acceso=dp.tipo_acceso, numero_accesos=dp.numero_accesos)
        for dp in plan.disciplinas.all()
    ])
    return rev


def get_revision_vigente(plan: Plan, fecha):
    """Devuelve la revisión vigente a `fecha` (o None si no hay)."""
    return plan.revisiones.filter(
        Q(vigente_desde__isnull=True) | Q(vigente_desde__lte=fecha),
        Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha),
    ).order_by("-version").first()


def ensure_revision_for_date(plan: Plan, fecha):
    """
    Devuelve una revisión vigente para `fecha`. Si no existe, publica una nueva
    con vigente_desde=fecha.
    """
    fecha = fecha or now().date()
    vigente = get_revision_vigente(plan, fecha)
    if vigente:
        return vigente
    with transaction.atomic():
        return publish_plan_revision(plan, vigente_desde=fecha)
