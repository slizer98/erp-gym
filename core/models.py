
from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """
    Modelo abstracto con campos de auditoría comunes.
    Lo heredan todas las tablas que necesiten created/updated/is_active.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="creado")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="actualizado")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
        verbose_name="creado por"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
        verbose_name="actualizado por"
    )

    is_active = models.BooleanField(default=True, verbose_name="activo")

    class Meta:
        abstract = True
