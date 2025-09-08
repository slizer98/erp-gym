from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from empresas.models import Empresa, Sucursal

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

class Servicio(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="servicios", verbose_name="Empresa")
    nombre = models.CharField("Nombre del servicio", max_length=255)
    descripcion = models.TextField("Descripción", blank=True)
    icono = models.CharField(max_length=64, blank=True, default="", help_text="Nombre del ícono (ej. 'Dumbbell')")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        indexes = [models.Index(fields=["empresa", "nombre"])]

    def __str__(self):
        return self.nombre


class Beneficio(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="beneficios", verbose_name="Empresa")
    nombre = models.CharField("Nombre del beneficio", max_length=255)
    descripcion = models.TextField("Descripción", blank=True)
    tipo_descuento = models.CharField("Tipo de descuento", max_length=50, blank=True)  # p.ej. porcentaje/monto
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    unidad = models.IntegerField("Unidad", default=0, help_text="Uso libre; 0 si no aplica")

    class Meta:
        verbose_name = "Beneficio"
        verbose_name_plural = "Beneficios"
        indexes = [models.Index(fields=["empresa", "nombre"])]

    def __str__(self):
        return self.nombre


# === Relación Plan – Servicio ===
class PlanServicio(TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="servicios_incluidos", verbose_name="Plan")
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name="en_planes", verbose_name="Servicio")
    precio = models.DecimalField("Precio", max_digits=10, decimal_places=2, default=0)
    icono = models.CharField("Icono", max_length=120, blank=True)
    fecha_baja = models.DateTimeField("Fecha de baja", null=True, blank=True)

    class Meta:
        verbose_name = "Servicio del plan"
        verbose_name_plural = "Servicios del plan"
        unique_together = ("plan", "servicio")
        indexes = [models.Index(fields=["plan", "servicio"])]

    def __str__(self):
        return f"{self.plan} - {self.servicio}"


# === Relación Plan – Beneficio ===
class PlanBeneficio(TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="beneficios_incluidos", verbose_name="Plan")
    beneficio = models.ForeignKey(Beneficio, on_delete=models.PROTECT, related_name="en_planes", verbose_name="Beneficio")
    vigencia_inicio = models.DateTimeField("Vigencia inicio", null=True, blank=True)
    vigencia_fin = models.DateTimeField("Vigencia fin", null=True, blank=True)

    class Meta:
        verbose_name = "Beneficio del plan"
        verbose_name_plural = "Beneficios del plan"
        unique_together = ("plan", "beneficio")
        indexes = [models.Index(fields=["plan", "beneficio"])]

    def __str__(self):
        return f"{self.plan} - {self.beneficio}"


# === Disciplinas ===
class Disciplina(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="disciplinas", verbose_name="Empresa")
    nombre = models.CharField("Nombre", max_length=255)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="disciplinas_impartidas", verbose_name="Instructor"
    )
    limite_personas = models.IntegerField("Límite de personas", default=0, help_text="0 = sin límite")
    recomendaciones = models.TextField("Recomendaciones", blank=True)

    class Meta:
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"
        indexes = [models.Index(fields=["empresa", "nombre"])]

    def __str__(self):
        return self.nombre


class DisciplinaPlan(TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="disciplinas", verbose_name="Plan")
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, related_name="en_planes", verbose_name="Disciplina")
    tipo_acceso = models.CharField("Tipo de acceso", max_length=50, blank=True)  # 'ilimitado', 'bolsa', etc.
    numero_accesos = models.IntegerField("Número de accesos", default=0)

    class Meta:
        verbose_name = "Disciplina por plan"
        verbose_name_plural = "Disciplinas por plan"
        unique_together = ("plan", "disciplina")
        indexes = [models.Index(fields=["plan", "disciplina"])]

    def __str__(self):
        return f"{self.plan} - {self.disciplina}"


class HorarioDisciplina(TimeStampedModel):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="horarios", verbose_name="Disciplina")
    hora_inicio = models.TimeField("Hora inicio")
    hora_fin = models.TimeField("Hora fin")

    class Meta:
        verbose_name = "Horario de disciplina"
        verbose_name_plural = "Horarios de disciplina"
        indexes = [models.Index(fields=["disciplina", "hora_inicio", "hora_fin"])]

    def __str__(self):
        return f"{self.disciplina} [{self.hora_inicio}-{self.hora_fin}]"


# === Alta de plan a cliente ===
class AltaPlan(TimeStampedModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="altas_plan", verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name="altas_plan", verbose_name="Sucursal")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="altas_plan", verbose_name="Cliente")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="altas", verbose_name="Plan")
    fecha_alta = models.DateField("Fecha de alta")
    fecha_vencimiento = models.DateField("Fecha de vencimiento", null=True, blank=True)
    renovacion = models.BooleanField("Renovación automática", default=False)

    class Meta:
        verbose_name = "Alta de plan"
        verbose_name_plural = "Altas de plan"
        indexes = [models.Index(fields=["empresa", "sucursal", "cliente", "plan"])]

    def __str__(self):
        return f"{self.cliente} -> {self.plan} ({self.fecha_alta})"


# === Accesos ===
class Acceso(TimeStampedModel):
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="accesos", verbose_name="Cliente")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="accesos", verbose_name="Empresa")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name="accesos", verbose_name="Sucursal")
    tipo_acceso = models.CharField("Tipo de acceso", max_length=20)  # 'entrada' / 'salida'
    puerta = models.CharField("Puerta", max_length=120, blank=True)
    temperatura = models.FloatField("Temperatura", null=True, blank=True)
    fecha = models.DateTimeField("Fecha/Hora de acceso")

    class Meta:
        verbose_name = "Acceso"
        verbose_name_plural = "Accesos"
        indexes = [models.Index(fields=["empresa", "sucursal", "cliente", "fecha"])]

    def __str__(self):
        return f"{self.cliente} {self.tipo_acceso} {self.fecha}"
      
class ServicioBeneficio(TimeStampedModel):
    """
    Relación independiente entre un Servicio y un Beneficio.
    Permite n beneficios por servicio, con vigencia opcional.
    """
    servicio = models.ForeignKey(
        "planes.Servicio",  # ajusta al app_label real
        on_delete=models.CASCADE,
        related_name="beneficios_rel"
    )
    beneficio = models.ForeignKey(
        "planes.Beneficio",  # ajusta al app_label real
        on_delete=models.CASCADE,
        related_name="servicios_rel"
    )
    vigencia_inicio = models.DateField(null=True, blank=True)
    vigencia_fin = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="servicio_beneficio_responsables"
    )

    class Meta:
        verbose_name = "Beneficio de servicio"
        verbose_name_plural = "Beneficios de servicio"
        unique_together = ("servicio", "beneficio")  # evita duplicados

    def clean(self):
        # Validación: servicio.empresa == beneficio.empresa
        if self.servicio_id and self.beneficio_id:
            s_emp = getattr(self.servicio, "empresa_id", None)
            b_emp = getattr(self.beneficio, "empresa_id", None)
            if s_emp and b_emp and s_emp != b_emp:
                from django.core.exceptions import ValidationError
                raise ValidationError("El beneficio y el servicio deben pertenecer a la misma empresa.")

    def __str__(self):
        return f"{self.servicio} ↔ {self.beneficio}"