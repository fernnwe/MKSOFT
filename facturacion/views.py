from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Exists, OuterRef
from django.conf import settings
from django import forms
from core.views import PermissionRequiredMixin
from .models import Factura
from comandas.models import Comanda
from inventario.models import Compra, CuentaPorPagar


class FacturaListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Factura
    template_name = "facturacion/list.html"
    context_object_name = "facturas"
    paginate_by = 20
    permission = "can_view_facturacion"

    def get_queryset(self):
        qs = Factura.objects.select_related("comanda")
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        fecha = self.request.GET.get("fecha")
        if fecha:
            try:
                from datetime import datetime
                f = datetime.strptime(fecha, "%Y-%m-%d").date()
                start = timezone.make_aware(timezone.datetime.combine(f, timezone.datetime.min.time()))
                end = timezone.make_aware(timezone.datetime.combine(f, timezone.datetime.max.time()))
                qs = qs.filter(fecha_emision__gte=start, fecha_emision__lte=end)
            except (ValueError, OverflowError):
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estados"] = Factura.Estado.choices
        context["total_ventas"] = self.get_queryset().filter(estado=Factura.Estado.PAGADA).aggregate(
            total=Sum("total_con_impuestos")
        )["total"] or 0
        return context


from django import forms

class FacturaForm(forms.ModelForm):
    aplicar_servicio = forms.BooleanField(
        label="Aplicar servicio del 10%",
        initial=True,
        required=False
    )

    class Meta:
        model = Factura
        fields = ["comanda", "cliente_nombre", "cliente_rfc", "cliente_email", "metodo_pago", "descuento"]


class FacturaCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Factura
    form_class = FacturaForm
    template_name = "facturacion/crear.html"
    success_url = reverse_lazy("facturacion:list")
    permission = "can_create_facturas"

    def get_initial(self):
        initial = super().get_initial()
        comanda_id = self.request.GET.get("comanda")
        if comanda_id:
            initial["comanda"] = comanda_id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        comandas_con_factura = Factura.objects.filter(comanda=OuterRef("pk"))
        form.fields["comanda"].queryset = Comanda.objects.filter(
            estado__in=[Comanda.Estado.ABIERTA, Comanda.Estado.EN_COCINA, Comanda.Estado.EN_PREPARACION,
                        Comanda.Estado.LISTA, Comanda.Estado.SERVING, Comanda.Estado.CERRADA]
        ).exclude(Exists(comandas_con_factura)).order_by("-fecha_creacion")
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comanda_id = self.request.GET.get("comanda")
        if comanda_id:
            comanda = Comanda.objects.filter(id=comanda_id).first()
            if comanda:
                context["preview"] = {
                    "subtotal": comanda.total,
                    "servicio": comanda.total * 10 / 100,
                    "total_sin_servicio": comanda.total,
                    "total_con_servicio": comanda.total + comanda.total * 10 / 100,
                }
        return context

    def form_valid(self, form):
        comanda = form.cleaned_data["comanda"]
        aplicar_servicio = form.cleaned_data.get("aplicar_servicio", False)
        descuento = form.cleaned_data.get("descuento", 0)
        servicio = comanda.total * 10 / 100 if aplicar_servicio else 0

        form.instance.subtotal = comanda.total
        form.instance.impuestos = 0
        form.instance.total_sin_impuestos = comanda.total
        form.instance.propina = servicio
        form.instance.descuento = descuento
        form.instance.total_con_impuestos = comanda.total + servicio - descuento
        form.instance.usuario = self.request.user
        form.instance.estado = Factura.Estado.PAGADA
        form.instance.fecha_pago = timezone.now()

        response = super().form_valid(form)
        messages.success(self.request, f"Factura {form.instance.folio} generada")
        return response


class FacturaDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Factura
    template_name = "facturacion/detalle.html"
    context_object_name = "factura"
    permission = "can_view_facturacion"


class FacturaDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Factura
    success_url = reverse_lazy("facturacion:list")
    permission = "can_cancel_facturas"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f"Factura {self.object.folio} eliminada")
        return super().post(request, *args, **kwargs)


def imprimir_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render(request, "facturacion/imprimir.html", {"factura": factura})


