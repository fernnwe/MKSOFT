from django.contrib import admin
from .models import Mesero


@admin.register(Mesero)
class MeseroAdmin(admin.ModelAdmin):
    list_display = ("usuario", "codigo_pin", "activo", "comandas_atendidas", "propinas_total")
    list_filter = ("activo",)
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name")
