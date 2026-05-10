from django.contrib import admin
from django.utils.html import format_html
from .models import DatabaseBackup


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ["nombre", "cliente_display", "tipo", "estado", "tamaño_mb_display", "fecha_creacion", "creado_por"]
    list_filter = ["estado", "tipo", "fecha_creacion", "cliente"]
    search_fields = ["nombre", "notas", "cliente__nombre_negocio"]
    readonly_fields = ["id_backup", "nombre", "fecha_creacion", "tamaño_mb", "estado", "hash_md5", "fecha_restauracion"]
    actions = ["descargar_respaldos"]

    def cliente_display(self, obj):
        if obj.cliente:
            return obj.cliente.nombre_negocio
        return "Global"
    cliente_display.short_description = "Restaurante"

    def tamaño_mb_display(self, obj):
        return f"{obj.tamaño_mb:.2f} MB"
    tamaño_mb_display.short_description = "Tamaño"

    @admin.action(description="Descargar respaldo seleccionado")
    def descargar_respaldos(self, request, queryset):
        if queryset.count() == 1:
            backup = queryset.first()
            if backup.archivo:
                return None
        self.message_user(request, "Selecciona un respaldo para descargar")
