from django.db import models
from django.conf import settings
from core.models import TimeStampedModel  # tu clase base con auditoría

class Almacen(TimeStampedModel):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='almacenes')
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        unique_together = ('empresa', 'nombre')
        indexes = [models.Index(fields=['empresa', 'nombre'])]

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
