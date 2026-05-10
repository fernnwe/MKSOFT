from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("mksoft-panel/", admin.site.urls),
    path("api/", include("comandas.api_urls")),
    path("", include("core.urls")),
    path("mesas/", include("mesas.urls")),
    path("meseros/", include("meseros.urls")),
    path("productos/", include("productos.urls")),
    path("comandas/", include("comandas.urls")),
    path("inventario/", include("inventario.urls")),
    path("facturacion/", include("facturacion.urls")),
    path("respaldos/", include("respaldos.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
