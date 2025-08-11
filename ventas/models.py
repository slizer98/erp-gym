from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from empresas.models import Empresa

class CodigoDescuento(TimeStampedModel):
    """
    Tabla: codigos_descuento
    """
    class Tipo(models.TextChoices):
        PORCENTAJE = "porcentaje", "Porcentaje"
        MONTO = "monto", "Monto"

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name="codigos_descuento", verbose_name="Empresa"
    )
    codigo = models.CharField("Código", max_length=50)
    descuento = models.DecimalField("Descuento", max_digits=10, decimal_places=2)
    tipo_descuento = models.CharField("Tipo de descuento", max_length=20, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField("Cantidad disponible", default=0)
    restantes = models.PositiveIntegerField("Usos restantes", default=0)

    # Usuario_id de tu tabla como responsable opcional
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="codigos_descuento_responsables",
        verbose_name="Usuario responsable"
    )

    class Meta:
        verbose_name = "Código de descuento"
        verbose_name_plural = "Códigos de descuento"
        unique_together = ("empresa", "codigo")   # mismo código no se repite en la empresa
        indexes = [
            models.Index(fields=["empresa", "codigo"]),
        ]

    def save(self, *args, **kwargs):
        # normaliza el código en mayúsculas y sin espacios alrededor
        if self.codigo:
            self.codigo = self.codigo.strip().upper()
        # si se crea y 'restantes' no se puso, igualarlo a 'cantidad'
        if not self.pk and (self.restantes is None or self.restantes == 0):
            self.restantes = self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} ({self.empresa})"
