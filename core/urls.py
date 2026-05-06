from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
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
]
