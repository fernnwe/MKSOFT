from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from core.views import ClienteScopeMixin, PermissionRequiredMixin
from .models import Comanda, ComandaItem
from mesas.models import Mesa
from productos.models import Producto
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

User = get_user_model()


class ComandaListView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Comanda
    template_name = "comandas/list.html"
    context_object_name = "comandas"
    paginate_by = 20
    permission = "can_view_comandas"

    def get_queryset(self):
        qs = super().get_queryset().select_related("mesa", "mesero").prefetch_related("items")
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estados"] = Comanda.Estado.choices
        return context


class ComandaCreateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Comanda
    template_name = "comandas/crear.html"
    fields = ["mesa", "prioridad", "notas"]
    success_url = reverse_lazy("comandas:list")
    permission = "can_create_comandas"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        cliente = self.get_cliente()
        if cliente:
            form.fields["mesa"].queryset = Mesa.objects.filter(cliente=cliente)
        return form

    def form_valid(self, form):
        import uuid
        if not form.instance.codigo:
            form.instance.codigo = f"CMD-{uuid.uuid4().hex[:8].upper()}"

        cliente = self.get_cliente()
        if not form.instance.cliente_id and cliente:
            form.instance.cliente = cliente

        mesero_id = self.request.POST.get("mesero")
        if mesero_id:
            mesero_qs = User.objects.all()
            if cliente:
                mesero_qs = mesero_qs.filter(cliente=cliente)
            form.instance.mesero = mesero_qs.filter(pk=mesero_id).first() or self.request.user
        else:
            form.instance.mesero = self.request.user

        mesa = form.instance.mesa
        if cliente and mesa.cliente_id != cliente.pk:
            messages.error(self.request, "La mesa seleccionada no pertenece a tu restaurante")
            return self.form_invalid(form)
        if mesa.estado == Mesa.Estado.LIBRE:
            mesa.estado = Mesa.Estado.OCUPADA
            mesa.save()
        response = super().form_valid(form)
        messages.success(self.request, f"Comanda {form.instance.codigo} creada. Agrega productos y envia a cocina.")

        try:
            async_to_sync(get_channel_layer().group_send)(
                "comandas",
                {
                    "type": "comanda_new",
                    "comanda_id": form.instance.pk,
                    "codigo": form.instance.codigo,
                    "mesa": str(mesa),
                },
            )
        except Exception:
            pass
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_cliente()
        mesas_qs = Mesa.objects.all()
        productos_qs = Producto.objects.all()
        users_qs = User.objects.all()
        if cliente:
            mesas_qs = mesas_qs.filter(cliente=cliente)
            productos_qs = productos_qs.filter(cliente=cliente)
            users_qs = users_qs.filter(cliente=cliente)
        context["mesas_libres"] = mesas_qs.filter(estado__in=[Mesa.Estado.LIBRE, Mesa.Estado.OCUPADA])
        context["categorias"] = productos_qs.filter(
            activo=True, disponible=True, categoria__isnull=False
        ).values_list("categoria__id", "categoria__nombre", "categoria__icono").distinct()
        context["meseros"] = users_qs.filter(
            role__in=[User.Role.WAITER, User.Role.CASHIER, User.Role.ADMIN, User.Role.MANAGER],
            is_active=True
        ).order_by("first_name", "last_name")
        return context


class ComandaDetailView(ClienteScopeMixin, LoginRequiredMixin, DetailView):
    model = Comanda
    template_name = "comandas/detalle.html"
    context_object_name = "comanda"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_cliente()
        productos_qs = Producto.objects.filter(cliente=cliente)
        context["productos"] = productos_qs.filter(activo=True, disponible=True).select_related("categoria")
        context["categorias"] = productos_qs.filter(
            activo=True, disponible=True, categoria__isnull=False
        ).values_list("categoria__id", "categoria__nombre", "categoria__icono").distinct()
        return context


