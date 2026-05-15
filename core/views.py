from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.timezone import now, localtime
from django.db.models import Sum, Count, Q, F
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django import forms
import string
import random
from django.http import HttpResponseForbidden
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from inventario.models import Inventario, Ingrediente, Compra, CompraItem, CuentaPorPagar, MovimientoInventario
from mesas.models import Mesa
from comandas.models import Comanda, ComandaItem
from facturacion.models import Factura, CajaApertura
from productos.models import Producto, Categoria
from .models import User, ConfigRestaurante, Cliente, PagoCliente


class LandingView(TemplateView):
    template_name = "core/landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect("core:superadmin_dashboard")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)


class PermissionRequiredMixin:
    permission = None

    def dispatch(self, request, *args, **kwargs):
        if self.permission and not request.user.has_perm(self.permission):
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)


class ClienteScopeMixin:
    """Mixin que filtra automaticamente todas las queries por el cliente del usuario actual."""

    @classmethod
    def get_cliente_static(cls, request):
        if request.user.is_superuser:
            return None
        return getattr(request.user, "cliente", None)

    def get_cliente(self):
        if self.request.user.is_superuser:
            return None
        return getattr(self.request.user, "cliente", None)

    def get_queryset(self):
        qs = super().get_queryset()
        cliente = self.get_cliente()
        if cliente:
            if hasattr(qs.model, "cliente"):
                qs = qs.filter(cliente=cliente)
        return qs

    def form_valid(self, form):
        cliente = self.get_cliente()
        if hasattr(form, "instance") and hasattr(form.instance, "cliente_id"):
            if not form.instance.cliente_id:
                if cliente:
                    form.instance.cliente = cliente
                else:
                    from django.contrib import messages
                    messages.error(self.request, "No tienes un restaurante asignado. Contacta a soporte.")
                    return self.form_invalid(form)
        return super().form_valid(form)


class CustomLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        if not user.is_superuser:
            messages.error(self.request, "Usa cliente/login para iniciar sesion con tus credenciales de acceso")
            return reverse_lazy("core:cliente_login")
        return reverse_lazy("core:superadmin_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo"] = True
        return context


class ClienteLoginView(LoginView):
    template_name = "core/login_cliente.html"
    redirect_authenticated_user = True

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect("core:superadmin_dashboard")
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return reverse_lazy("core:dashboard")

    def form_valid(self, form):
        user = form.get_user()
        if user.is_superuser:
            messages.error(self.request, "Usa el panel de administrador para iniciar sesion")
            return redirect("core:login")
        if not user.is_active:
            messages.error(self.request, "Tu cuenta esta suspendida. Contacta a soporte.")
            return redirect("core:cliente_login")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_cliente_login"] = True
        return context


class CustomLogoutView(LogoutView):

    def dispatch(self, request, *args, **kwargs):
        self._is_superuser = request.user.is_superuser
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        if getattr(self, "_is_superuser", False):
            return redirect("core:login")
        return redirect("core:cliente_login")


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

    def _get_cliente(self):
        if self.request.user.is_superuser:
            return None
        return getattr(self.request.user, "cliente", None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self._get_cliente()

        mesa_qs = Mesa.objects.all()
        comanda_qs = Comanda.objects.all()
        factura_qs = Factura.objects.all()
        inventario_qs = Inventario.objects.all()

        if cliente:
            mesa_qs = mesa_qs.filter(cliente=cliente)
            comanda_qs = comanda_qs.filter(cliente=cliente)
            factura_qs = factura_qs.filter(cliente=cliente)
            inventario_qs = inventario_qs.filter(ingrediente__cliente=cliente)

        context["mesas_ocupadas"] = mesa_qs.filter(estado=Mesa.Estado.OCUPADA).count()
        context["mesas_libres"] = mesa_qs.filter(estado=Mesa.Estado.LIBRE).count()
        context["mesas_reservadas"] = mesa_qs.filter(estado=Mesa.Estado.RESERVADA).count()
        context["mesas_total"] = mesa_qs.count()

        ahora = localtime(now())
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        hoy_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)

        context["comandas_abiertas"] = comanda_qs.filter(estado=Comanda.Estado.ABIERTA).count()
        context["comandas_en_cocina"] = comanda_qs.filter(estado=Comanda.Estado.EN_COCINA).count()
        context["comandas_cerradas"] = comanda_qs.filter(estado=Comanda.Estado.CERRADA).count()
        context["comandas_hoy"] = comanda_qs.filter(
            fecha_creacion__gte=hoy_inicio,
            fecha_creacion__lte=hoy_fin
        ).count()

        facturas_pagadas = factura_qs.filter(estado=Factura.Estado.PAGADA)

        facturas_hoy = facturas_pagadas.filter(
            fecha_emision__gte=hoy_inicio,
            fecha_emision__lte=hoy_fin
        )
        hoy_stats = facturas_hoy.aggregate(
            total=Sum("total_con_impuestos"),
            count=Count("id")
        )
        context["ventas_hoy"] = hoy_stats["total"] or 0
        context["facturas_hoy"] = hoy_stats["count"] or 0

        facturas_mes = facturas_pagadas.filter(
            fecha_emision__month=ahora.month,
            fecha_emision__year=ahora.year
        )
        mes_stats = facturas_mes.aggregate(total=Sum("total_con_impuestos"))
        context["ventas_mes"] = mes_stats["total"] or 0

        total_stats = facturas_pagadas.aggregate(
            total=Sum("total_con_impuestos"),
            count=Count("id")
        )
        context["ventas_total"] = total_stats["total"] or 0
        context["facturas_total"] = total_stats["count"] or 0

        context["productos_bajo_stock"] = inventario_qs.filter(
            cantidad_actual__lte=F("ingrediente__stock_minimo")
        ).count()

        context["ventas_recientes"] = facturas_pagadas.select_related(
            "comanda__mesa"
        ).order_by("-fecha_emision")[:5]

        context["comandas_recientes"] = comanda_qs.select_related(
            "mesa", "mesero"
        ).order_by("-fecha_creacion")[:5]

        return context


class UsuarioListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "core/usuarios/list.html"
    context_object_name = "usuarios"
    permission = "can_manage_users"

    def get_queryset(self):
        qs = User.objects.select_related("cliente").filter(is_superuser=False)
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs.order_by("cliente__nombre_negocio", "role", "first_name", "last_name")


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
        if not self.request.user.is_superuser:
            form.instance.cliente = getattr(self.request.user, "cliente", None)
        messages.success(self.request, f"Usuario creado exitosamente")
        return super().form_valid(form)


class UsuarioUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = User
    template_name = "core/usuarios/form.html"
    fields = ["first_name", "last_name", "email", "role", "phone", "is_active_staff"]
    success_url = reverse_lazy("core:usuarios")
    permission = "can_manage_users"

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs

    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado correctamente")
        return super().form_valid(form)


class UsuarioResetPasswordView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = User
    template_name = "core/usuarios/reset_password.html"
    context_object_name = "usuario"
    permission = "can_manage_users"

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        password = _generar_contrasena()
        usuario.password = make_password(password)
        usuario.visible_password = password
        usuario.save(update_fields=["password", "visible_password"])
        cliente = getattr(usuario, "cliente", None)
        if cliente and usuario.role == User.Role.ADMIN:
            cliente.admin_password_visible = password
            cliente.save(update_fields=["admin_password_visible"])
        messages.success(request, f"Contraseña de {usuario.get_full_name() or usuario.username} restablecida. Nueva contraseña: {password}")
        return redirect("core:usuarios")


class UsuarioDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy("core:usuarios")
    permission = "can_delete_users"

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs

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

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        cliente_filter = getattr(user, "cliente", None)
        if not self.request.user.is_superuser and not cliente_filter:
            return context
        comanda_qs = Comanda.objects.all()
        factura_qs = Factura.objects.all()
        if cliente_filter:
            comanda_qs = comanda_qs.filter(cliente=cliente_filter)
            factura_qs = factura_qs.filter(cliente=cliente_filter)
        context["comandas_count"] = comanda_qs.filter(mesero=user).count()
        context["comandas_recientes"] = comanda_qs.filter(mesero=user).order_by("-fecha_creacion")[:10]
        context["facturas_count"] = factura_qs.filter(usuario=user).count()
        context["facturas_recientes"] = factura_qs.filter(usuario=user).order_by("-fecha_emision")[:10]
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

        user = request.user
        user.password = make_password(nueva)
        user.visible_password = nueva
        user.save(update_fields=["password", "visible_password"])
        cliente = getattr(user, "cliente", None)
        if cliente:
            cliente.admin_password_visible = nueva
            cliente.save(update_fields=["admin_password_visible"])
        messages.success(request, "Contraseña cambiada exitosamente")
        return redirect("core:usuario_detalle", pk=user.pk)


