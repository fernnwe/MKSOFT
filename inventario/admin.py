from django.contrib import admin
from .models import Ingrediente, Inventario, MovimientoInventario, Compra, CompraItem, CuentaPorPagar


class MovimientoInline(admin.TabularInline):
    model = MovimientoInventario
    extra = 0


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "stock_minimo")
    list_filter = ("categoria",)
    search_fields = ("nombre", "categoria")


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("ingrediente", "cantidad_actual", "unidad", "costo_unitario", "bajo_stock")
    list_filter = ("unidad",)
    search_fields = ("ingrediente__nombre",)
    inlines = [MovimientoInline]


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("inventario", "tipo", "cantidad", "costo_unitario", "usuario", "fecha")
    list_filter = ("tipo",)


class CompraItemInline(admin.TabularInline):
    model = CompraItem
    extra = 0


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("folio", "proveedor", "estado", "total", "fecha")
    list_filter = ("estado",)
    search_fields = ("proveedor", "folio")
    inlines = [CompraItemInline]


@admin.register(CuentaPorPagar)
class CuentaPorPagarAdmin(admin.ModelAdmin):
    list_display = ("folio", "proveedor", "monto_total", "monto_pagado", "fecha_vencimiento", "estado")
    list_filter = ("estado",)
    search_fields = ("proveedor", "folio")
