from django.urls import path
from . import views

app_name = "facturacion"

urlpatterns = [
    path("", views.FacturaListView.as_view(), name="list"),
    path("crear/", views.FacturaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.FacturaDetailView.as_view(), name="detalle"),
    path("<int:pk>/imprimir/", views.imprimir_factura, name="imprimir"),
    path("<int:pk>/eliminar/", views.FacturaDeleteView.as_view(), name="eliminar"),
    path("cierre-caja/", views.CierreCajaView.as_view(), name="cierre_caja"),
]
