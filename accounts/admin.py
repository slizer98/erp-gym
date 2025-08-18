# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('id','username','email','first_name','last_name','empresa','is_staff','is_active','last_login')
    list_filter = ('is_staff','is_active','empresa')
    search_fields = ('username','email','first_name','last_name')
    ordering = ('-id',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información personal', {
            'fields': (
                'first_name','last_name','email','empresa','cargo','dias_trabajo',
                'horario_entrada','horario_salida','fecha_contratacion',
                'codigo_postal','telefono','fecha_nacimiento','numero_seguro',
                'domicilio','notas'
            )
        }),
        ('Permisos', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login','date_joined')}),
    )