class PermisosMeserosView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "core/usuarios/permisos.html"
    context_object_name = "usuarios"
    permission = "can_manage_users"

    def get_queryset(self):
        qs = User.objects.order_by("first_name", "last_name")
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        return qs

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

    def post(self, request, *args, **kwargs):
        from django.urls import reverse
        next_url = request.POST.get("next") or reverse("core:permisos_meseros")

        qs = User.objects.all()
        if not request.user.is_superuser:
            cliente = getattr(request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
        user = get_object_or_404(qs, pk=kwargs['pk'])
        if user.role == User.Role.ADMIN:
            messages.error(request, "No puedes modificar permisos de un Administrador")
            return redirect(next_url)

        perms = User.ROLE_PERMISSIONS.get("waiter", {}).keys()
        custom = {}
        for perm in perms:
            custom[perm] = request.POST.get(perm) == "on"

        if not any(custom.values()):
            custom["can_view_dashboard"] = True

        user.custom_permissions = custom
        user.save(update_fields=["custom_permissions"])

        messages.success(request, f"Permisos de {user.get_full_name()} actualizados")
        return redirect(next_url)

class ConfigRestauranteForm(forms.ModelForm):
    class Meta:
        model = ConfigRestaurante
        fields = ["nombre", "rfc", "direccion", "telefono", "email", "simbolo_moneda", "dias_credito_proveedor", "logo"]


class ConfigRestauranteView(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = "core/config_restaurante.html"
    permission = "can_manage_users"

    def get(self, request):
        cliente = getattr(request.user, 'cliente', None)
        config = ConfigRestaurante.get_config(cliente)
        form = ConfigRestauranteForm(instance=config)
        from respaldos.models import DatabaseBackup
        ultimo_respaldo = DatabaseBackup.objects.filter(
            cliente=cliente,
            estado__in=[DatabaseBackup.Estado.EXITOSO, DatabaseBackup.Estado.RESTAURADO]
        ).order_by("-fecha_creacion").first()
        return render(request, self.template_name, {
            "object": config,
            "form": form,
            "ultimo_respaldo": ultimo_respaldo,
        })

    def post(self, request):
        cliente = getattr(request.user, 'cliente', None)
        config = ConfigRestaurante.get_config(cliente)
        form = ConfigRestauranteForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuracion del restaurante actualizada")
            return redirect("core:config_restaurante")
        for field, errors in form.errors.items():
            for error in errors:
                label = field.replace("_", " ").title()
                messages.error(request, f"{label}: {error}")
        return render(request, self.template_name, {"object": config, "form": form})


class AyudaImpresionView(LoginRequiredMixin, TemplateView):
    template_name = "core/ayuda_impresion.html"


class RestablecerFabricaView(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = "core/config_restaurante_reset.html"
    permission = "can_manage_users"

    def get(self, request):
        cliente = getattr(request.user, 'cliente', None)
        from respaldos.models import DatabaseBackup
        ultimo_respaldo = DatabaseBackup.objects.filter(
            cliente=cliente,
            estado__in=[DatabaseBackup.Estado.EXITOSO, DatabaseBackup.Estado.RESTAURADO]
        ).order_by("-fecha_creacion").first()
        return render(request, self.template_name, {
            "cliente": cliente,
            "ultimo_respaldo": ultimo_respaldo,
        })

    def post(self, request):
        confirmacion = request.POST.get("confirmacion", "").strip()
        if confirmacion != "RESTABLECER":
            messages.error(request, "Debes escribir 'RESTABLECER' para confirmar")
            return redirect("core:config_restaurante")

        cliente = getattr(request.user, 'cliente', None)
        if not cliente:
            messages.error(request, "No se puede restablecer sin un restaurante asignado")
            return redirect("core:config_restaurante")

        import os
        import uuid
        import hashlib
        from datetime import datetime
        from django.db import transaction
        from respaldos.models import DatabaseBackup, TENANT_APPS

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"backup_pre_reset_{timestamp}_{unique_id}.json"
            backup_dir = os.path.join(settings.MEDIA_ROOT, "respaldos", str(cliente.pk))
            backup_path = os.path.join(backup_dir, filename)
            os.makedirs(backup_dir, exist_ok=True)

            backup = DatabaseBackup.objects.create(
                nombre=f"Respaldo Pre-Reset {timestamp}",
                creado_por=request.user,
                cliente=cliente,
                estado=DatabaseBackup.Estado.PENDIENTE,
                notas="Respaldo automatico antes de restablecer de fabrica",
            )

            import json
            data = []
            for app_model in TENANT_APPS:
                app_label, model_name = app_model.split(".")
                model = __import__(f"{app_label}.models", fromlist=[model_name]).__dict__[model_name]

                if hasattr(model, 'cliente'):
                    qs = model.objects.filter(cliente=cliente)
                else:
                    filter_lookups = {
                        "Inventario": "ingrediente__cliente",
                        "MovimientoInventario": "inventario__ingrediente__cliente",
                        "CompraItem": "compra__cliente",
                        "ComandaItem": "comanda__cliente",
                    }
                    lookup = filter_lookups.get(model_name)
                    if lookup:
                        qs = model.objects.filter(**{lookup: cliente})
                    else:
                        continue

                for obj in qs:
                    item = {
                        "model": f"{app_label}.{model_name}",
                        "pk": obj.pk,
                        "fields": {},
                    }
                    for field in obj._meta.fields:
                        if field.name in ("id", "cliente"):
                            continue
                        value = getattr(obj, field.name)
                        if hasattr(value, "isoformat"):
                            value = value.isoformat()
                        if hasattr(value, "pk"):
                            value = value.pk
                        item["fields"][field.name] = value
                    data.append(item)

            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            backup.archivo.name = os.path.relpath(backup_path, settings.MEDIA_ROOT).replace("\\", "/")
            backup.estado = DatabaseBackup.Estado.EXITOSO
            backup.calcular_tamaño()
            try:
                with open(backup_path, "rb") as f:
                    backup.hash_md5 = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
            backup.save()

        except Exception as e:
            messages.error(request, f"Error al crear respaldo previo: {str(e)}")
            return redirect("core:config_restaurante")

        try:
            with transaction.atomic():
                from facturacion.models import Factura, CajaApertura
                from comandas.models import Comanda, ComandaItem
                from mesas.models import Mesa
                from productos.models import Producto, Categoria
                from meseros.models import Mesero
                from inventario.models import Ingrediente, Compra, CompraItem, CuentaPorPagar, Inventario, MovimientoInventario

                ComandaItem.objects.filter(comanda__cliente=cliente).delete()
                Factura.objects.filter(cliente=cliente).delete()
                CajaApertura.objects.filter(cliente=cliente).delete()
                Comanda.objects.filter(cliente=cliente).delete()
                Mesa.objects.filter(cliente=cliente).delete()
                Mesero.objects.filter(cliente=cliente).delete()
                CuentaPorPagar.objects.filter(cliente=cliente).delete()
                MovimientoInventario.objects.filter(inventario__ingrediente__cliente=cliente).delete()
                CompraItem.objects.filter(ingrediente__cliente=cliente).delete()
                Compra.objects.filter(cliente=cliente).delete()
                Inventario.objects.filter(ingrediente__cliente=cliente).delete()
                Ingrediente.objects.filter(cliente=cliente).delete()
                Producto.objects.filter(cliente=cliente).delete()
                Categoria.objects.filter(cliente=cliente).delete()

            from core.utils import crear_datos_iniciales_cliente
            crear_datos_iniciales_cliente(cliente)

            messages.success(request, "Sistema restablecido de fabrica. Datos iniciales creados. Tu respaldo previo fue guardado automaticamente.")
        except Exception as e:
            messages.error(request, f"Error durante el restablecimiento: {str(e)}")

        return redirect("core:config_restaurante")


class RestaurarUltimoRespaldoView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def post(self, request):
        from respaldos.models import DatabaseBackup
        import os
        from django.db import transaction
        import json

        cliente = getattr(request.user, 'cliente', None)
        if not cliente:
            messages.error(request, "No se puede restaurar sin un restaurante asignado")
            return redirect("core:config_restaurante")

        ultimo = DatabaseBackup.objects.filter(
            cliente=cliente,
            estado__in=[DatabaseBackup.Estado.EXITOSO, DatabaseBackup.Estado.RESTAURADO]
        ).order_by("-fecha_creacion").first()

        if not ultimo or not ultimo.archivo or not os.path.exists(ultimo.archivo.path):
            messages.error(request, "No hay un respaldo valido para restaurar")
            return redirect("core:config_restaurante")

        confirmacion = request.POST.get("confirmacion", "").strip()
        if confirmacion != "RESTAURAR":
            messages.error(request, "Debes escribir 'RESTAURAR' para confirmar")
            return redirect("core:config_restaurante")

        try:
            from django.utils import timezone
            from facturacion.models import Factura, CajaApertura, CajaMovimiento
            from comandas.models import Comanda, ComandaItem
            from mesas.models import Mesa
            from productos.models import Producto, Categoria
            from meseros.models import Mesero
            from inventario.models import Ingrediente, Compra, CompraItem, CuentaPorPagar, Inventario, MovimientoInventario, Receta

            ultimo.estado = DatabaseBackup.Estado.RESTAURANDO
            ultimo.fecha_restauracion = timezone.now()
            ultimo.restaurado_por = request.user
            ultimo.save(update_fields=["estado", "fecha_restauracion", "restaurado_por"])

            with transaction.atomic():
                delete_order = [
                    ComandaItem, CajaMovimiento, Factura, Comanda, Mesa,
                    Mesero, CuentaPorPagar, MovimientoInventario,
                    CompraItem, Compra, Inventario, Receta, Ingrediente,
                    Producto, Categoria, CajaApertura,
                ]
                for model in delete_order:
                    if hasattr(model, 'cliente'):
                        model.objects.filter(cliente=cliente).delete()
                    else:
                        delete_lookups = {
                            "ComandaItem": "comanda__cliente",
                            "CajaMovimiento": "caja__cliente",
                            "Receta": "producto__cliente",
                            "MovimientoInventario": "inventario__ingrediente__cliente",
                            "CompraItem": "compra__cliente",
                            "Inventario": "ingrediente__cliente",
                        }
                        lookup = delete_lookups.get(model.__name__)
                        if lookup:
                            model.objects.filter(**{lookup: cliente}).delete()

                with open(ultimo.archivo.path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                grouped = {}
                for item in data:
                    model_key = item["model"]
                    grouped.setdefault(model_key, []).append(item)

                restore_order = [
                    "mesas.Mesa",
                    "productos.Categoria",
                    "inventario.Ingrediente",
                    "inventario.Inventario",
                    "meseros.Mesero",
                    "productos.Producto",
                    "inventario.Receta",
                    "comandas.Comanda",
                    "inventario.Compra",
                    "comandas.ComandaItem",
                    "inventario.CompraItem",
                    "inventario.MovimientoInventario",
                    "facturacion.Factura",
                    "facturacion.CajaApertura",
                    "facturacion.CajaMovimiento",
                    "inventario.CuentaPorPagar",
                ]

                for model_key in restore_order:
                    items = grouped.get(model_key, [])
                    if not items:
                        continue
                    app_label, model_name = model_key.split(".")
                    model = __import__(f"{app_label}.models", fromlist=[model_name]).__dict__[model_name]
                    for item in items:
                        pk = item["pk"]
                        fields = dict(item["fields"])
                        fk_fields = [f.name for f in model._meta.fields if f.is_relation and f.name != "cliente"]
                        for fk_name in fk_fields:
                            if fk_name in fields and fields[fk_name] is not None:
                                fk_model = model._meta.get_field(fk_name).related_model
                                if fk_model._meta.app_label != app_label:
                                    try:
                                        fields[fk_name] = fk_model.objects.get(pk=fields[fk_name])
                                    except fk_model.DoesNotExist:
                                        fields[fk_name] = None
                        fields["cliente"] = cliente
                        model.objects.create(pk=pk, **fields)

            ultimo.estado = DatabaseBackup.Estado.RESTAURADO
            ultimo.save(update_fields=["estado"])
            messages.success(request, "Respaldo restaurado exitosamente. Redirigiendo...")
        except Exception as e:
            ultimo.estado = DatabaseBackup.Estado.FALLIDO
            ultimo.save(update_fields=["estado"])
            messages.error(request, f"Error al restaurar: {str(e)}")

        return redirect("core:config_restaurante")


class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            cliente = getattr(request.user, 'cliente', None)
            if cliente and cliente.dias_restantes() <= 0 and cliente.estado not in (Cliente.Estado.CANCELADO,):
                excluded_paths = [
                    '/suscripcion-vencida/',
                    '/logout/',
                    '/core/logout/',
                ]
                if not any(request.path.startswith(p) for p in excluded_paths):
                    return redirect("core:suscripcion_vencida")
        return self.get_response(request)


class SuscripcionVencidaView(LoginRequiredMixin, View):
    template_name = "core/suscripcion_vencida.html"

    def get(self, request):
        cliente = getattr(request.user, 'cliente', None)
        if not cliente:
            return redirect("core:dashboard")
        if cliente.dias_restantes() > 0 or cliente.estado == Cliente.Estado.CANCELADO:
            return redirect("core:dashboard")
        return render(request, self.template_name, {"cliente": cliente})


class SuperAdminListView(PermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/superadmin/dashboard.html"
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils import timezone
        from django.db.models import Sum, OuterRef, Subquery
        clientes = Cliente.objects.all()
        context["clientes"] = clientes
        context["total_clientes"] = clientes.count()
        context["clientes_activos"] = clientes.filter(estado=Cliente.Estado.ACTIVO).count()
        context["clientes_prueba"] = clientes.filter(estado=Cliente.Estado.PRUEBA).count()
        context["clientes_vencidos"] = clientes.filter(estado=Cliente.Estado.VENCIDO).count()
        total_ingresos = PagoCliente.objects.aggregate(total=Sum("monto"))["total"] or 0
        context["total_ingresos"] = total_ingresos
        ingresos_mes = PagoCliente.objects.filter(fecha__month=timezone.now().month, fecha__year=timezone.now().year).aggregate(total=Sum("monto"))["total"] or 0
        context["ingresos_mes"] = ingresos_mes
        ingresos_anio = PagoCliente.objects.filter(fecha__year=timezone.now().year).aggregate(total=Sum("monto"))["total"] or 0
        context["ingresos_anio"] = ingresos_anio
        pagos_recientes = PagoCliente.objects.select_related("cliente").order_by("-fecha")[:10]
        context["pagos_recientes"] = pagos_recientes
        clientes_por_vencer = clientes.filter(fecha_pago_proximo__isnull=False).order_by("fecha_pago_proximo")[:5]
        context["clientes_por_vencer"] = clientes_por_vencer
        totales_por_cliente = dict(PagoCliente.objects.values("cliente").annotate(total=Sum("monto")).values_list("cliente", "total"))
        context["totales_por_cliente"] = totales_por_cliente
        return context


class ClienteCreateView(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = "core/superadmin/cliente_crear.html"
    permission = "can_manage_users"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from django.contrib.auth.hashers import make_password

        nombre = request.POST.get("nombre_negocio", "").strip()
        rfc = request.POST.get("rfc", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()
        admin_username = request.POST.get("admin_username", "").strip()
        admin_email = request.POST.get("admin_email", "").strip()
        periodo = request.POST.get("periodo", "30")

        if not nombre or not admin_username:
            messages.error(request, "Nombre del negocio y usuario administrador son obligatorios")
            return render(request, self.template_name, {"nombre": nombre, "rfc": rfc, "direccion": direccion, "telefono": telefono, "email": email, "admin_username": admin_username, "admin_email": admin_email})

        if User.objects.filter(username=admin_username).exists():
            messages.error(request, f"El usuario '{admin_username}' ya existe")
            return render(request, self.template_name, {"nombre": nombre, "rfc": rfc, "direccion": direccion, "telefono": telefono, "email": email, "admin_username": admin_username, "admin_email": admin_email})

        password = _generar_contrasena(10)
        fecha_inicio = timezone.now()
        periodo_dias = int(periodo)
        fecha_pago = fecha_inicio + timedelta(days=periodo_dias)

        cliente = Cliente.objects.create(
            nombre_negocio=nombre,
            rfc=rfc,
            direccion=direccion,
            telefono=telefono,
            email=email,
            simbolo_moneda="C$",
            admin_username=admin_username,
            admin_email=admin_email,
            admin_password_visible=password,
            periodo_dias=periodo_dias,
            estado=Cliente.Estado.PRUEBA if periodo_dias <= 14 else Cliente.Estado.ACTIVO,
            fecha_inicio=fecha_inicio,
            fecha_pago_proximo=fecha_pago,
        )

        admin_user = User.objects.create(
            username=admin_username,
            email=admin_email,
            first_name="Admin",
            last_name=nombre,
            role=User.Role.ADMIN,
            cliente=cliente,
            visible_password=password,
            password=make_password(password),
        )

        ConfigRestaurante.objects.create(
            cliente=cliente,
            nombre=nombre,
            rfc=rfc,
            direccion=direccion,
            telefono=telefono,
            email=email,
            simbolo_moneda="C$",
        )

        from core.utils import crear_datos_iniciales_cliente
        crear_datos_iniciales_cliente(cliente)

        messages.success(request, f"Cliente '{nombre}' creado. Usuario: {admin_username}, Contraseña: {password}")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = "core/superadmin/cliente_detalle.html"
    context_object_name = "cliente"
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_object()

        context["pagos"] = PagoCliente.objects.filter(cliente=cliente).order_by("-fecha")[:20]
        context["admin_user"] = User.objects.filter(cliente=cliente).first()
        context["config"] = ConfigRestaurante.objects.filter(cliente=cliente).first()
        context["total_pagado"] = PagoCliente.objects.filter(cliente=cliente).aggregate(total=Sum("monto"))["total"] or 0

        from mesas.models import Mesa
        from comandas.models import Comanda
        from facturacion.models import Factura
        from inventario.models import Inventario, Ingrediente
        from productos.models import Producto
        from django.db.models import F, Count

        context["total_mesas"] = Mesa.objects.filter(cliente=cliente).count()
        context["mesas_ocupadas"] = Mesa.objects.filter(cliente=cliente, estado=Mesa.Estado.OCUPADA).count()
        context["mesas_libres"] = Mesa.objects.filter(cliente=cliente, estado=Mesa.Estado.LIBRE).count()

        context["total_comandas"] = Comanda.objects.filter(cliente=cliente).count()
        context["comandas_abiertas"] = Comanda.objects.filter(cliente=cliente, estado=Comanda.Estado.ABIERTA).count()
        context["comandas_en_cocina"] = Comanda.objects.filter(cliente=cliente, estado=Comanda.Estado.EN_COCINA).count()
        context["comandas_cerradas"] = Comanda.objects.filter(cliente=cliente, estado=Comanda.Estado.CERRADA).count()

        facturas_pagadas = Factura.objects.filter(cliente=cliente, estado=Factura.Estado.PAGADA)
        context["total_facturas"] = Factura.objects.filter(cliente=cliente).count()
        context["ventas_total"] = facturas_pagadas.aggregate(total=Sum("total_con_impuestos"))["total"] or 0

        context["total_productos"] = Producto.objects.filter(cliente=cliente, activo=True).count()
        context["total_ingredientes"] = Ingrediente.objects.filter(cliente=cliente, activo=True).count()
        context["productos_bajo_stock"] = Inventario.objects.filter(
            ingrediente__cliente=cliente,
            cantidad_actual__lte=F("ingrediente__stock_minimo")
        ).count()

        context["usuarios"] = User.objects.filter(cliente=cliente, is_superuser=False).order_by("role", "first_name", "last_name")
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


class ClienteUpdateView(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = "core/superadmin/cliente_editar.html"
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, self.template_name, {"cliente": cliente})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.nombre_negocio = request.POST.get("nombre_negocio", cliente.nombre_negocio)
        cliente.rfc = request.POST.get("rfc", cliente.rfc)
        cliente.direccion = request.POST.get("direccion", cliente.direccion)
        cliente.telefono = request.POST.get("telefono", cliente.telefono)
        cliente.email = request.POST.get("email", cliente.email)
        cliente.admin_email = request.POST.get("admin_email", cliente.admin_email)
        cliente.estado = request.POST.get("estado", cliente.estado)
        cliente.notas = request.POST.get("notas", cliente.notas)

        periodo = request.POST.get("periodo")
        if periodo:
            from django.utils import timezone
            from datetime import timedelta
            cliente.fecha_pago_proximo = timezone.now() + timedelta(days=int(periodo))

        nueva_password = request.POST.get("nueva_password", "").strip()
        if nueva_password:
            cliente.admin_password_visible = nueva_password
            admin_user = User.objects.filter(cliente=cliente).first()
            if admin_user:
                from django.contrib.auth.hashers import make_password
                admin_user.password = make_password(nueva_password)
                admin_user.visible_password = nueva_password
                admin_user.save(update_fields=["password", "visible_password"])

        cliente.save()

        config = ConfigRestaurante.objects.filter(cliente=cliente).first()
        if config:
            config.nombre = cliente.nombre_negocio
            config.rfc = cliente.rfc
            config.direccion = cliente.direccion
            config.telefono = cliente.telefono
            config.email = cliente.email
            config.save()

        messages.success(request, f"Cliente '{cliente.nombre_negocio}' actualizado")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteRegistrarPagoView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        monto = request.POST.get("monto", "")
        metodo = request.POST.get("metodo", PagoCliente.Metodo.EFECTIVO)
        notas = request.POST.get("notas", "")

        if not monto:
            messages.error(request, "El monto es obligatorio")
            return redirect("core:superadmin_cliente_detalle", pk=pk)

        from decimal import Decimal
        try:
            monto_dec = Decimal(monto)
        except Exception:
            messages.error(request, "Monto no valido")
            return redirect("core:superadmin_cliente_detalle", pk=pk)

        PagoCliente.objects.create(cliente=cliente, monto=monto_dec, metodo=metodo, notas=notas)

        from django.utils import timezone
        from datetime import timedelta
        cliente.fecha_pago_proximo = timezone.now() + timedelta(days=30)

        if cliente.estado == Cliente.Estado.VENCIDO:
            cliente.estado = Cliente.Estado.ACTIVO

        cliente.save()
        messages.success(request, f"Pago de {monto_dec} registrado para {cliente.nombre_negocio}")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteCancelarView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.estado = Cliente.Estado.CANCELADO
        from django.utils import timezone
        cliente.fecha_cancelacion = timezone.now()
        cliente.save()

        admin_user = User.objects.filter(cliente=cliente).first()
        if admin_user:
            admin_user.is_active = False
            admin_user.save(update_fields=["is_active"])

        messages.success(request, f"Cliente '{cliente.nombre_negocio}' cancelado")
        return redirect("core:superadmin_dashboard")


class ClienteReactivarView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.estado = Cliente.Estado.ACTIVO
        cliente.fecha_cancelacion = None
        cliente.save()

        admin_user = User.objects.filter(cliente=cliente).first()
        if admin_user:
            admin_user.is_active = True
            admin_user.save(update_fields=["is_active"])

        messages.success(request, f"Cliente '{cliente.nombre_negocio}' reactivado")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteResetPasswordView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        nueva_password = _generar_contrasena(10)
        cliente.admin_password_visible = nueva_password
        cliente.save(update_fields=["admin_password_visible"])

        admin_user = User.objects.filter(cliente=cliente).first()
        if admin_user:
            admin_user.password = make_password(nueva_password)
            admin_user.visible_password = nueva_password
            admin_user.save(update_fields=["password", "visible_password"])

        messages.success(request, f"Contraseña de '{cliente.nombre_negocio}' restablecida. Nueva contraseña: {nueva_password}")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteEnviarCredencialesView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        admin_user = User.objects.filter(cliente=cliente, role=User.Role.ADMIN).first()
        password = admin_user.visible_password if admin_user else cliente.admin_password_visible
        if not cliente.admin_email:
            messages.error(request, "El cliente no tiene un email registrado")
            return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)
        import threading
        import logging
        logger = logging.getLogger(__name__)
        def _send():
            try:
                from core.emails import enviar_email_bienvenida
                enviar_email_bienvenida(cliente, password)
            except Exception:
                logger.exception("Error al enviar credenciales por correo a %s", cliente.admin_email)
        threading.Thread(target=_send).start()
        messages.success(request, f"Enviando credenciales por correo a {cliente.admin_email}...")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteDeleteView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, "core/superadmin/cliente_eliminar.html", {
            "cliente": cliente,
            "admin_user": User.objects.filter(cliente=cliente).first(),
            "config": ConfigRestaurante.objects.filter(cliente=cliente).first(),
            "pagos": PagoCliente.objects.filter(cliente=cliente),
        })

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        confirmacion = request.POST.get("confirmacion", "").strip()

        if confirmacion != cliente.nombre_negocio:
            messages.error(request, f"El nombre no coincide. Escribe '{cliente.nombre_negocio}' para confirmar")
            return render(request, "core/superadmin/cliente_eliminar.html", {
                "cliente": cliente,
                "error": True,
                "admin_user": User.objects.filter(cliente=cliente).first(),
                "config": ConfigRestaurante.objects.filter(cliente=cliente).first(),
                "pagos": PagoCliente.objects.filter(cliente=cliente),
            })

        nombre = cliente.nombre_negocio
        User.objects.filter(cliente=cliente).delete()
        ConfigRestaurante.objects.filter(cliente=cliente).delete()
        PagoCliente.objects.filter(cliente=cliente).delete()

        from facturacion.models import Factura
        from comandas.models import Comanda, ComandaItem
        from mesas.models import Mesa
        from productos.models import Producto, Categoria
        from meseros.models import Mesero
        from inventario.models import Ingrediente, Compra, CompraItem, CuentaPorPagar, Inventario, MovimientoInventario

        ComandaItem.objects.filter(comanda__cliente=cliente).delete()
        Factura.objects.filter(cliente=cliente).delete()
        Comanda.objects.filter(cliente=cliente).delete()
        Mesa.objects.filter(cliente=cliente).delete()
        CuentaPorPagar.objects.filter(cliente=cliente).delete()
        MovimientoInventario.objects.filter(inventario__ingrediente__cliente=cliente).delete()
        CompraItem.objects.filter(ingrediente__cliente=cliente).delete()
        Compra.objects.filter(cliente=cliente).delete()
        Inventario.objects.filter(ingrediente__cliente=cliente).delete()
        Ingrediente.objects.filter(cliente=cliente).delete()
        Mesero.objects.filter(cliente=cliente).delete()
        Producto.objects.filter(cliente=cliente).delete()
        Categoria.objects.filter(cliente=cliente).delete()

        cliente.delete()

        messages.success(request, f"Cliente '{nombre}' y todos sus datos han sido eliminados permanentemente")
        return redirect("core:superadmin_dashboard")


class ClienteExtendView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        dias = request.POST.get("dias", "")

        if not dias:
            messages.error(request, "Ingresa el numero de dias a extender")
            return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)

        from django.utils import timezone
        from datetime import timedelta
        try:
            dias_int = int(dias)
            if dias_int <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Numero de dias no valido")
            return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)

        base = timezone.now() if cliente.fecha_pago_proximo is None or cliente.fecha_pago_proximo < timezone.now() else cliente.fecha_pago_proximo
        cliente.fecha_pago_proximo = base + timedelta(days=dias_int)
        cliente.periodo_dias = dias_int

        if cliente.estado == Cliente.Estado.VENCIDO:
            cliente.estado = Cliente.Estado.ACTIVO

        cliente.save()
        messages.success(request, f"Suscripcion de '{cliente.nombre_negocio}' extendida por {dias_int} dias")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)


class ClienteSuspendView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission = "can_manage_users"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "core/acceso_bloqueado.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        if cliente.estado == Cliente.Estado.CANCELADO:
            messages.error(request, "El cliente ya esta cancelado")
            return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)

        cliente.estado = Cliente.Estado.VENCIDO
        admin_user = User.objects.filter(cliente=cliente).first()
        if admin_user:
            admin_user.is_active = False
            admin_user.save(update_fields=["is_active"])

        cliente.save()
        messages.success(request, f"Cliente '{cliente.nombre_negocio}' suspendido. No puede iniciar sesion")
        return redirect("core:superadmin_cliente_detalle", pk=cliente.pk)
