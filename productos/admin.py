from django.contrib import admin
from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono", "orden", "activo")
    list_editable = ("orden", "activo")
    ordering = ("orden",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "categoria", "precio", "disponible", "activo")
    list_filter = ("tipo", "categoria", "disponible", "activo")
    search_fields = ("nombre", "codigo", "descripcion")
    list_editable = ("precio", "disponible", "activo")
