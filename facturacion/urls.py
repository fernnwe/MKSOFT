from django.urls import path
from . import views

app_name = "facturacion"

urlpatterns = [
    path("", views.FacturaListView.as_view(), name="list"),
    path("crear/", views.FacturaCreateView.as_view(), name="crear"),
    path("crear-llevar/", views.FacturaLlevarCreateView.as_view(), name="crear_llevar"),
    path("<int:pk>/", views.FacturaDetailView.as_view(), name="detalle"),
    path("<int:pk>/imprimir/", views.imprimir_factura, name="imprimir"),
    path("<int:pk>/escpos/", views.factura_escpos, name="escpos"),
    path("<int:pk>/escpos-tcp/", views.factura_escpos_tcp, name="escpos_tcp"),
    path("<int:pk>/eliminar/", views.FacturaDeleteView.as_view(), name="eliminar"),
    path("apertura/", views.AperturaCajaView.as_view(), name="apertura"),
    path("cierre-caja/", views.CierreCajaView.as_view(), name="cierre_caja"),
    path("cierre-caja/confirmar/", views.CierreCajaConfirmView.as_view(), name="cierre_confirm"),
    path("cierre-caja/exitoso/", views.CierreExitosoView.as_view(), name="cierre_exitoso"),
    path("cierre-caja/ticket/", views.CierreTicketView.as_view(), name="cierre_ticket"),
    path("cierre-caja/escpos/", views.cierre_escpos, name="cierre_escpos"),
    path("cierre-caja/escpos-tcp/", views.cierre_escpos_tcp, name="cierre_escpos_tcp"),
    path("cierre-caja/pdf/", views.CierreCajaPdfView.as_view(), name="cierre_pdf"),
    path("cierres/historial/", views.HistorialCierresView.as_view(), name="historial_cierres"),
    path("caja/movimiento/", views.CajaMovimientoCreateView.as_view(), name="caja_movimiento"),
    path("excel/facturas/", views.facturas_export_excel, name="facturas_excel"),
]
