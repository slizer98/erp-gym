from django.urls import path
from .views import PerfilView   # <- antes importabas 'perfil'

urlpatterns = [
    path("perfil/", PerfilView.as_view(), name="perfil"),
]