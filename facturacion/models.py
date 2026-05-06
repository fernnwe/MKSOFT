from django.db import models
from django.conf import settings
from comandas.models import Comanda


class Factura(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADA = "pagada", "Pagada"
        CANCELADA = "cancelada", "Cancelada"

    class MetodoPago(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"

    folio = models.CharField(max_length=50, unique=True)
    comanda = models.ForeignKey(Comanda, on_delete=models.PROTECT, related_name="facturas")
    cliente_nombre = models.CharField(max_length=200, blank=True)
    cliente_rfc = models.CharField(max_length=13, blank=True)
    cliente_email = models.EmailField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    propina = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sin_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    total_con_impuestos = models.DecimalField(max_digits=10, decimal_places=2)

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices, blank=True)
    notas = models.TextField(blank=True)

    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-fecha_emision"]
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"

    def __str__(self):
        return f"Factura {self.folio} - {self.cliente_nombre or 'Sin cliente'}"

    def save(self, *args, **kwargs):
        if not self.folio:
            import uuid
            self.folio = f"FAC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def total(self):
        return self.total_con_impuestos or 0
