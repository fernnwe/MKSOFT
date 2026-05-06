from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.InventarioListView.as_view(), name="list"),
    path("ingredientes/crear/", views.IngredienteCreateView.as_view(), name="ingrediente_crear"),
    path("crear/", views.InventarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.InventarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/movimiento/", views.registrar_movimiento, name="movimiento"),
    path("movimientos/", views.MovimientoListView.as_view(), name="movimientos"),
    path("compras/", views.CompraListView.as_view(), name="compras"),
    path("compras/crear/", views.CompraCreateView.as_view(), name="compra_crear"),
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
]
