from django.urls import path
from . import views

app_name = "facturacion"

urlpatterns = [
    path("", views.FacturaListView.as_view(), name="list"),
    path("crear/", views.FacturaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.FacturaDetailView.as_view(), name="detalle"),
    path("<int:pk>/imprimir/", views.imprimir_factura, name="imprimir"),
    path("<int:pk>/eliminar/", views.FacturaDeleteView.as_view(), name="eliminar"),
    path("apertura/", views.AperturaCajaView.as_view(), name="apertura"),
    path("cierre-caja/", views.CierreCajaView.as_view(), name="cierre_caja"),
    path("cierre-caja/confirmar/", views.CierreCajaConfirmView.as_view(), name="cierre_confirm"),
    path("cierre-caja/exitoso/", views.CierreExitosoView.as_view(), name="cierre_exitoso"),
    path("cierre-caja/pdf/", views.CierreCajaPdfView.as_view(), name="cierre_pdf"),
    path("cierres/historial/", views.HistorialCierresView.as_view(), name="historial_cierres"),
]
