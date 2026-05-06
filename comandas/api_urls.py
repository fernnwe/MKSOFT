from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r"mesas", api_views.MesaViewSet, basename="mesa")
router.register(r"categorias", api_views.CategoriaViewSet, basename="categoria")
router.register(r"productos", api_views.ProductoViewSet, basename="producto")
router.register(r"comandas", api_views.ComandaViewSet, basename="comanda")
router.register(r"facturas", api_views.FacturaViewSet, basename="factura")

urlpatterns = [
    path("", include(router.urls)),
]
