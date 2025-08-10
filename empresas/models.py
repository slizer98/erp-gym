from django.db import models
from core.models import TimeStampedModel


class Empresa(TimeStampedModel):
    nombre = models.CharField("Nombre", max_length=255)
    razon_social = models.CharField("Razón social", max_length=255, blank=True)
    rfc = models.CharField("RFC", max_length=20, blank=True)
    direccion = models.TextField("Dirección", blank=True)
    telefono = models.CharField("Teléfono", max_length=30, blank=True)
    correo = models.EmailField("Correo", max_length=254, blank=True)
    sitio_web = models.CharField("Sitio web", max_length=255, blank=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nombre


class Sucursal(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="sucursales",
        verbose_name="Empresa",
    )
    nombre = models.CharField("Nombre", max_length=255)
    direccion = models.TextField("Dirección", blank=True)
    # Nota en tu doc: "telefono varchar // relacionar con usuarios"
    # Por ahora respetamos 'varchar'; más adelante podemos enlazar responsable a Usuario.
    telefono = models.CharField("Teléfono", max_length=30, blank=True)
    correo = models.EmailField("Correo", max_length=254, blank=True)
    responsable = models.CharField("Responsable", max_length=255, blank=True)
    horario_apertura = models.TimeField("Horario de apertura", null=True, blank=True)
    horario_cierre = models.TimeField("Horario de cierre", null=True, blank=True)

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        unique_together = ("empresa", "nombre")

    def __str__(self):
        return f"{self.empresa.nombre} - {self.nombre}"


class Configuracion(models.Model):
    """
    Catálogo de claves de configuración disponibles para el sistema.
    (Global; no está ligada a una empresa en tu esquema.)
    """
    nombre = models.CharField("Nombre", max_length=150, unique=True)
    tipo_dato = models.CharField("Tipo de dato", max_length=30)  # ej: text, int, decimal, bool, date, datetime, json
    descripcion = models.TextField("Descripción", blank=True)

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuraciones"

    def __str__(self):
        return f"{self.nombre} ({self.tipo_dato})"


class ValorConfiguracion(TimeStampedModel):
    """
    Valor por empresa para una configuración específica.
    """
    configuracion = models.ForeignKey(
        Configuracion,
        on_delete=models.CASCADE,
        related_name="valores",
        verbose_name="Configuración"
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="valores_configuracion",
        verbose_name="Empresa"
    )
    valor = models.TextField("Valor")  # Se valida/parsea según tipo_dato en el serializer

    class Meta:
        verbose_name = "Valor de configuración"
        verbose_name_plural = "Valores de configuración"
        unique_together = ("configuracion", "empresa")  # una clave por empresa

    def __str__(self):
        return f"{self.empresa} -> {self.configuracion.nombre} = {self.valor}"