from django.contrib import admin
from .models import Mesa


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("numero", "zona", "capacidad", "estado")
    list_filter = ("zona", "estado")
    list_editable = ("estado",)
    ordering = ("numero",)
