from django.db import models
from django.conf import settings
from mesas.models import Mesa


class Comanda(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        EN_COCINA = "en_cocina", "En Cocina"
        EN_PREPARACION = "en_preparacion", "En Preparación"
        LISTA = "lista", "Lista para Servir"
        SERVING = "sirviendo", "Sirviendo"
        CERRADA = "cerrada", "Cerrada"
        CANCELADA = "cancelada", "Cancelada"

    class Prioridad(models.TextChoices):
        NORMAL = "normal", "Normal"
        URGENTE = "urgente", "Urgente"
        VIP = "vip", "VIP"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="comandas")
    codigo = models.CharField(max_length=20)
    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name="comandas")
    mesero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="comandas"
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.NORMAL)
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Comanda"
        verbose_name_plural = "Comandas"
        constraints = [
            models.UniqueConstraint(fields=["cliente", "codigo"], name="unique_comanda_codigo_per_cliente"),
        ]

    def __str__(self):
        return f"Comanda {self.codigo} - Mesa {self.mesa.numero}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            import uuid
            self.codigo = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_impuestos(self):
        from django.conf import settings
        from decimal import Decimal
        return self.total * Decimal(str(settings.TAX_RATE))

    @property
    def total_con_impuestos(self):
        return self.total + self.total_impuestos

    @property
    def items_count(self):
        return self.items.aggregate(total=models.Sum("cantidad"))["total"] or 0


class ComandaItem(models.Model):
    comanda = models.ForeignKey(Comanda, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True)
    enviado_cocina = models.BooleanField(default=False)
    listo = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_creacion"]
        verbose_name = "Item de Comanda"
        verbose_name_plural = "Items de Comanda"

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"

    @property
    def subtotal(self):
        if self.cancelado:
            return 0
        return self.cantidad * self.precio_unitario
