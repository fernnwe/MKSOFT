from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from core.views import PermissionRequiredMixin
from .models import Producto, Categoria


class ProductoListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Producto
    template_name = "productos/list.html"
    context_object_name = "productos"
    paginate_by = 20
    permission = "can_view_productos"

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
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
        context["categorias"] = Categoria.objects.filter(activo=True)
        context["tipos"] = Producto.Tipo.choices
        cat_id = self.request.GET.get("categoria")
        if cat_id:
            cat = Categoria.objects.filter(id=cat_id).first()
            if cat:
                context["categoria_actual"] = cat.nombre
        return context


class ProductoCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Producto
    template_name = "productos/form.html"
    fields = ["codigo", "nombre", "descripcion", "tipo", "categoria", "precio", "costo", "imagen", "tiempo_preparacion"]
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def form_valid(self, form):
        messages.success(self.request, "Producto creado exitosamente")
        return super().form_valid(form)


class ProductoUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Producto
    template_name = "productos/form.html"
    fields = ["codigo", "nombre", "descripcion", "tipo", "categoria", "precio", "costo", "imagen", "disponible", "tiempo_preparacion"]
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def form_valid(self, form):
        messages.success(self.request, "Producto actualizado exitosamente")
        return super().form_valid(form)


class ProductoDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Producto
    success_url = reverse_lazy("productos:list")
    permission = "can_manage_productos"

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Producto eliminado")
        return super().delete(request, *args, **kwargs)


class CategoriaListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "productos/categorias.html"
    context_object_name = "categorias"
    permission = "can_manage_productos"

    def get_queryset(self):
        return Categoria.objects.all().order_by("orden", "nombre")


class CategoriaCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Categoria
    template_name = "productos/categoria_form.html"
    fields = ["nombre", "descripcion", "icono", "orden"]
    success_url = reverse_lazy("productos:categorias")
    permission = "can_manage_productos"

    def form_valid(self, form):
        messages.success(self.request, "Categoría creada exitosamente")
        return super().form_valid(form)