class CierreCajaView(PermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "facturacion/cierre_caja.html"
    permission = "can_view_facturacion"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha_str = self.request.GET.get("fecha")
        if fecha_str:
            from datetime import datetime
            hoy = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        else:
            hoy = timezone.localtime(timezone.now()).date()

        start = timezone.make_aware(timezone.datetime.combine(hoy, timezone.datetime.min.time()))
        end = timezone.make_aware(timezone.datetime.combine(hoy, timezone.datetime.max.time()))

        facturas_dia = Factura.objects.filter(fecha_emision__gte=start, fecha_emision__lte=end)

        context["hoy"] = hoy
        context["fecha_cierre"] = timezone.now()

        facturas_pagadas = facturas_dia.filter(estado=Factura.Estado.PAGADA)
        facturas_canceladas = facturas_dia.filter(estado=Factura.Estado.CANCELADA)
        facturas_pendientes = facturas_dia.filter(estado=Factura.Estado.PENDIENTE)

        context["total_facturas"] = facturas_dia.count()
        context["facturas_pagadas_count"] = facturas_pagadas.count()
        context["facturas_canceladas_count"] = facturas_canceladas.count()
        context["facturas_pendientes_count"] = facturas_pendientes.count()

        total_ventas = facturas_pagadas.aggregate(total=Sum("total_con_impuestos"))["total"] or 0
        total_servicio = facturas_pagadas.aggregate(servicio=Sum("propina"))["servicio"] or 0
        total_descuentos = facturas_pagadas.aggregate(descuento=Sum("descuento"))["descuento"] or 0
        context["total_ventas"] = total_ventas
        context["total_servicio"] = total_servicio
        context["total_descuentos"] = total_descuentos
        context["total_neto"] = total_ventas - total_descuentos

        efectivo = facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.EFECTIVO).aggregate(
            total=Sum("total_con_impuestos")
        )["total"] or 0
        tarjeta = facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.TARJETA).aggregate(
            total=Sum("total_con_impuestos")
        )["total"] or 0
        transferencia = facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.TRANSFERENCIA).aggregate(
            total=Sum("total_con_impuestos")
        )["total"] or 0

        context["total_efectivo"] = efectivo
        context["total_tarjeta"] = tarjeta
        context["total_transferencia"] = transferencia

        ventas_por_metodo = [
            {"metodo": "Efectivo", "icono": "bi-cash-coin", "total": efectivo, "count": facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.EFECTIVO).count()},
            {"metodo": "Tarjeta", "icono": "bi-credit-card", "total": tarjeta, "count": facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.TARJETA).count()},
            {"metodo": "Transferencia", "icono": "bi-bank", "total": transferencia, "count": facturas_pagadas.filter(metodo_pago=Factura.MetodoPago.TRANSFERENCIA).count()},
        ]
        if total_ventas > 0:
            for item in ventas_por_metodo:
                item["percent"] = round((item["total"] / total_ventas) * 100)
        else:
            for item in ventas_por_metodo:
                item["percent"] = 0

        context["ventas_por_metodo"] = ventas_por_metodo

        context["facturas_detalladas"] = facturas_pagadas.select_related("comanda", "usuario").order_by("fecha_emision")
        context["facturas_canceladas_detalladas"] = facturas_canceladas.select_related("comanda", "usuario").order_by("fecha_emision")

        comandas_cerradas = Comanda.objects.filter(fecha_cierre__gte=start, fecha_cierre__lte=end)
        context["comandas_cerradas_count"] = comandas_cerradas.count()
        context["fecha_seleccionada"] = hoy

        compras_dia = Compra.objects.filter(fecha__gte=start, fecha__lte=end)
        compras_recibidas = compras_dia.filter(estado=Compra.Estado.RECIBIDA)
        compras_pendientes = compras_dia.filter(estado=Compra.Estado.PENDIENTE)
        compras_canceladas = compras_dia.filter(estado=Compra.Estado.CANCELADA)

        total_compras = sum(c.total for c in compras_recibidas)

        context["compras_recibidas_count"] = compras_recibidas.count()
        context["compras_pendientes_count"] = compras_pendientes.count()
        context["compras_canceladas_count"] = compras_canceladas.count()
        context["total_compras"] = total_compras
        context["compras_detalladas"] = compras_recibidas.prefetch_related("items").order_by("fecha")

        context["balance_neto"] = total_ventas - total_compras
        context["balance_color"] = "success" if (total_ventas - total_compras) >= 0 else "danger"

        return context
