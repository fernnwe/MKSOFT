from django.contrib import admin
from .models import Comanda, ComandaItem


class ComandaItemInline(admin.TabularInline):
    model = ComandaItem
    extra = 0


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "mesa", "mesero", "estado", "prioridad", "fecha_creacion")
    list_filter = ("estado", "prioridad")
    search_fields = ("codigo",)
    inlines = [ComandaItemInline]


@admin.register(ComandaItem)
class ComandaItemAdmin(admin.ModelAdmin):
    list_display = ("comanda", "producto", "cantidad", "precio_unitario", "listo", "cancelado")
    list_filter = ("listo", "cancelado")
