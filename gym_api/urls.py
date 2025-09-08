


from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("core.urls")),  
        # Prefijos por dominio (API v1)
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/", include("empresas.urls")),
    path("api/v1/", include("clientes.urls_sub")),
    path("api/v1/", include("clientes.urls")),
    path("api/v1/", include("empleados.urls")),
    path("api/v1/", include("planes.urls")),
    path("api/v1/", include("ventas.urls")),
    path("api/v1/inventario/", include("inventario.urls")),
    path("api/v1/", include("finanzas.urls")),
    path("api/v1/", include("accesos.urls")),
]
