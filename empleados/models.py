from django.conf import settings
from django.db import models
from core.models import TimeStampedModel
from empresas.models import Empresa, Sucursal

class UsuarioEmpresa(TimeStampedModel):
    """
    Asigna un usuario (empleado) a una empresa y opcionalmente a una sucursal,
    con rol y permisos (flexibles en JSON).
    Basado en tu tabla 'usuarios_empresa'.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asignaciones_empresa",
        verbose_name="Usuario"
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="usuarios_asignados",
        verbose_name="Empresa"
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name="usuarios_asignados",
        null=True, blank=True,
        verbose_name="Sucursal"
    )
    rol = models.CharField("Rol", max_length=50)
    # En tu documento es text. Usar JSONField es más útil;
    # si prefieres TextField, cámbialo por models.TextField(blank=True).
    permisos = models.JSONField("Permisos", blank=True, null=True)

    class Meta:
        verbose_name = "Usuario de empresa"
        verbose_name_plural = "Usuarios de empresa"
        unique_together = ("usuario", "empresa", "sucursal")

    def __str__(self):
        return f"{self.usuario} - {self.empresa} ({self.sucursal or 'Sin sucursal'})"