@login_required
def agregar_item(request, pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso para modificar comandas")
        return redirect("comandas:detalle", pk=pk)
    if request.method == "POST":
        producto_id = request.POST.get("producto")
        cantidad_str = request.POST.get("cantidad", "1")
        notas = request.POST.get("notas", "")

        try:
            cantidad = max(1, int(cantidad_str))
        except (ValueError, TypeError):
            cantidad = 1

        if not producto_id:
            messages.error(request, "Selecciona un producto")
            return redirect("comandas:detalle", pk=pk)

        producto_qs = Producto.objects.filter(cliente=cliente)
        producto = get_object_or_404(producto_qs, pk=producto_id)

        ComandaItem.objects.create(
            comanda=comanda,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            notas=notas,
        )

        try:
            async_to_sync(get_channel_layer().group_send)(
                "comandas",
                {
                    "type": "comanda_update",
                    "comanda_id": comanda.pk,
                    "total": float(comanda.total),
                    "items_count": comanda.items_count,
                },
            )
        except Exception:
            pass
        messages.success(request, f"{cantidad}x {producto.nombre} agregado a la comanda")
    return redirect("comandas:detalle", pk=pk)


@login_required
def enviar_cocina(request, pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:detalle", pk=pk)
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)

    if comanda.estado != Comanda.Estado.ABIERTA:
        messages.error(request, "La comanda ya fue enviada a cocina o esta cerrada")
        return redirect("comandas:detalle", pk=pk)

    if not comanda.items.filter(cancelado=False).exists():
        messages.error(request, "Agrega al menos un producto antes de enviar a cocina")
        return redirect("comandas:detalle", pk=pk)

    comanda.estado = Comanda.Estado.EN_COCINA
    comanda.save()

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "cocina",
                {
                    "type": "comanda_cocina",
                    "comanda_id": comanda.pk,
                    "codigo": comanda.codigo,
                    "mesa": comanda.mesa.numero if comanda.mesa else "N/A",
                    "prioridad": comanda.prioridad,
                    "items_count": comanda.items.filter(cancelado=False).count(),
                },
            )
    except Exception:
        pass

    messages.success(request, f"Comanda {comanda.codigo} enviada a cocina exitosamente")
    return redirect("comandas:detalle", pk=pk)


@login_required
def marcar_listo_item(request, item_pk):
    if not request.user.has_perm("can_view_cocina"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:cocina")
    cliente = getattr(request.user, 'cliente', None)
    qs = ComandaItem.objects.all()
    if cliente:
        qs = qs.filter(comanda__cliente=cliente)
    item = get_object_or_404(qs, pk=item_pk)

    if item.cancelado or item.listo:
        return redirect("comandas:cocina")

    item.listo = True
    item.save()

    comanda = item.comanda
    items_pendientes = comanda.items.filter(cancelado=False, listo=False)
    if not items_pendientes.exists():
        comanda.estado = Comanda.Estado.LISTA
        comanda.save()

    messages.success(request, "Item marcado como listo")
    return redirect("comandas:cocina")


@login_required
def marcar_lista(request, pk):
    if not request.user.has_perm("can_view_cocina"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:cocina")
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)

    if comanda.estado in [Comanda.Estado.CERRADA, Comanda.Estado.CANCELADA, Comanda.Estado.LISTA]:
        messages.error(request, "La comanda ya esta lista o cerrada")
        return redirect("comandas:cocina")

    comanda.items.filter(cancelado=False).update(listo=True)
    comanda.estado = Comanda.Estado.LISTA
    comanda.save()

    messages.success(request, f"Comanda {comanda.codigo} marcada como lista")
    return redirect("comandas:cocina")


@login_required
def cancelar_item(request, item_pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:detalle", pk=item_pk)
    cliente = getattr(request.user, 'cliente', None)
    qs = ComandaItem.objects.all()
    if cliente:
        qs = qs.filter(comanda__cliente=cliente)
    item = get_object_or_404(qs, pk=item_pk)

    if item.cancelado:
        return redirect("comandas:detalle", pk=item.comanda.pk)

    item.cancelado = True
    item.save()
    messages.success(request, "Item cancelado")
    return redirect("comandas:detalle", pk=item.comanda.pk)


@login_required
def cerrar_comanda(request, pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:list")
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)

    if comanda.estado in [Comanda.Estado.CERRADA, Comanda.Estado.CANCELADA]:
        messages.error(request, "La comanda ya esta cerrada")
        return redirect("comandas:list")

    comanda.estado = Comanda.Estado.CERRADA
    comanda.fecha_cierre = timezone.now()
    comanda.save()

    mesas_ocupadas = comanda.mesa.comandas.filter(
        estado__in=[Comanda.Estado.ABIERTA, Comanda.Estado.EN_COCINA]
    )
    if not mesas_ocupadas.exists():
        comanda.mesa.estado = Mesa.Estado.LIBRE
        comanda.mesa.save()

    try:
        async_to_sync(get_channel_layer().group_send)(
            "mesas",
            {
                "type": "mesa_update",
                "mesa_id": comanda.mesa.pk,
                "estado": comanda.mesa.estado,
                "color": comanda.mesa.color_estado,
            },
        )
    except Exception:
        pass

    messages.success(request, f"Comanda {comanda.codigo} cerrada")
    return redirect("comandas:list")


@login_required
def reabrir_comanda(request, pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:list")
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)
    comanda.estado = Comanda.Estado.ABIERTA
    comanda.save()
    messages.success(request, f"Comanda {comanda.codigo} reabierta")
    return redirect("comandas:detalle", pk=pk)


@login_required
def eliminar_comanda(request, pk):
    if not request.user.has_perm("can_manage_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:list")
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)

    facturas = list(comanda.facturas.all())
    if facturas:
        for factura in facturas:
            factura.delete()

    mesa = comanda.mesa
    comanda.delete()

    if mesa and not mesa.comandas.filter(estado__in=[Comanda.Estado.ABIERTA, Comanda.Estado.EN_COCINA]).exists():
        mesa.estado = Mesa.Estado.LIBRE
        mesa.save()

    messages.success(request, f"Comanda eliminada")
    return redirect("comandas:list")


@login_required
def imprimir_cocina(request, pk):
    if not request.user.has_perm("can_view_cocina") and not request.user.has_perm("can_view_comandas"):
        messages.error(request, "No tienes permiso")
        return redirect("comandas:list")
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)
    return render(request, "comandas/imprimir_cocina.html", {"comanda": comanda})


