from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from core.views import PermissionRequiredMixin
from .models import Mesa


class MesaListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Mesa
    template_name = "mesas/list.html"
    context_object_name = "mesas"
    permission = "can_view_mesas"

    def get_queryset(self):
        qs = super().get_queryset()
        zona = self.request.GET.get("zona")
        estado = self.request.GET.get("estado")
        if zona:
            qs = qs.filter(zona=zona)
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class MesaCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Mesa
    template_name = "mesas/form.html"
    fields = ["numero", "zona", "capacidad", "estado", "descripcion"]
    success_url = reverse_lazy("mesas:list")
    permission = "can_view_mesas"

    def form_valid(self, form):
        messages.success(self.request, "Mesa creada exitosamente")
        return super().form_valid(form)


class MesaUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Mesa
    template_name = "mesas/form.html"
    fields = ["numero", "zona", "capacidad", "estado", "descripcion"]
    success_url = reverse_lazy("mesas:list")
    permission = "can_view_mesas"

    def form_valid(self, form):
        messages.success(self.request, "Mesa actualizada exitosamente")
        return super().form_valid(form)


class MesaDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Mesa
    success_url = reverse_lazy("mesas:list")
    permission = "can_view_mesas"

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        numero = self.object.numero
        try:
            self.object.delete()
            messages.success(request, f"Mesa {numero} eliminada")
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar Mesa {numero}: tiene comandas asociadas"
            )
        return redirect(self.success_url)


class MesaPlanoView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Mesa
    template_name = "mesas/plano.html"
    context_object_name = "mesas"
    permission = "can_view_mesas"

    def get_queryset(self):
        zona = self.request.GET.get("zona")
        if zona:
            return Mesa.objects.filter(zona=zona)
        return Mesa.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["zonas"] = Mesa.Zona.choices
        return context


def cambiar_estado_mesa(request, pk, estado):
    mesa = get_object_or_404(Mesa, pk=pk)
    if not request.user.has_perm("can_view_mesas"):
        messages.error(request, "No tienes permiso")
        return redirect("core:dashboard")
    validos = [e[0] for e in Mesa.Estado.choices]
    if estado not in validos:
        messages.error(request, "Estado no valido")
        return redirect("mesas:plano")
    mesa.estado = estado
    mesa.save()

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "mesas",
            {
                "type": "mesa_update",
                "mesa_id": mesa.pk,
                "estado": mesa.estado,
                "color": mesa.color_estado,
            },
        )
    except Exception:
        pass

    messages.success(request, f"Estado de Mesa {mesa.numero} cambiado a {mesa.get_estado_display()}")
    return redirect("mesas:plano")
