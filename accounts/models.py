from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario/empleado basado en tu tabla 'Usuarios'.
    Aprovechamos los campos nativos de Django:
      - username        -> (tabla: usuario)
      - password        -> (tabla: contraseña)  [encriptada]
      - last_login      -> (tabla: ultimo_acceso)
      - email           -> (tabla: correo)
      - first_name      -> (tabla: nombre)
      - last_name       -> (tabla: apellido)
      - is_active       -> (tabla: is_active)

    Extra del dominio (sí existen en tu tabla y NO los trae AbstractUser):
      - empresa (FK)
      - cargo, dias_trabajo
      - horario_entrada, horario_salida
      - fecha_contratacion
      - codigo_postal, telefono, fecha_nacimiento, numero_seguro
      - domicilio, notas
    """

    # FK a empresas (tu tabla: empresa_id)
    empresa = models.ForeignKey(
        "empresas.Empresa",
        on_delete=models.PROTECT,
        related_name="usuarios",
        verbose_name="Empresa",
        null=True,
        blank=True,
    )

    # Campos del dominio
    cargo = models.CharField("Cargo", max_length=150, blank=True)
    dias_trabajo = models.CharField(
        "Días de trabajo",
        max_length=150,
        blank=True,
        help_text="Texto libre, ej. 'Lun-Vie' o 'Lun,Mié,Vie'."
    )
    horario_entrada = models.TimeField("Horario de entrada", null=True, blank=True)
    horario_salida = models.TimeField("Horario de salida", null=True, blank=True)
    fecha_contratacion = models.DateField("Fecha de contratación", null=True, blank=True)

    codigo_postal = models.CharField("Código postal", max_length=10, blank=True)
    telefono = models.CharField("Teléfono", max_length=20, blank=True)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    numero_seguro = models.CharField("No. seguro", max_length=50, blank=True)
    domicilio = models.TextField("Domicilio", blank=True)
    notas = models.TextField("Notas", blank=True)

    # Opcional: asegurar emails únicos por sistema (si lo deseas)
    # email ya existe en AbstractUser
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    # Atajos para mantener nombres de tu documento:
    @property
    def nombre(self):
        return self.first_name

    @nombre.setter
    def nombre(self, value):
        self.first_name = value or ""

    @property
    def apellido(self):
        return self.last_name

    @apellido.setter
    def apellido(self, value):
        self.last_name = value or ""

    def __str__(self):
        full = (self.first_name or "").strip() + " " + (self.last_name or "").strip()
        return full.strip() or self.username
