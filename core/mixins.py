from empleados.models import UsuarioEmpresa

class CompanyScopedQuerysetMixin:
    """
    Limita los querysets a la(s) empresa(s) del usuario.
    Requiere que el modelo tenga un FK llamado 'empresa' o que el viewset
    defina 'company_fk_name' para indicar el nombre real del FK.
    """
    company_fk_name = "empresa"

    def get_user_companies(self):
        return self.request.user.asignaciones_empresa.values_list("empresa_id", flat=True)

    def filter_queryset_by_company(self, qs):
        companies = list(self.get_user_companies())
        if not companies:
            return qs.none()
        fk = self.company_fk_name
        if fk in [f.name for f in qs.model._meta.get_fields()]:
            return qs.filter(**{f"{fk}_id__in": companies})
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_queryset_by_company(qs)
