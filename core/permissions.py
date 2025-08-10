from rest_framework.permissions import BasePermission

class IsAuthenticatedInCompany(BasePermission):
    """
    Requiere usuario autenticado y con al menos una asignación en UsuarioEmpresa.
    Puedes extenderla para validar empresa/sucursal específica por request.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.asignaciones_empresa.exists())
