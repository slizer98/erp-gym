from rest_framework import serializers
from .models import Cliente,DatoContacto, DatosFiscales, Convenio,Caracteristica, DatoAdicional, ClienteSucursal

class ClienteSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.get_full_name", read_only=True)
    
    avatar = serializers.ImageField(required=False, allow_null=True)

    # URL absoluta para el front (solo lectura)
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id", "nombre", "apellidos", "fecha_nacimiento",
            "contacto_emergencia", "email", "factura", "observaciones",
            "recordar_vencimiento", "recibo_pago", "recibir_promociones",
            "genero", "usuario", "usuario_nombre", "avatar",       # <-- imagen
            "avatar_url",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
        
    def get_avatar_url(self, obj):
        req = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return req.build_absolute_uri(obj.avatar.url) if req else obj.avatar.url
        return None


class DatoContactoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)

    class Meta:
        model = DatoContacto
        fields = [
            "id", "cliente", "cliente_nombre", "tipo", "valor",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class DatosFiscalesSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)

    class Meta:
        model = DatosFiscales
        fields = [
            "id", "cliente", "cliente_nombre",
            "rfc", "razon_social", "persona", "codigo_postal", "regimen_fiscal",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class ConvenioSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Convenio
        fields = [
            "id","cliente","cliente_nombre","empresa","empresa_nombre",
            "empresa_convenio","telefono_oficina","medio_entero","tipo_cliente",
            "is_active","created_at","updated_at","created_by","updated_by",
        ]
        read_only_fields = ("empresa","created_at","updated_at","created_by","updated_by")


class CaracteristicaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Caracteristica
        fields = [
            "id", "empresa", "empresa_nombre",
            "nombre", "tipo_dato",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class DatoAdicionalSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)
    caracteristica_nombre = serializers.CharField(source="caracteristica.nombre", read_only=True)

    class Meta:
        model = DatoAdicional
        fields = [
            "id", "cliente", "cliente_nombre",
            "caracteristica", "caracteristica_nombre",
            "campo", "valor",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class ClienteSucursalSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.__str__", read_only=True)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = ClienteSucursal
        fields = [
            "id", "cliente", "cliente_nombre",
            "sucursal", "sucursal_nombre",
            "empresa", "empresa_nombre",
            "fecha_inicio", "fecha_fin",
            "is_active", "created_at", "updated_at", "created_by", "updated_by",
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
        
    def validate(self, attrs):
        sucursal = attrs.get("sucursal") or getattr(self.instance, "sucursal", None)
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        if sucursal and empresa:
            # Asegurar que la sucursal pertenece a la misma empresa
            if sucursal.empresa_id != empresa.id:
                raise serializers.ValidationError("La sucursal no pertenece a la empresa seleccionada.")
        return attrs