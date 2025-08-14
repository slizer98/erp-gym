# core/permissions.py (ejemplo)
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAuthenticatedInCompany(BasePermission):
    """
    Requiere usuario autenticado y con al menos una asignación en UsuarioEmpresa.
    Puedes extenderla para validar empresa/sucursal específica por request.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.asignaciones_empresa.exists())


ROLE_OWNER = 'owner'
ROLE_MANAGER = 'gerente'
ROLE_RECEP = 'recepcionista'
ROLE_ACCOUNTING = 'contabilidad'
ROLE_AUDITOR = 'auditor'

# Helper: obtiene rol normalizado desde request (perfil/empresa)
def get_role(request):
    # ej: request.user.perfil.rol en la empresa; devuelve str minúsculas
    try:
        return (request.user.perfil.rol or '').lower()
    except:
        return ''

def is_superuser(request):
    return bool(getattr(request.user, 'is_superuser', False))

class CanAccessERP(BasePermission):
    """
    Evalúa permisos por view.action y rol.
    Se usa en tus ViewSets.
    """

    def has_permission(self, request, view):
        if is_superuser(request):
            return True

        role = get_role(request)
        action = getattr(view, 'action', None)  # list, retrieve, create, update, partial_update, destroy

        # Mapa por recurso
        view_name = view.__class__.__name__.lower()

        # Defaults de solo lectura
        if request.method in SAFE_METHODS:
            return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP, ROLE_ACCOUNTING, ROLE_AUDITOR}

        # Clientes y subrecursos
        if 'cliente' in view_name and 'caracteristica' not in view_name:
            if action in {'create', 'update', 'partial_update'}:
                return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP}
            if action == 'destroy':
                # hard-delete: restringe
                return role in {ROLE_OWNER, ROLE_MANAGER}
            return True

        # Datos fiscales: recep+contab+manager/owner
        if 'datosfiscales' in view_name:
            if action in {'create', 'update', 'partial_update'}:
                return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP, ROLE_ACCOUNTING}
            if action == 'destroy':
                return role in {ROLE_OWNER, ROLE_MANAGER}
            return True

        # Planes / precios / restricciones
        if 'plan' in view_name:
            if action in {'create', 'update', 'partial_update'}:
                return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP}
            if action == 'destroy':
                return role in {ROLE_OWNER, ROLE_MANAGER}
            return True

        # Configuraciones y Usuarios empresa
        if 'configuracion' in view_name or 'usuariosempresa' in view_name:
            if action in {'create', 'update', 'partial_update', 'destroy'}:
                return role in {ROLE_OWNER, ROLE_MANAGER}
            return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_ACCOUNTING, ROLE_AUDITOR}

        # Características (catálogo empresa)
        if 'caracteristica' in view_name:
            if action in {'create', 'update', 'partial_update', 'destroy'}:
                return role in {ROLE_OWNER, ROLE_MANAGER}
            return True

        # Convenios / DatosAdicionales / ClienteSucursal
        if any(k in view_name for k in ['convenio','datoadicional','clientesucursal','datocontacto']):
            if action in {'create','update','partial_update'}:
                return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP}
            if action == 'destroy':
                return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP}  # puedes restringir a manager+
            return True

        # Fallback: lectura para todos los roles internos
        return role in {ROLE_OWNER, ROLE_MANAGER, ROLE_RECEP, ROLE_ACCOUNTING, ROLE_AUDITOR}
