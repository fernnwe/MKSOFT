import os
import uuid
from datetime import datetime
from django.db import models
from django.conf import settings


def backup_upload_path(instance, filename):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cliente_prefix = f"cliente_{instance.cliente_id}" if instance.cliente_id else "global"
    return f"respaldos/{cliente_prefix}/{timestamp}_{instance.id}_{filename}"


TENANT_APPS = [
    "mesas.Mesa",
    "productos.Categoria",
    "productos.Producto",
    "inventario.Ingrediente",
    "inventario.Inventario",
    "inventario.MovimientoInventario",
    "inventario.Receta",
    "inventario.Compra",
    "inventario.CompraItem",
    "inventario.CuentaPorPagar",
    "comandas.Comanda",
    "comandas.ComandaItem",
    "facturacion.Factura",
    "facturacion.CajaApertura",
    "facturacion.CajaMovimiento",
    "meseros.Mesero",
]


class DatabaseBackup(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EXITOSO = "exitoso", "Exitoso"
        FALLIDO = "fallido", "Fallido"
        RESTAURANDO = "restaurando", "Restaurando"
        RESTAURADO = "restaurado", "Restaurado"

    class Tipo(models.TextChoices):
        COMPLETO = "completo", "Completo (Superadmin)"
        TENANT = "tenant", "Por Restaurante"

    id_backup = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255, editable=False)
    archivo = models.FileField(upload_to="respaldos/", blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    tamaño_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="respaldos_creados",
    )
    cliente = models.ForeignKey(
        "core.Cliente",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="respaldos",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.TENANT)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    notas = models.TextField(blank=True, default="")
    fecha_restauracion = models.DateTimeField(null=True, blank=True)
    restaurado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respaldos_restaurados",
    )
    hash_md5 = models.CharField(max_length=32, blank=True, editable=False, help_text="Hash de integridad del respaldo")

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Respaldo de Base de Datos"
        verbose_name_plural = "Respaldos de Base de Datos"

    def __str__(self):
        cliente_str = f" - {self.cliente.nombre_negocio}" if self.cliente else ""
        return f"Respaldo {self.nombre}{cliente_str} ({self.fecha_creacion:%d/%m/%Y %H:%M})"

    def tamaño_formateado(self):
        if self.tamaño_mb >= 1024:
            return f"{self.tamaño_mb / 1024:.2f} GB"
        return f"{self.tamaño_mb:.2f} MB"

    def calcular_tamaño(self):
        if self.archivo and os.path.exists(self.archivo.path):
            bytes_size = os.path.getsize(self.archivo.path)
            self.tamaño_mb = round(bytes_size / (1024 * 1024), 2)
            self.save(update_fields=["tamaño_mb"])

    def eliminar_archivo(self):
        if self.archivo and os.path.exists(self.archivo.path):
            os.remove(self.archivo.path)
