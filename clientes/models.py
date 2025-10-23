from django.db import models
from core.models import TimeStampedModel
from django.conf import settings
from django.core.exceptions import ValidationError
from empresas.models import Empresa, Sucursal


def cliente_avatar_upload_to(instance, filename):
    # Opcional: arma ruta por año/mes o por ID
    # A falta de empresa, lo dejamos simple:
    return f"clientes/avatars/{filename}"

def validate_image(file_obj):
    # Validación básica de tamaño (ej. 5MB) y content-type
    max_mb = 5
    if file_obj.size > max_mb * 1024 * 1024:
        raise ValidationError(f"La imagen supera {max_mb} MB.")
    valid_ctypes = {"image/jpeg", "image/png", "image/webp"}
    if getattr(file_obj, "content_type", None) and file_obj.content_type not in valid_ctypes:
        raise ValidationError("Formato no permitido. Usa JPG/PNG/WebP.")

class Cliente(TimeStampedModel):
    apellidos = models.CharField("Apellidos", max_length=255)
    nombre = models.CharField("Nombre", max_length=255)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    contacto_emergencia = models.CharField("Contacto de emergencia", max_length=255, blank=True)
    email = models.EmailField("Correo", max_length=254, blank=True)
    factura = models.BooleanField("¿Requiere factura?", default=False)
    observaciones = models.TextField("Observaciones", blank=True)
    recordar_vencimiento = models.BooleanField("Recordar vencimiento", default=False)
    recibo_pago = models.BooleanField("Enviar recibo de pago", default=False)
    recibir_promociones = models.BooleanField("Recibir promociones", default=True)
    genero = models.CharField("Género", max_length=20, blank=True)
    fecha_limite_pago = models.DateField("Fecha límite de pago", null=True, blank=True, db_index=True)
    esquema = models.CharField("Esquema", max_length=20, null=True)
    # Tu doc trae: Usuarios_id (revisar). Lo dejo como opcional por si quieres asignar un responsable/comercial.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="clientes_asignados",
        verbose_name="Usuario asignado"
    )
    avatar = models.ImageField(
        "Foto/Avatar",
        upload_to=cliente_avatar_upload_to,
        null=True,
        blank=True,
        validators=[validate_image],
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()
      
      
class DatoContacto(TimeStampedModel):
    class TipoContacto(models.TextChoices):
        CORREO = "correo", "Correo"
        TELEFONO = "telefono", "Teléfono"
        CELULAR = "celular", "Celular"
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        OTRO = "otro", "Otro"

    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="datos_contacto",
        verbose_name="Cliente"
    )
    tipo = models.CharField("Tipo", max_length=30, choices=TipoContacto.choices)
    valor = models.CharField("Valor", max_length=255)

    class Meta:
        verbose_name = "Dato de contacto"
        verbose_name_plural = "Datos de contacto"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.valor}"


# =========================
# DATOS FISCALES
# =========================
class DatosFiscales(TimeStampedModel):
    class PersonaTipo(models.TextChoices):
        FISICA = "fisica", "Persona Física"
        MORAL = "moral", "Persona Moral"

    cliente = models.OneToOneField(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="datos_fiscales",
        verbose_name="Cliente"
    )
    rfc = models.CharField("RFC", max_length=20, blank=True)
    razon_social = models.CharField("Razón social", max_length=255, blank=True)
    persona = models.CharField("Tipo de persona", max_length=10, choices=PersonaTipo.choices, blank=True)
    codigo_postal = models.CharField("Código postal", max_length=10, blank=True)
    regimen_fiscal = models.CharField("Régimen fiscal", max_length=120, blank=True)

    class Meta:
        verbose_name = "Datos fiscales"
        verbose_name_plural = "Datos fiscales"

    def __str__(self):
        return f"{self.rfc or 'Sin RFC'} - {self.razon_social or self.cliente}"


# =========================
# CONVENIOS
# =========================
class Convenio(TimeStampedModel):
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="convenios",
        verbose_name="Cliente",
        null=True, blank=True
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="convenios_clientes",
        verbose_name="Empresa"
    )
    empresa_convenio = models.CharField("Empresa del convenio", max_length=255, blank=True)
    telefono_oficina = models.CharField("Teléfono de oficina", max_length=30, blank=True)
    medio_entero = models.CharField("¿Cómo se enteró?", max_length=120, blank=True)
    tipo_cliente = models.CharField("Tipo de cliente", max_length=120, blank=True)

    class Meta:
        verbose_name = "Convenio"
        verbose_name_plural = "Convenios"

    def __str__(self):
        return f"{self.cliente} - {self.empresa_convenio or 'Convenio'}"


# =========================
# CARACTERÍSTICAS / DATOS ADICIONALES
# =========================
class Caracteristica(TimeStampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="caracteristicas",
        verbose_name="Empresa"
    )
    nombre = models.TextField("Nombre")
    tipo_dato = models.TextField("Tipo de dato")  # libre: texto, número, fecha, booleano, etc.

    class Meta:
        verbose_name = "Característica"
        verbose_name_plural = "Características"

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"


class DatoAdicional(TimeStampedModel):
    caracteristica = models.ForeignKey(
        Caracteristica,
        on_delete=models.CASCADE,
        related_name="valores",
        verbose_name="Característica"
    )
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="datos_adicionales",
        verbose_name="Cliente"
    )
    campo = models.CharField("Campo", max_length=255, blank=True)  # tu doc lo pide
    valor = models.CharField("Valor", max_length=255, blank=True)

    class Meta:
        verbose_name = "Dato adicional"
        verbose_name_plural = "Datos adicionales"

    def __str__(self):
        return f"{self.caracteristica.nombre}: {self.valor}"


# =========================
# CLIENTE - SUCURSAL
# =========================
class ClienteSucursal(TimeStampedModel):
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="sucursales_asignadas",
        verbose_name="Cliente"
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name="clientes_asignados",
        verbose_name="Sucursal"
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="clientes_sucursales",
        verbose_name="Empresa"
    )
    fecha_inicio = models.DateField("Fecha de inicio", null=True, blank=True)
    fecha_fin = models.DateField("Fecha de fin", null=True, blank=True)
    # is_active ya viene de TimeStampedModel

    class Meta:
        verbose_name = "Cliente por sucursal"
        verbose_name_plural = "Clientes por sucursal"
        unique_together = ("cliente", "sucursal", "empresa")

    def __str__(self):
        return f"{self.cliente} @ {self.sucursal}"
