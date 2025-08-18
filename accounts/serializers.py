from rest_framework import serializers
from django.conf import settings
from empleados.models import UsuarioEmpresa
from .models import Usuario


class AsignacionEmpresaSerializer(serializers.ModelSerializer):
    empresa_id = serializers.IntegerField(source="empresa.id", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    sucursal_id = serializers.IntegerField(source="sucursal.id", read_only=True, default=None)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True, default=None)

    class Meta:
        model = UsuarioEmpresa
        fields = [
            "id",
            "empresa_id", "empresa_nombre",
            "sucursal_id", "sucursal_nombre",
            "rol", "permisos", "is_active",
        ]


class UsuarioPerfilSerializer(serializers.ModelSerializer):
    # Campos del usuario
    nombre = serializers.CharField(source="first_name", read_only=True)
    apellido = serializers.CharField(source="last_name", read_only=True)
    telefono = serializers.CharField(read_only=True)
    cargo = serializers.CharField(read_only=True)
    fecha_contratacion = serializers.DateField(read_only=True)
    ultimo_acceso = serializers.DateTimeField(source="last_login", read_only=True)

    # Todas las asignaciones del usuario
    asignaciones = AsignacionEmpresaSerializer(
        source="asignaciones_empresa", many=True, read_only=True
    )

    # Asignación activa (calculada en la vista y pasada vía context)
    empresa_activa = serializers.SerializerMethodField()
    sucursal_activa = serializers.SerializerMethodField()
    rol_activo = serializers.SerializerMethodField()
    permisos_activos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "email",
            "nombre", "apellido", "telefono",
            "cargo", "fecha_contratacion", "ultimo_acceso",
            "is_staff", "is_superuser",
            "asignaciones",
            "empresa_activa", "sucursal_activa",
            "rol_activo", "permisos_activos",
        ]

    def _get_active_assignment(self, obj):
        """La vista puede inyectar 'asignacion_activa' en context; si no, toma la primera."""
        asignacion = self.context.get("asignacion_activa")
        if asignacion is None:
            asignaciones = getattr(obj, "prefetch_asignaciones", None) or obj.asignaciones_empresa.all()
            asignacion = next((a for a in asignaciones if a.is_active), None) or (asignaciones[0] if asignaciones else None)
        return asignacion

    def get_empresa_activa(self, obj):
        a = self._get_active_assignment(obj)
        if not a:
            return None
        return {"id": a.empresa_id, "nombre": a.empresa.nombre}

    def get_sucursal_activa(self, obj):
        a = self._get_active_assignment(obj)
        if not a or not a.sucursal:
            return None
        return {"id": a.sucursal_id, "nombre": a.sucursal.nombre}

    def get_rol_activo(self, obj):
        a = self._get_active_assignment(obj)
        return a.rol if a else None

    def get_permisos_activos(self, obj):
        a = self._get_active_assignment(obj)
        return a.permisos if a and a.permisos is not None else {}



from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from empresas.models import Empresa

Usuario = get_user_model()

class UsuarioListSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    nombre = serializers.CharField(source='first_name', required=False)
    apellido = serializers.CharField(source='last_name', required=False)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email',
            'nombre', 'apellido',
            'empresa', 'empresa_nombre',
            'cargo','dias_trabajo','horario_entrada','horario_salida','fecha_contratacion',
            'codigo_postal','telefono','fecha_nacimiento','numero_seguro','domicilio','notas',
            'is_active','is_staff','is_superuser','last_login','date_joined'
        ]
        read_only_fields = ('is_superuser','last_login','date_joined')

class UsuarioCreateUpdateSerializer(serializers.ModelSerializer):
    # alias amigables
    nombre = serializers.CharField(source='first_name', required=False, allow_blank=True)
    apellido = serializers.CharField(source='last_name', required=False, allow_blank=True)

    # password write-only; en update puedes mandar new_password
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id','username','email','password','new_password',
            'nombre','apellido',
            'empresa','empresa_nombre',
            'cargo','dias_trabajo','horario_entrada','horario_salida','fecha_contratacion',
            'codigo_postal','telefono','fecha_nacimiento','numero_seguro','domicilio','notas',
            'is_active','is_staff', 'is_superuser'
        ]
        read_only_fields = ('is_superuser',)  # solo superuser podrá setearlo desde la vista

    def validate_password(self, value):
        # Aplica validadores de Django (opcional; puedes desactivarlo si no los usas)
        validate_password(value)
        return value

    def validate(self, attrs):
        # Si no mandan empresa, y existe header X-Empresa-Id, la inyectamos en la view (perform_create)
        return attrs

    def create(self, validated_data):
        # `password` viene en validated_data; set_password para hashear
        password = validated_data.pop('password')
        new_password = validated_data.pop('new_password', None)  # ignorar en create
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        # No sobrescribas password directamente
        password = validated_data.pop('password', None)  # en update no lo usamos
        new_password = validated_data.pop('new_password', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if new_password:
            validate_password(new_password)
            instance.set_password(new_password)

        instance.save()
        return instance
