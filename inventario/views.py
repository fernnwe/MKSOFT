from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import F, Sum
from django.utils import timezone
from django import forms
from core.views import PermissionRequiredMixin
from .models import Ingrediente, Inventario, MovimientoInventario, Compra, CompraItem, CuentaPorPagar
from core.models import ConfigRestaurante


class InventarioListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Inventario
    template_name = "inventario/list.html"
    context_object_name = "inventario"
    permission = "can_view_inventario"

    def get_queryset(self):
        qs = Inventario.objects.select_related("ingrediente")
        alertas = self.request.GET.get("alertas")
        if alertas == "1":
            qs = qs.filter(cantidad_actual__lte=F("ingrediente__stock_minimo"))
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(ingrediente__nombre__icontains=search)
        return qs


class IngredienteCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Ingrediente
    template_name = "inventario/ingrediente_form.html"
    fields = ["nombre", "descripcion", "categoria", "stock_minimo"]
    success_url = reverse_lazy("inventario:list")
    permission = "can_manage_inventario"

    def form_valid(self, form):
        response = super().form_valid(form)
        Inventario.objects.get_or_create(
            ingrediente=form.instance,
            defaults={"cantidad_actual": 0, "unidad": Ingrediente.Unidad.UNIDAD}
        )
        messages.success(self.request, f"Ingrediente {form.instance.nombre} creado")
        return response

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)


class InventarioCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Inventario
    template_name = "inventario/form.html"
    fields = ["ingrediente", "cantidad_actual", "unidad", "costo_unitario", "proveedor"]
    success_url = reverse_lazy("inventario:list")
    permission = "can_manage_inventario"

    def form_valid(self, form):
        messages.success(self.request, "Producto registrado en inventario")
        return super().form_valid(form)


class InventarioUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Inventario
    template_name = "inventario/form.html"
    fields = ["cantidad_actual", "unidad", "costo_unitario", "proveedor"]
    success_url = reverse_lazy("inventario:list")
    permission = "can_manage_inventario"

    def form_valid(self, form):
        messages.success(self.request, "Inventario actualizado")
        return super().form_valid(form)


class MovimientoListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = MovimientoInventario
    template_name = "inventario/movimientos.html"
    context_object_name = "movimientos"
    paginate_by = 50
    permission = "can_view_inventario"


def registrar_movimiento(request, pk):
    if not request.user.has_perm("can_manage_inventario"):
        messages.error(request, "No tienes permiso")
        return redirect("core:dashboard")
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == "POST":
        tipo = request.POST.get("tipo")
        cantidad_str = request.POST.get("cantidad", "0")
        costo_str = request.POST.get("costo", "0")
        motivo = request.POST.get("motivo", "")

        validos = [t[0] for t in MovimientoInventario.Tipo.choices]
        if tipo not in validos:
            messages.error(request, "Tipo de movimiento no valido")
            return redirect("inventario:list")

        try:
            from decimal import Decimal
            cantidad = Decimal(cantidad_str)
            costo = Decimal(costo_str)
            if cantidad < 0:
                messages.error(request, "La cantidad no puede ser negativa")
                return redirect("inventario:list")
        except Exception:
            messages.error(request, "Cantidad no valida")
            return redirect("inventario:list")

        if tipo in (MovimientoInventario.Tipo.ENTRADA, MovimientoInventario.Tipo.DEVOLUCION):
            inventario.cantidad_actual += cantidad
            if costo > 0:
                inventario.costo_unitario = costo
        elif tipo in (MovimientoInventario.Tipo.SALIDA, MovimientoInventario.Tipo.MERMA):
            inventario.cantidad_actual = max(0, inventario.cantidad_actual - cantidad)
        elif tipo == MovimientoInventario.Tipo.AJUSTE:
            inventario.cantidad_actual = cantidad
            if costo > 0:
                inventario.costo_unitario = costo

        inventario.save()

        MovimientoInventario.objects.create(
            inventario=inventario,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo,
            motivo=motivo,
            usuario=request.user,
        )

        if inventario.bajo_stock:
            messages.warning(request, f"Alerta! {inventario.ingrediente.nombre} tiene stock bajo")
        else:
            messages.success(request, "Movimiento registrado correctamente")

    return redirect("inventario:list")


