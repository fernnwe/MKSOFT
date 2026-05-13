from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from . import views

app_name = "core"


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health"),
    path("", views.LandingView.as_view(), name="landing"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("cliente/login/", views.ClienteLoginView.as_view(), name="cliente_login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/crear/", views.UsuarioCreateView.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/", views.UsuarioDetailView.as_view(), name="usuario_detalle"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.UsuarioDeleteView.as_view(), name="usuario_eliminar"),
    path("usuarios/<int:pk>/reset-password/", views.UsuarioResetPasswordView.as_view(), name="usuario_reset_password"),
    path("usuarios/mi-password/", views.CambiarPasswordView.as_view(), name="cambiar_password"),
    path("permisos-meseros/", views.PermisosMeserosView.as_view(), name="permisos_meseros"),
    path("permisos-meseros/<int:pk>/actualizar/", views.ActualizarPermisosView.as_view(), name="actualizar_permisos"),
    path("configuracion/", views.ConfigRestauranteView.as_view(), name="config_restaurante"),
    path("configuracion/restablecer/", views.RestablecerFabricaView.as_view(), name="restablecer_fabrica"),
    path("configuracion/restaurar-respaldo/", views.RestaurarUltimoRespaldoView.as_view(), name="restaurar_ultimo_respaldo"),
    path("superadmin/", views.SuperAdminListView.as_view(), name="superadmin_dashboard"),
    path("superadmin/cliente/crear/", views.ClienteCreateView.as_view(), name="superadmin_cliente_crear"),
    path("superadmin/cliente/<int:pk>/", views.ClienteDetailView.as_view(), name="superadmin_cliente_detalle"),
    path("superadmin/cliente/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="superadmin_cliente_editar"),
    path("superadmin/cliente/<int:pk>/pago/", views.ClienteRegistrarPagoView.as_view(), name="superadmin_registrar_pago"),
    path("superadmin/cliente/<int:pk>/cancelar/", views.ClienteCancelarView.as_view(), name="superadmin_cliente_cancelar"),
    path("superadmin/cliente/<int:pk>/reactivar/", views.ClienteReactivarView.as_view(), name="superadmin_cliente_reactivar"),
    path("superadmin/cliente/<int:pk>/reset-password/", views.ClienteResetPasswordView.as_view(), name="superadmin_cliente_reset_password"),
    path("superadmin/cliente/<int:pk>/eliminar/", views.ClienteDeleteView.as_view(), name="superadmin_cliente_eliminar"),
    path("superadmin/cliente/<int:pk>/extender/", views.ClienteExtendView.as_view(), name="superadmin_cliente_extender"),
    path("suscripcion-vencida/", views.SuscripcionVencidaView.as_view(), name="suscripcion_vencida"),
    path("superadmin/cliente/<int:pk>/suspender/", views.ClienteSuspendView.as_view(), name="superadmin_cliente_suspender"),
    path("superadmin/cliente/<int:pk>/enviar-credenciales/", views.ClienteEnviarCredencialesView.as_view(), name="superadmin_enviar_credenciales"),
]
