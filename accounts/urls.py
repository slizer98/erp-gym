# accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PerfilView, UsuarioViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='accounts-usuarios')

urlpatterns = [
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('', include(router.urls)),
]
