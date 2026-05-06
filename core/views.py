from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.timezone import now, localtime
from django.db.models import Sum, Count, Q, F
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password
import string
import random
from django.http import HttpResponseForbidden
from inventario.models import Inventario
from mesas.models import Mesa
from comandas.models import Comanda
from facturacion.models import Factura
from .models import User, ConfigRestaurante


class PermissionRequiredMixin:
    permission = None

    def dispatch(self, request, *args, **kwargs):
        if self.permission and not request.user.has_perm(self.permission):
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("core:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo"] = True
        return context


class CustomLogoutView(LogoutView):
    next_page = "core:login"


def _generar_contrasena(longitud=10):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(longitud))


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get(self, request, *args, **kwargs):
        if not request.user.has_perm("can_view_dashboard"):
            if request.user.has_perm("can_view_cocina"):
                return redirect("comandas:cocina")
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["mesas_ocupadas"] = Mesa.objects.filter(estado=Mesa.Estado.OCUPADA).count()
        context["mesas_libres"] = Mesa.objects.filter(estado=Mesa.Estado.LIBRE).count()
        context["mesas_reservadas"] = Mesa.objects.filter(estado=Mesa.Estado.RESERVADA).count()
        context["mesas_total"] = Mesa.objects.count()

        context["comandas_hoy"] = Comanda.objects.count()
        context["comandas_abiertas"] = Comanda.objects.filter(estado=Comanda.Estado.ABIERTA).count()
        context["comandas_en_cocina"] = Comanda.objects.filter(estado=Comanda.Estado.EN_COCINA).count()
        context["comandas_cerradas"] = Comanda.objects.filter(estado=Comanda.Estado.CERRADA).count()

        todas_facturas = Factura.objects.filter(estado=Factura.Estado.PAGADA)
        facturas_result = todas_facturas.aggregate(
            total=Sum("total_con_impuestos"),
            count=Count("id")
        )
        context["ventas_total"] = facturas_result["total"] or 0
        context["facturas_total"] = facturas_result["count"] or 0

        facturas_mes = Factura.objects.filter(estado=Factura.Estado.PAGADA)
        ahora = localtime(now())
        facturas_mes = facturas_mes.filter(
            fecha_emision__month=ahora.month,
            fecha_emision__year=ahora.year
        )
        ventas_mes = facturas_mes.aggregate(total=Sum("total_con_impuestos"))["total"] or 0
        context["ventas_mes"] = ventas_mes

        context["productos_bajo_stock"] = Inventario.objects.filter(
            cantidad_actual__lte=F("ingrediente__stock_minimo")
        ).count()

        context["ventas_recientes"] = Factura.objects.filter(
            estado=Factura.Estado.PAGADA
        ).select_related("comanda__mesa").order_by("-fecha_emision")[:5]

        context["comandas_recientes"] = Comanda.objects.select_related(
            "mesa", "mesero"
        ).order_by("-fecha_creacion")[:5]

        return context


class UsuarioListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "core/usuarios/list.html"
    context_object_name = "usuarios"
    permission = "can_manage_users"

    def get_queryset(self):
        return User.objects.all().order_by("first_name", "last_name")


class UsuarioCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = User
    template_name = "core/usuarios/form.html"
    fields = ["username", "first_name", "last_name", "email", "role", "phone", "is_active_staff"]
    success_url = reverse_lazy("core:usuarios")
    permission = "can_manage_users"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.role == User.Role.MANAGER:
            context["roles"] = [(r[0], r[1]) for r in User.Role.choices if r[0] != User.Role.ADMIN]
        else:
            context["roles"] = User.Role.choices
        context["show_password_field"] = True
        return context

    def form_valid(self, form):
        password = self.request.POST.get("password", "")
        if not password:
            messages.error(self.request, "La contraseña es obligatoria")
            return super().form_invalid(form)
        form.instance.password = make_password(password)
        form.instance.visible_password = password
        messages.success(self.request, f"Usuario creado exitosamente")
        return super().form_valid(form)


class UsuarioUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = User
    template_name = "core/usuarios/form.html"
    fields = ["first_name", "last_name", "email", "role", "phone", "is_active_staff"]
    success_url = reverse_lazy("core:usuarios")
    permission = "can_manage_users"

    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado correctamente")
        return super().form_valid(form)


