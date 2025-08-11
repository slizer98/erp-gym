from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from empresas.models import Empresa

class Plan(TimeStampedModel):
    """
    Tabla: planes
    """
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name="planes", verbose_name="Empresa"
    )
    nombre = models.CharField("Nombre", max_length=255)
    descripcion = models.TextField("Descripción", blank=True)
    acceso_multisucursal = models.BooleanField("Acceso multisucursal", default=False)
    tipo_plan = models.CharField("Tipo de plan", max_length=50, blank=True)  # libre: mensual, semanal, sesiones, etc.
    preventa = models.BooleanField("Preventa", default=False)
    desde = models.DateField("Vigente desde", null=True, blank=True)
    hasta = models.DateField("Vigente hasta", null=True, blank=True)
    visitas_gratis = models.PositiveIntegerField("Visitas gratis", default=0)

    # Tu tabla incluye Usuario_id aparte de auditoría; lo dejamos como “responsable” opcional:
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="planes_responsables",
        verbose_name="Usuario responsable"
    )

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Planes"
        unique_together = ("empresa", "nombre")  # evita duplicados de nombre en la misma empresa

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"


class PrecioPlan(TimeStampedModel):
    """
    Tabla: precios_planes
    """
    class Esquema(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        GRUPAL = "grupal", "Grupal"
        EMPRESA = "empresa", "Empresa"

    class Tipo(models.TextChoices):
        MENSUAL = "mensual", "Mensual"
        SEMANAL = "semanal", "Semanal"
        SESIONES = "sesiones", "Por sesiones"

    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE,
        related_name="precios", verbose_name="Plan"
    )
    esquema = models.CharField("Esquema", max_length=20, choices=Esquema.choices)
    tipo = models.CharField("Tipo", max_length=20, choices=Tipo.choices)
    precio = models.DecimalField("Precio", max_digits=10, decimal_places=2)
    numero_visitas = models.PositiveIntegerField(
        "Número de visitas", default=0,
        help_text="Si es 0, no se contabilizan visitas."
    )

    # Usuario_id en tu tabla:
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="precios_planes_responsables",
        verbose_name="Usuario responsable"
    )

    class Meta:
        verbose_name = "Precio de plan"
        verbose_name_plural = "Precios de plan"
        unique_together = ("plan", "esquema", "tipo")  # evita duplicados del mismo esquema/tipo por plan

    def __str__(self):
        return f"{self.plan} - {self.esquema} / {self.tipo}: {self.precio}"


class RestriccionPlan(TimeStampedModel):
    """
    Tabla: restricciones_planes
    """
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE,
        related_name="restricciones", verbose_name="Plan"
    )
    dia = models.CharField("Día", max_length=20)  # libre: Lunes/Martes/... o código numérico, según tu preferencia
    hora_inicio = models.TimeField("Hora inicio", null=True, blank=True)
    hora_fin = models.TimeField("Hora fin", null=True, blank=True)

    # Usuario_id en tu tabla:
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="restricciones_planes_responsables",
        verbose_name="Usuario responsable"
    )

    class Meta:
        verbose_name = "Restricción de plan"
        verbose_name_plural = "Restricciones de plan"

    def __str__(self):
        return f"{self.plan} - {self.dia} ({self.hora_inicio} - {self.hora_fin})"
