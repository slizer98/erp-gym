from django.db import models
from django.conf import settings
from core.models import TimeStampedModel  # clase base con auditoría
from django.core.exceptions import ValidationError

class Almacen(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='almacenes')
    sucursal = models.ForeignKey('empresas.Sucursal', on_delete=models.CASCADE, related_name='almacenes', null=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        unique_together = ('empresa', 'sucursal', 'nombre')
        indexes = [
            models.Index(fields=['empresa', 'sucursal', 'nombre']),
            models.Index(fields=['sucursal', 'nombre']),
        ]
    def clean(self):
        if self.sucursal and self.empresa_id != self.sucursal.empresa_id:
            raise ValidationError("La sucursal no pertenece a la empresa seleccionada.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


    def __str__(self):
        return f'{self.nombre} (emp:{self.empresa_id})'


class CategoriaProducto(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='categorias_producto')
    nombre = models.CharField(max_length=255)

    class Meta:
        unique_together = ('empresa', 'nombre')
        indexes = [models.Index(fields=['empresa', 'nombre'])]

    def __str__(self):
        return self.nombre


class Producto(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey('inventario.CategoriaProducto', on_delete=models.PROTECT, related_name='productos')
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')
    codigo_barras = models.CharField(max_length=64, blank=True, default='')
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aplicar_iva = models.BooleanField("Aplicar IVA (16%)", default=True)
    aplicar_ieps = models.BooleanField("Aplicar IEPS (8%)", default=False)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = (('empresa', 'nombre'),)
        constraints = [
            # Único por empresa cuando no esté vacío
            models.UniqueConstraint(
                fields=['empresa', 'codigo_barras'],
                name='uniq_producto_codigo_barras_por_empresa',
                condition=~models.Q(codigo_barras='')
            )
        ]
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
            models.Index(fields=['empresa', 'codigo_barras']),
        ]

    def __str__(self):
        return self.nombre


class MovimientoProducto(TimeStampedModel):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'    # alta
        SALIDA  = 'salida', 'Salida'      # baja
        AJUSTE  = 'ajuste', 'Ajuste'      # modificación

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='movimientos_productos')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.CASCADE, related_name='movimientos')
    almacen = models.ForeignKey('inventario.Almacen', on_delete=models.PROTECT, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'producto']),
            models.Index(fields=['fecha']),
        ]
