from rest_framework import serializers
from .models import Empresa, Sucursal
from .models import Configuracion, ValorConfiguracion
from datetime import datetime, date
import json
from decimal import Decimal, InvalidOperation

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            "id", "nombre", "razon_social", "rfc", "direccion",
            "telefono", "correo", "sitio_web",
            "is_active", "created_at", "updated_at",
            "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

class SucursalSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Sucursal
        fields = [
            "id", "empresa", "empresa_nombre", "nombre", "direccion",
            "telefono", "correo", "responsable",
            "horario_apertura", "horario_cierre",
            "is_active", "created_at", "updated_at",
            "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class ConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuracion
        fields = ["id", "nombre", "tipo_dato", "descripcion"]


class ValorConfiguracionSerializer(serializers.ModelSerializer):
    configuracion_nombre = serializers.CharField(source="configuracion.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = ValorConfiguracion
        fields = [
            "id",
            "configuracion", "configuracion_nombre",
            "empresa", "empresa_nombre",
            "valor",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate(self, attrs):
        """
        Valida que 'valor' cumpla el 'tipo_dato' de la configuración.
        """
        cfg = attrs.get("configuracion") or getattr(self.instance, "configuracion", None)
        val = attrs.get("valor") if "valor" in attrs else getattr(self.instance, "valor", None)

        if cfg and val is not None:
            tipo = (cfg.tipo_dato or "").strip().lower()
            try:
                if tipo in ("text", "string", "varchar"):
                    # nada que validar
                    pass
                elif tipo in ("int", "integer"):
                    int(val)
                elif tipo in ("decimal", "float", "number"):
                    Decimal(val)
                elif tipo in ("bool", "boolean"):
                    if str(val).lower() not in ("true", "false", "1", "0", "yes", "no", "si"):
                        raise serializers.ValidationError("Valor booleano inválido.")
                elif tipo in ("date",):
                    # formatos comunes: YYYY-MM-DD
                    date.fromisoformat(val)
                elif tipo in ("datetime", "timestamp"):
                    # formato común: YYYY-MM-DDTHH:MM:SS
                    # intenta ISO 8601
                    datetime.fromisoformat(val)
                elif tipo in ("json",):
                    json.loads(val)
                else:
                    # tipo no reconocido: lo aceptamos sin validar fuerte
                    pass
            except (ValueError, InvalidOperation, json.JSONDecodeError) as e:
                raise serializers.ValidationError(f"El valor no cumple con el tipo '{tipo}': {e}")
        return attrs