class UsuarioResetPasswordView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = User
    template_name = "core/usuarios/reset_password.html"
    context_object_name = "usuario"
    permission = "can_manage_users"

    def post(self, request, pk):
        usuario = self.get_object()
        password = _generar_contrasena()
        usuario.password = make_password(password)
        usuario.visible_password = password
        usuario.save(update_fields=["password", "visible_password"])
        messages.success(request, f"Contraseña de {usuario.get_full_name() or usuario.username} restablecida. Nueva contraseña: {password}")
        return redirect("core:usuarios")


class UsuarioDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy("core:usuarios")
    permission = "can_delete_users"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.pk == request.user.pk:
            messages.error(request, "No puedes eliminar tu propio usuario")
            return redirect("core:usuarios")
        messages.success(request, f"Usuario {self.object.get_full_name()} eliminado")
        return super().post(request, *args, **kwargs)


class UsuarioDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "core/usuarios/detalle.html"
    context_object_name = "usuario"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context["comandas_count"] = Comanda.objects.filter(mesero=user).count()
        context["comandas_recientes"] = Comanda.objects.filter(mesero=user).order_by("-fecha_creacion")[:10]
        context["facturas_count"] = Factura.objects.filter(usuario=user).count()
        context["facturas_recientes"] = Factura.objects.filter(usuario=user).order_by("-fecha_emision")[:10]
        return context


class CambiarPasswordView(LoginRequiredMixin, View):
    template_name = "core/usuarios/cambiar_password.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        actual = request.POST.get("password_actual", "")
        nueva = request.POST.get("password_nueva", "")
        confirmar = request.POST.get("password_confirmar", "")

        if not actual or not nueva or not confirmar:
            messages.error(request, "Todos los campos son obligatorios")
            return render(request, self.template_name)

        if not request.user.check_password(actual):
            messages.error(request, "La contraseña actual es incorrecta")
            return render(request, self.template_name)

        if nueva != confirmar:
            messages.error(request, "Las contraseñas nuevas no coinciden")
            return render(request, self.template_name)

        if len(nueva) < 4:
            messages.error(request, "La contraseña debe tener al menos 4 caracteres")
            return render(request, self.template_name)

        request.user.password = make_password(nueva)
        request.user.visible_password = nueva
        request.user.save(update_fields=["password", "visible_password"])
        messages.success(request, "Contraseña cambiada exitosamente")
        return redirect("core:usuario_detalle", pk=request.user.pk)


class PermisosMeserosView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "core/usuarios/permisos.html"
    context_object_name = "usuarios"
    permission = "can_manage_users"

    def get_queryset(self):
        return User.objects.order_by("first_name", "last_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_perms"] = [
            ("General", [
                ("can_view_dashboard", "Dashboard"),
                ("can_view_mesas", "Mesas"),
                ("can_view_comandas", "Ver Comandas"),
                ("can_create_comandas", "Crear Comandas"),
                ("can_manage_comandas", "Gestionar Comandas"),
                ("can_view_cocina", "Cocina"),
            ]),
            ("Administracion", [
                ("can_view_productos", "Productos"),
                ("can_manage_productos", "Gestionar Productos"),
                ("can_view_inventario", "Inventario"),
                ("can_manage_inventario", "Gestionar Inventario"),
                ("can_view_facturacion", "Facturacion"),
                ("can_create_facturas", "Crear Facturas"),
                ("can_cancel_facturas", "Cancelar Facturas"),
                ("can_manage_users", "Gestionar Usuarios"),
                ("can_delete_users", "Eliminar Usuarios"),
            ]),
        ]
        return context


class ActualizarPermisosView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.role == User.Role.ADMIN:
            messages.error(request, "No puedes modificar permisos de un Administrador")
            return redirect("core:permisos_meseros")

        perms = User.ROLE_PERMISSIONS.get("waiter", {}).keys()
        custom = {}
        for perm in perms:
            custom[perm] = request.POST.get(perm) == "on"

        if not any(custom.values()):
            custom["can_view_dashboard"] = True

        user.custom_permissions = custom
        user.save(update_fields=["custom_permissions"])

        messages.success(request, f"Permisos de {user.get_full_name()} actualizados")
        return redirect("core:permisos_meseros")


class ConfigRestauranteView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = ConfigRestaurante
    template_name = "core/config_restaurante.html"
    fields = ["nombre", "rfc", "direccion", "telefono", "email", "simbolo_moneda", "tasa_impuesto", "dias_credito_proveedor", "logo"]
    success_url = reverse_lazy("core:config_restaurante")
    permission = "can_manage_users"

    def get_object(self):
        return ConfigRestaurante.get_config()

    def form_valid(self, form):
        messages.success(self.request, "Configuracion del restaurante actualizada")
        return super().form_valid(form)
