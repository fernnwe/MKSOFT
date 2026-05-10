from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import IntegrityError, models
from core.views import ClienteScopeMixin, PermissionRequiredMixin
from .models import Producto, Categoria
from comandas.models import ComandaItem


def _limpiar_huerfanos(cliente):
    if not cliente:
        return
    Producto.objects.filter(
        cliente=cliente,
        categoria__isnull=True
    ).annotate(
        has_items=models.Exists(ComandaItem.objects.filter(producto=models.OuterRef('pk')))
    ).filter(has_items=False).delete()


def _categorias_para_cliente(cliente):
    qs = Categoria.objects.filter(activo=True)
    if cliente:
        qs = qs.filter(cliente=cliente)
    return qs


class ProductoListView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Producto
    template_name = "productos/list.html"
    context_object_name = "productos"
    paginate_by = 20
    permission = "can_view_productos"

    def get_queryset(self):
        cliente = self.get_cliente()
        _limpiar_huerfanos(cliente)
        qs = super().get_queryset().select_related("categoria")
        tipo = self.request.GET.get("tipo")
        categoria = self.request.GET.get("categoria")
        if tipo:
            qs = qs.filter(tipo=tipo)
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(nombre__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_cliente()
        cat_qs = _categorias_para_cliente(cliente)
        context["categorias"] = cat_qs.annotate(
            productos_count=models.Count("productos", filter=models.Q(productos__activo=True))
        )
        context["tipos"] = Producto.Tipo.choices
        cat_id = self.request.GET.get("categoria")
        if cat_id:
            cat = cat_qs.filter(id=cat_id).first()
            if cat:
                context["categoria_actual"] = cat.nombre
        return context


class ProductoCreateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Producto
    template_name = "productos/form.html"
    fields = ["codigo", "nombre", "descripcion", "tipo", "categoria", "precio", "costo", "imagen", "tiempo_preparacion"]
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Producto creado exitosamente")
        return response

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        cliente = self.get_cliente()
        _limpiar_huerfanos(cliente)
        form.fields["categoria"].queryset = _categorias_para_cliente(cliente)
        return form


class ProductoUpdateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Producto
    template_name = "productos/form.html"
    fields = ["codigo", "nombre", "descripcion", "tipo", "categoria", "precio", "costo", "imagen", "disponible", "tiempo_preparacion"]
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Producto actualizado exitosamente")
        return response

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        cliente = self.get_cliente()
        form.fields["categoria"].queryset = _categorias_para_cliente(cliente)
        return form


class ProductoDeleteView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Producto
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        try:
            super().delete(request, *args, **kwargs)
            messages.success(request, f"Producto '{nombre}' eliminado permanentemente")
        except Exception as e:
            messages.error(request, f"No se pudo eliminar '{nombre}': {str(e)}")
        return redirect(self.success_url)


class CategoriaListView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "productos/categorias.html"
    context_object_name = "categorias"
    permission = "can_manage_productos"

    def get_queryset(self):
        qs = super().get_queryset()
        cliente = self.get_cliente()
        if cliente:
            qs = qs.filter(cliente=cliente)
        return qs.annotate(
            productos_count=models.Count("productos", filter=models.Q(productos__activo=True))
        ).order_by("orden", "nombre")


class CategoriaCreateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Categoria
    template_name = "productos/categoria_form.html"
    fields = ["nombre", "descripcion", "icono", "orden"]
    success_url = reverse_lazy("productos:categorias")
    permission = "can_manage_productos"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Categoria creada exitosamente")
        return response


class CategoriaDeleteView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Categoria
    template_name = "productos/categoria_eliminar.html"
    success_url = reverse_lazy("productos:categorias")
    permission = "can_manage_productos"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        self.object.productos.update(categoria=None)
        self.object.delete()
        messages.success(request, f"Categoria '{nombre}' eliminada")
        return redirect(self.success_url)


def productos_pdf(request):
    from django.http import HttpResponse
    from core.pdf_utils import generate_productos_pdf
    from core.models import ConfigRestaurante

    cliente = getattr(request.user, "cliente", None)
    config = ConfigRestaurante.get_config(cliente)
    qs = Producto.objects.filter(activo=True).order_by("categoria__orden", "nombre").select_related("categoria")
    if cliente:
        qs = qs.filter(cliente=cliente)

    buffer = generate_productos_pdf(qs, config.nombre, config.simbolo_moneda)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="productos.pdf"'
    return response
