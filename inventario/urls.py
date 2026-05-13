from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.InventarioListView.as_view(), name="list"),
    path("ingredientes/crear/", views.IngredienteCreateView.as_view(), name="ingrediente_crear"),
    path("<int:pk>/editar/", views.InventarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.InventarioDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/movimiento/", views.registrar_movimiento, name="movimiento"),
    path("movimientos/", views.MovimientoListView.as_view(), name="movimientos"),
    path("compras/", views.CompraListView.as_view(), name="compras"),
    path("compras/crear/", views.CompraCreateView.as_view(), name="compra_crear"),
    path("api/ingredientes/", views.ingredientes_api, name="ingredientes_api"),
    path("compras/<int:pk>/", views.CompraDetailView.as_view(), name="compra_detalle"),
    path("compras/<int:pk>/recibir/", views.CompraRecibirView.as_view(), name="compra_recibir"),
    path("compras/<int:pk>/cancelar/", views.CompraCancelarView.as_view(), name="compra_cancelar"),
    path("compras/<int:pk>/eliminar/", views.CompraDeleteView.as_view(), name="compra_eliminar"),
    path("cuentas/", views.CuentaPorPagarListView.as_view(), name="cuentas"),
    path("cuentas/crear/", views.CuentaPorPagarCreateView.as_view(), name="cuenta_crear"),
    path("cuentas/<int:pk>/", views.CuentaPorPagarDetailView.as_view(), name="cuenta_detalle"),
    path("cuentas/<int:pk>/pago/", views.CuentaPorPagarPagoView.as_view(), name="cuenta_pago"),
    path("cuentas/<int:pk>/cancelar/", views.CuentaPorPagarCancelarView.as_view(), name="cuenta_cancelar"),
    path("cuentas/<int:pk>/eliminar/", views.CuentaPorPagarDeleteView.as_view(), name="cuenta_eliminar"),
    path("pdf/inventario/", views.inventario_pdf, name="inventario_pdf"),
    path("pdf/compras/", views.compras_pdf, name="compras_pdf"),
    path("proveedores/", views.ProveedorListView.as_view(), name="proveedores"),
    path("proveedores/crear/", views.ProveedorCreateView.as_view(), name="proveedor_crear"),
    path("proveedores/<int:pk>/editar/", views.ProveedorUpdateView.as_view(), name="proveedor_editar"),
    path("proveedores/<int:pk>/eliminar/", views.ProveedorDeleteView.as_view(), name="proveedor_eliminar"),
    path("excel/inventario/", views.inventario_export_excel, name="inventario_excel"),
    path("excel/compras/", views.compras_export_excel, name="compras_excel"),
]
