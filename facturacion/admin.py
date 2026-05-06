from django.contrib import admin
from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("folio", "comanda", "cliente_nombre", "total_con_impuestos", "estado", "metodo_pago", "fecha_emision")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("folio", "cliente_nombre", "cliente_rfc")
    date_hierarchy = "fecha_emision"
