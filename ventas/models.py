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
      

class Venta(TimeStampedModel):
    # class MetodoPago(models.TextChoices):
    #     EFECTIVO = 'efectivo', 'Efectivo'
    #     TARJETA  = 'tarjeta', 'Tarjeta'
    #     TRANSFER = 'transferencia', 'Transferencia'
    #     MIXTO    = 'mixto', 'Mixto'

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ventas')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='compras')
    importe = models.DecimalField(max_digits=12, decimal_places=2)

    folio        = models.CharField(max_length=30, blank=True, null=True)                 # VTA-202510-...
    fecha        = models.DateTimeField()                                                 # fecha_hora
    sucursal     = models.ForeignKey('empresas.Sucursal', on_delete=models.PROTECT,
                                     related_name='ventas', null=True, blank=True)        # sucursal_id
    usuario      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas_capturadas', null=True, blank=True)  # usuario_id (cajero/asesor)
    cliente      = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='compras')                              # cliente_id
    tipo_venta   = models.CharField(max_length=60,null=True, blank=True )                              # PLAN / PRODUCTO / MIXTO
    # metodo_pago  = models.CharField(max_length=20, choices=MetodoPago.choices)

    # Totales (según encabezados: subtotal, descuento_monto, impuesto_monto, total)
    subtotal        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento_monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto_monto  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Otros campos de la tabla
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)             # referencia_pa
    notas           = models.TextField(blank=True, null=True)
    procesado       = models.BooleanField(default=False)                                  # 0/1
    uso_cfdi        = models.CharField(max_length=10, blank=True, null=True)              # G01, etc.
    uuid_cfdi       = models.CharField(max_length=40, blank=True, null=True)
    serie           = models.CharField(max_length=20, blank=True, null=True)
    folio_fiscal    = models.CharField(max_length=50, blank=True, null=True)


    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['folio']),
            models.Index(fields=['sucursal']),
        ]

    def __str__(self):
        return f'Venta #{self.id or "—"} {self.folio or ""} - {self.total:.2f}'


class MetodoPago(TimeStampedModel):
    """Pagos recibidos de una venta: SOLO venta_id, forma_pago_id, importe."""
    venta      = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE, related_name='pagos')
    forma_pago = models.CharField(max_length=30, blank=True, null=True)
    importe    = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['venta']),
        ]

    def __str__(self):
        return f'Pago {self.forma_pago} ${self.importe} de venta {self.venta_id}'


class DetalleVenta(TimeStampedModel):
    class ItemTipo(models.TextChoices):
        PLAN     = 'PLAN', 'PLAN'
        PRODUCTO = 'PRODUCTO', 'PRODUCTO'

    class Periodicidad(models.TextChoices):
        DIARIO   = 'DIARIO', 'DIARIO'
        SEMANAL  = 'SEMANAL', 'SEMANAL'
        QUINCENAL= 'QUINCENAL', 'QUINCENAL'
        MENSUAL  = 'MENSUAL', 'MENSUAL'
        ANUAL    = 'ANUAL', 'ANUAL'

    venta    = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE, related_name='detalles')

    # Identificación del renglón (encabezado: item_tipo, item_id, descripcion)
    item_tipo   = models.CharField(max_length=12, choices=ItemTipo.choices, null=True, blank=True)
    item_id     = models.IntegerField(null=True, blank=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)                                        # texto que ves en la tabla

    # FKs opcionales (uno u otro según item_tipo)
    plan     = models.ForeignKey('planes.Plan', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='detalles_venta')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='detalles_venta')

    codigo_descuento = models.ForeignKey('ventas.CodigoDescuento', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='detalles_venta')

    cantidad        = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)     # precio_unitari

    # Totales por renglón (encabezados: descuento_m, impuesto_pct, impuesto_mo, subtotal, total)
    descuento_monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto_pct    = models.DecimalField(max_digits=5,  decimal_places=2, default=0)     # ej. 16.00
    impuesto_monto  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Campos específicos cuando el item es un PLAN
    plan_inicio  = models.DateField(null=True, blank=True)
    plan_fin     = models.DateField(null=True, blank=True)
    periodicidad = models.CharField(max_length=12, choices=Periodicidad.choices,
                                    null=True, blank=True)

    # Campo específico cuando es PRODUCTO
    almacen      = models.ForeignKey('inventario.Almacen', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='detalles_venta')  # almacen_id

    class Meta:
        indexes = [
            models.Index(fields=['venta']),
            models.Index(fields=['item_tipo']),
        ]

    def __str__(self):
        return f'Detalle #{self.id} - {self.item_tipo} x{self.cantidad}'
