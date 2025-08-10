from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    # Campos extra en el formulario del admin
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Datos laborales", {
            "fields": (
                "empresa", "cargo", "dias_trabajo",
                "horario_entrada", "horario_salida",
                "fecha_contratacion",
            )
        }),
        ("Datos personales/Contacto", {
            "fields": (
                "telefono", "fecha_nacimiento", "numero_seguro",
                "codigo_postal", "domicilio", "notas",
            )
        }),
    )

    list_display = (
        "id", "username", "email", "first_name", "last_name",
        "empresa", "cargo", "is_active"
    )
    list_filter = ("is_active", "empresa")
    search_fields = (
        "username", "email", "first_name", "last_name",
        "telefono", "numero_seguro", "cargo"
    )