@login_required
def comanda_escpos(request, pk):
    try:
        from core.escpos_utils import build_comanda
        from core.models import ConfigRestaurante
        cliente = getattr(request.user, 'cliente', None)
        qs = Comanda.objects.all()
        if cliente:
            qs = qs.filter(cliente=cliente)
        comanda = get_object_or_404(qs, pk=pk)
        config = ConfigRestaurante.get_config(cliente)
        cols = int(request.GET.get("cols", "32"))
        data = build_comanda(comanda, config, cols=cols)
        return HttpResponse(data, content_type="application/octet-stream")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return HttpResponse(f"Error ESC/POS: {e}\n\n{tb}", content_type="text/plain", status=500)


@login_required
def comanda_escpos_tcp(request, pk):
    from core.escpos_utils import build_comanda, send_tcp
    from core.models import ConfigRestaurante
    host = request.GET.get("host", "")
    port = int(request.GET.get("port", "9100"))
    if not host:
        return HttpResponse("Falta parametro host", status=400)
    cliente = getattr(request.user, 'cliente', None)
    qs = Comanda.objects.all()
    if cliente:
        qs = qs.filter(cliente=cliente)
    comanda = get_object_or_404(qs, pk=pk)
    config = ConfigRestaurante.get_config(cliente)
    data = build_comanda(comanda, config)
    try:
        send_tcp(data, host, port)
        return HttpResponse(f"Impreso en {host}:{port}")
    except Exception as e:
        return HttpResponse(f"Error al imprimir: {e}", status=500)


class VistaCocina(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Comanda
    template_name = "comandas/cocina.html"
    context_object_name = "comandas"
    permission = "can_view_cocina"

    def get_queryset(self):
        return super().get_queryset().filter(
            estado__in=[Comanda.Estado.EN_COCINA, Comanda.Estado.EN_PREPARACION, Comanda.Estado.LISTA]
        ).prefetch_related("items__producto").order_by(
            models.Case(
                models.When(prioridad="urgente", then=models.Value(0)),
                models.When(prioridad="vip", then=models.Value(1)),
                default=models.Value(2),
                output_field=models.IntegerField(),
            ),
            "fecha_creacion",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = ctx["comandas"]
        ctx["urgentes"] = qs.filter(prioridad="urgente").count()
        ctx["vips"] = qs.filter(prioridad="vip").count()
        ctx["normales"] = qs.filter(prioridad="normal").count()
        return ctx
