from django.contrib import admin
from .models import Empresa, Sucursal

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "rfc", "telefono", "correo", "is_active", "created_at", "updated_at")
    search_fields = ("nombre", "razon_social", "rfc", "correo", "telefono")
    list_filter = ("is_active",)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("id", "empresa", "nombre", "telefono", "correo", "horario_apertura", "horario_cierre", "is_active")
    search_fields = ("nombre", "correo", "telefono", "empresa__nombre")
    list_filter = ("empresa", "is_active")
