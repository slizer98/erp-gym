from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

class Proveedor(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='proveedores')
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=50, blank=True, default='')
    correo = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('empresa', 'nombre')
        indexes = [models.Index(fields=['empresa', 'nombre'])]

    def __str__(self):
        return self.nombre


class CategoriaEgreso(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='categorias_egresos')
    nombre = models.CharField(max_length=255)

    class Meta:
        unique_together = ('empresa', 'nombre')
        indexes = [models.Index(fields=['empresa', 'nombre'])]

    def __str__(self):
        return self.nombre


class Egreso(TimeStampedModel):
    class FormaPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA  = 'tarjeta', 'Tarjeta'
        TRANSFER = 'transferencia', 'Transferencia'
        CHEQUE   = 'cheque', 'Cheque'
        OTRO     = 'otro', 'Otro'

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='egresos')
    concepto = models.CharField(max_length=255)
    proveedor = models.ForeignKey('finanzas.Proveedor', on_delete=models.SET_NULL, null=True, related_name='egresos')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField()
    forma_pago = models.CharField(max_length=20, choices=FormaPago.choices)
    descripcion = models.TextField(blank=True, default='')
    sucursal = models.CharField(max_length=255, blank=True, default='')  # si tienes modelo Sucursal, cámbialo a FK
    categoria = models.ForeignKey('finanzas.CategoriaEgreso', on_delete=models.SET_NULL, null=True, related_name='egresos')

    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['empresa', 'categoria']),
            models.Index(fields=['empresa', 'proveedor']),
        ]
