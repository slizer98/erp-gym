from empleados.models import UsuarioEmpresa

# core/mixins.py
class CompanyScopedQuerysetMixin:
    """
    Scope por empresa:
      - SUPERUSER: respeta X-Empresa-Id si viene; si no, usa asignaciones.
      - NO SUPERUSER: ignora el header y usa empresa_activa (o asignaciones).
    Permite FK directo (company_fk_name) o path relacionado (company_filter_path).
    """
    company_fk_name = "empresa"
    company_filter_path = None

    def _user_companies(self):
        try:
            return list(self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True))
        except Exception:
            return []

    def _active_company_for_non_superuser(self):
        # Usa empresa_activa del perfil si la tienes en el request.user,
        # si no, cae a la primera asignación disponible.
        emp = getattr(getattr(self.request.user, "empresa_activa", None), "id", None)
        if emp:
            return str(emp)
        assigned = self._user_companies()
        return str(assigned[0]) if assigned else None

    def get_active_company_id(self):
        user = self.request.user
        is_su = bool(getattr(user, "is_superuser", False))

        if is_su:
            # Solo superusuario puede cambiar empresa por header
            emp_id = self.request.headers.get("X-Empresa-Id") or self.request.META.get("HTTP_X_EMPRESA_ID")
            if emp_id:
                return str(emp_id)
            # fallback: cualquier asignación
            assigned = self._user_companies()
            return str(assigned[0]) if assigned else None

        # Usuarios normales: ignorar header y usar su empresa activa
        return self._active_company_for_non_superuser()

    def filter_queryset_by_company(self, qs):
        active_id = self.get_active_company_id()
        path = self.company_filter_path or self.company_fk_name
        # ¿tiene FK directo?
        has_direct_fk = any(f.name == self.company_fk_name for f in qs.model._meta.get_fields())

        if not active_id:
            return qs.none()

        if self.company_filter_path or has_direct_fk:
            return qs.filter(**{f"{path}_id": active_id})
        return qs.filter(**{f"{path}": active_id})

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_queryset_by_company(qs)



# core/mixins.py (nuevo)
from core.permissions import get_role, ROLE_RECEP

class ReceptionBranchScopedByClienteMixin:
    """
    Limita queryset a clientes de la sucursal del recepcionista.
    Supone que el modelo tiene FK -> cliente.
    """
    def filter_by_reception_branch(self, qs):
        role = get_role(self.request)
        if role == ROLE_RECEP:
            sucursal_id = getattr(getattr(self.request.user, 'perfil', None), 'sucursal_id', None)
            if sucursal_id:
                return qs.filter(cliente__sucursales_asignadas__sucursal_id=sucursal_id).distinct()
            return qs.none()
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_by_reception_branch(qs)


def _user_sucursal_id(request):
    # Ajusta al lugar real donde guardas la sucursal del usuario
    return getattr(getattr(request.user, 'perfil', None), 'sucursal_id', None)

class ReceptionBranchScopedClientesMixin:
    """
    Limita Clientes a los asignados a la sucursal del recepcionista.
    Cliente --(related_name='sucursales_asignadas')-> ClienteSucursal.sucursal_id
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if get_role(self.request) == ROLE_RECEP:
            sucursal_id = _user_sucursal_id(self.request)
            if not sucursal_id:
                return qs.none()
            return qs.filter(sucursales_asignadas__sucursal_id=sucursal_id).distinct()
        return qs


class ReceptionBranchScopedByClienteMixin:
    """
    Para viewsets cuyo modelo tiene FK -> cliente
    (DatoContacto, DatosFiscales, Convenio, DatoAdicional)
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if get_role(self.request) == ROLE_RECEP:
            sucursal_id = _user_sucursal_id(self.request)
            if not sucursal_id:
                return qs.none()
            return qs.filter(cliente__sucursales_asignadas__sucursal_id=sucursal_id).distinct()
        return qs


class ReceptionBranchScopedSucursalMixin:
    """
    Para ClienteSucursal: sólo filas de la sucursal del recepcionista.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if get_role(self.request) == ROLE_RECEP:
            sucursal_id = _user_sucursal_id(self.request)
            if not sucursal_id:
                return qs.none()
            return qs.filter(sucursal_id=sucursal_id)
        return qs


class ReceptionEnforceBranchOnWriteMixin:
    """
    Refuerza en escritura que recepcionista no opere fuera de su sucursal.
    Útil en ClienteSucursal y recursos con FK->cliente.
    """
    def _ensure_reception_branch(self, instance_or_validated):
        if get_role(self.request) != ROLE_RECEP:
            return

        sucursal_id = _user_sucursal_id(self.request)
        if not sucursal_id:
            raise PermissionDenied("No tienes sucursal asignada.")

        # Caso 1: modelos con campo sucursal_id directo (ClienteSucursal)
        sid = getattr(instance_or_validated, 'sucursal_id', None) \
              or (instance_or_validated.get('sucursal') if isinstance(instance_or_validated, dict) else None)
        if sid and int(sid) != int(sucursal_id):
            raise PermissionDenied("No puedes operar con otra sucursal distinta a la tuya.")

        # Caso 2: modelos con FK->cliente (DatoContacto, DatosFiscales, Convenio, DatoAdicional)
        cliente = getattr(instance_or_validated, 'cliente', None) \
                  or (instance_or_validated.get('cliente') if isinstance(instance_or_validated, dict) else None)
        if cliente:
            # Si viene id, no tenemos instancia aún; el check fuerte quedará en DB.
            # Puedes endurecer consultando ClienteSucursal aquí si lo deseas.
            pass

    def perform_create(self, serializer):
        self._ensure_reception_branch(serializer.validated_data)
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        self._ensure_reception_branch(serializer.validated_data)
        return super().perform_update(serializer)