class CompraItemForm(forms.ModelForm):
    class Meta:
        model = CompraItem
        fields = ["ingrediente", "cantidad", "costo_unitario"]
        widgets = {
            "ingrediente": forms.Select(attrs={"class": "compra-form-input"}),
            "cantidad": forms.NumberInput(attrs={"class": "compra-form-input", "step": "0.001"}),
            "costo_unitario": forms.NumberInput(attrs={"class": "compra-form-input", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Ingrediente.objects.order_by("categoria", "nombre")
        self.fields["ingrediente"].widget = forms.Select(
            choices=[("", "---------")] + [
                (p.pk, f"{p.nombre}{' [' + p.categoria + ']' if p.categoria else ''}") for p in qs
            ],
            attrs={"class": "compra-form-input"},
        )
        self.fields["cantidad"].widget.attrs.update({"class": "compra-form-input", "step": "0.001"})
        self.fields["costo_unitario"].widget.attrs.update({"class": "compra-form-input", "step": "0.01"})
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned = super().clean()
        ing = cleaned.get('ingrediente')
        cant = cleaned.get('cantidad')
        costo = cleaned.get('costo_unitario')
        if not ing and not cant and not costo:
            return cleaned
        if not ing:
            self.add_error('ingrediente', 'Este campo es obligatorio')
        if not cant:
            self.add_error('cantidad', 'Este campo es obligatorio')
        if not costo:
            self.add_error('costo_unitario', 'Este campo es obligatorio')
        return cleaned


CompraItemFormSet = forms.modelformset_factory(
    CompraItem,
    form=CompraItemForm,
    extra=5,
    can_delete=True,
)


class BaseCompraItemFormSet(forms.BaseModelFormSet):
    def clean(self):
        super().clean()
        valid = []
        for form in self.forms:
            if hasattr(form, 'cleaned_data') and form.cleaned_data:
                if form.cleaned_data.get('DELETE'):
                    continue
                if form.cleaned_data.get('ingrediente'):
                    valid.append(form)
        if not valid:
            raise forms.ValidationError("Debes agregar al menos un ingrediente")


def get_compra_item_formset(**kwargs):
    return forms.modelformset_factory(
        CompraItem,
        form=CompraItemForm,
        extra=10,
        can_delete=True,
        formset=BaseCompraItemFormSet,
    )


class CompraListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Compra
    template_name = "inventario/compras.html"
    context_object_name = "compras"
    paginate_by = 20
    permission = "can_manage_inventario"


class CompraCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Compra
    template_name = "inventario/compra_form.html"
    fields = ["proveedor", "notas"]
    success_url = reverse_lazy("inventario:compras")
    permission = "can_manage_inventario"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["proveedor"].widget = forms.TextInput(attrs={
            "class": "compra-form-input",
            "placeholder": "Nombre del proveedor",
        })
        form.fields["notas"].widget = forms.Textarea(attrs={
            "class": "compra-form-input compra-form-textarea",
            "rows": 3,
            "placeholder": "Observaciones opcionales...",
        })
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ItemFormSet = get_compra_item_formset()
        if self.request.POST:
            context["formset"] = ItemFormSet(self.request.POST, prefix="items")
            context["is_post"] = True
        else:
            context["formset"] = ItemFormSet(prefix="items")
            context["is_post"] = False
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            valid_items = []
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get("DELETE"):
                    ing = item_form.cleaned_data.get("ingrediente")
                    cant = item_form.cleaned_data.get("cantidad")
                    costo = item_form.cleaned_data.get("costo_unitario")
                    if ing and cant and costo:
                        valid_items.append((ing, cant, costo))

            form.instance.usuario = self.request.user
            form.instance.estado = Compra.Estado.PENDIENTE
            response = super().form_valid(form)

            for ing, cant, costo in valid_items:
                CompraItem.objects.create(
                    compra=self.object,
                    ingrediente=ing,
                    cantidad=cant,
                    costo_unitario=costo,
                )

            messages.success(self.request, f"Compra {self.object.folio} registrada como pendiente")
            return response
        return self.form_invalid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


class CompraDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Compra
    template_name = "inventario/compra_detalle.html"
    context_object_name = "compra"
    permission = "can_manage_inventario"


class CompraRecibirView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Compra
    template_name = "inventario/compra_detalle.html"
    context_object_name = "compra"
    permission = "can_manage_inventario"

    def post(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        if compra.estado != Compra.Estado.PENDIENTE:
            messages.error(request, "Esta compra ya fue procesada")
            return redirect("inventario:compras")

        for item in compra.items.all():
            inv, created = Inventario.objects.get_or_create(
                ingrediente=item.ingrediente,
                defaults={
                    "cantidad_actual": item.cantidad,
                    "unidad": Ingrediente.Unidad.UNIDAD,
                    "costo_unitario": item.costo_unitario,
                    "proveedor": compra.proveedor,
                }
            )
            if not created:
                inv.cantidad_actual += item.cantidad
                inv.costo_unitario = item.costo_unitario
                inv.proveedor = compra.proveedor
                inv.save()

            MovimientoInventario.objects.create(
                inventario=inv,
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad=item.cantidad,
                costo_unitario=item.costo_unitario,
                motivo=f"Compra {compra.folio}",
                usuario=request.user,
            )

        compra.estado = Compra.Estado.RECIBIDA
        compra.save()

        config = ConfigRestaurante.get_config()
        dias = config.dias_credito_proveedor

        CuentaPorPagar.objects.create(
            proveedor=compra.proveedor,
            compra=compra,
            monto_total=compra.total,
            fecha_vencimiento=timezone.now().date() + timezone.timedelta(days=dias),
            usuario=request.user,
            estado=CuentaPorPagar.Estado.PENDIENTE,
        )

        messages.success(request, f"Compra {compra.folio} recibida - Inventario actualizado - Cuenta por pagar generada")
        return redirect("inventario:compras")


class CompraCancelarView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Compra
    template_name = "inventario/compra_detalle.html"
    context_object_name = "compra"
    permission = "can_manage_inventario"

    def post(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        if compra.estado == Compra.Estado.RECIBIDA:
            messages.error(request, "No puedes cancelar una compra ya recibida")
            return redirect("inventario:compras")
        compra.estado = Compra.Estado.CANCELADA
        compra.save()
        messages.success(request, f"Compra {compra.folio} cancelada")
        return redirect("inventario:compras")


class CompraDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Compra
    success_url = reverse_lazy("inventario:compras")
    permission = "can_manage_inventario"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            folio = self.object.folio
            self.object.delete()
            messages.success(request, f"Compra {folio} eliminada")
        except Exception:
            messages.error(request, "No se puede eliminar: tiene datos asociados")
        return redirect(self.success_url)


class CuentaPorPagarListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = CuentaPorPagar
    template_name = "inventario/cuentas_list.html"
    context_object_name = "cuentas"
    paginate_by = 20
    permission = "can_manage_inventario"

    def get_queryset(self):
        qs = CuentaPorPagar.objects.select_related("compra")
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        proveedor = self.request.GET.get("proveedor")
        if proveedor:
            qs = qs.filter(proveedor__icontains=proveedor)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_pendiente"] = CuentaPorPagar.objects.filter(
            estado__in=["pendiente", "parcial", "vencida"]
        ).aggregate(total=Sum(F("monto_total") - F("monto_pagado")))["total"] or 0
        context["cuentas_vencidas"] = CuentaPorPagar.objects.filter(estado="vencida").count()
        return context


class CuentaPorPagarCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = CuentaPorPagar
    template_name = "inventario/cuenta_form.html"
    fields = ["proveedor", "monto_total", "fecha_vencimiento", "notas"]
    success_url = reverse_lazy("inventario:cuentas")
    permission = "can_manage_inventario"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.monto_pagado = 0
        form.instance.estado = CuentaPorPagar.Estado.PENDIENTE
        response = super().form_valid(form)
        messages.success(self.request, f"Cuenta {form.instance.folio} creada")
        return response


class CuentaPorPagarDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = CuentaPorPagar
    template_name = "inventario/cuenta_detalle.html"
    context_object_name = "cuenta"
    permission = "can_manage_inventario"


class CuentaPorPagarPagoView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = CuentaPorPagar
    template_name = "inventario/cuenta_detalle.html"
    context_object_name = "cuenta"
    permission = "can_manage_inventario"

    def post(self, request, pk):
        cuenta = get_object_or_404(CuentaPorPagar, pk=pk)
        if cuenta.estado in (CuentaPorPagar.Estado.PAGADA, CuentaPorPagar.Estado.CANCELADA):
            messages.error(request, "Esta cuenta ya fue procesada")
            return redirect("inventario:cuentas")
        monto_str = request.POST.get("monto", "")
        try:
            from decimal import Decimal
            monto = Decimal(monto_str)
            if monto <= 0:
                messages.error(request, "El monto debe ser mayor a 0")
                return redirect("inventario:cuenta_detalle", pk=pk)
            if monto > cuenta.monto_pendiente:
                messages.error(request, f"El monto no puede ser mayor a {cuenta.monto_pendiente}")
                return redirect("inventario:cuenta_detalle", pk=pk)
        except Exception:
            messages.error(request, "Monto no valido")
            return redirect("inventario:cuenta_detalle", pk=pk)
        cuenta.registrar_pago(monto, request.user)
        messages.success(request, f"Pago registrado - {cuenta.monto_pendiente} pendiente")
        return redirect("inventario:cuenta_detalle", pk=pk)


class CuentaPorPagarCancelarView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = CuentaPorPagar
    template_name = "inventario/cuenta_detalle.html"
    context_object_name = "cuenta"
    permission = "can_manage_inventario"

    def post(self, request, pk):
        cuenta = get_object_or_404(CuentaPorPagar, pk=pk)
        if cuenta.estado == CuentaPorPagar.Estado.PAGADA:
            messages.error(request, "No puedes cancelar una cuenta ya pagada")
            return redirect("inventario:cuentas")
        cuenta.estado = CuentaPorPagar.Estado.CANCELADA
        cuenta.save()
        messages.success(request, f"Cuenta {cuenta.folio} cancelada")
        return redirect("inventario:cuentas")


class CuentaPorPagarDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = CuentaPorPagar
    success_url = reverse_lazy("inventario:cuentas")
    permission = "can_manage_inventario"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            folio = self.object.folio
            self.object.delete()
            messages.success(request, f"Cuenta {folio} eliminada")
        except Exception:
            messages.error(request, "No se puede eliminar: tiene datos asociados")
        return redirect(self.success_url)
