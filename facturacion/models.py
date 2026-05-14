from django.db import models
from django.conf import settings
from comandas.models import Comanda


class CajaApertura(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="cajas_apertura")
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usuario_apertura = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="cajas_abiertas")
    usuario_cierre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="cajas_cerradas")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    notas = models.TextField(blank=True)
    monto_cierre_efectivo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-fecha_apertura"]
        verbose_name = "Apertura de Caja"
        verbose_name_plural = "Aperturas de Caja"

    def __str__(self):
        return f"Caja {self.pk} - {self.fecha_apertura.strftime('%d/%m/%Y %H:%M')} ({self.get_estado_display()})"

    def cerrar(self, monto_cierre, usuario):
        self.fecha_cierre = models.functions.Now()
        self.usuario_cierre = usuario
        self.estado = self.Estado.CERRADA
        self.monto_cierre_efectivo = monto_cierre
        from django.db.models import Sum
        facturas_efectivo = Factura.objects.filter(
            fecha_emision__gte=self.fecha_apertura,
            fecha_emision__lte=self.fecha_cierre,
            estado=Factura.Estado.PAGADA,
            metodo_pago=Factura.MetodoPago.EFECTIVO
        ).aggregate(total=Sum("total_con_impuestos"))["total"] or 0
        total_gastos = self.movimientos.filter(
            tipo=CajaMovimiento.Tipo.GASTO
        ).aggregate(total=Sum("monto"))["total"] or 0
        total_retiros = self.movimientos.filter(
            tipo=CajaMovimiento.Tipo.RETIRO
        ).aggregate(total=Sum("monto"))["total"] or 0
        efectivo_esperado = self.monto_inicial + facturas_efectivo - total_gastos - total_retiros
        self.diferencia = monto_cierre - efectivo_esperado
        self.save()


class Factura(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADA = "pagada", "Pagada"
        CANCELADA = "cancelada", "Cancelada"

    class MetodoPago(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"

    class Tipo(models.TextChoices):
        MESA = "mesa", "Mesa"
        LLEVAR = "llevar", "Para llevar"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="facturas")
    folio = models.CharField(max_length=50)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.MESA)
    comanda = models.ForeignKey(Comanda, on_delete=models.PROTECT, related_name="facturas", null=True, blank=True)
    items_json = models.TextField(blank=True, help_text="Items en formato JSON (para llevar)")
    cliente_nombre = models.CharField(max_length=200, blank=True)
    cliente_rfc = models.CharField(max_length=13, blank=True, verbose_name="RUC del cliente")
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

    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Monto recibido del cliente en efectivo")
    cambio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cambio a devolver al cliente")

    divisa_nombre = models.CharField(max_length=10, blank=True, help_text="Ej: USD, EUR")
    divisa_monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Equivalente en otra moneda")
    divisa_tasa = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Tasa de cambio usada")

    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-fecha_emision"]
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        constraints = [
            models.UniqueConstraint(fields=["cliente", "folio"], name="unique_factura_folio_per_cliente"),
        ]

    def __str__(self):
        return f"Factura {self.folio} - {self.cliente_nombre or 'Sin cliente'}"

    def save(self, *args, **kwargs):
        if not self.folio:
            import uuid
            for _ in range(5):
                self.folio = f"FAC-{uuid.uuid4().hex[:8].upper()}"
                if not Factura.objects.filter(cliente=self.cliente, folio=self.folio).exists():
                    break
        super().save(*args, **kwargs)

    @property
    def total(self):
        return self.total_con_impuestos or 0

    @property
    def items(self):
        if self.items_json:
            import json
            try:
                return json.loads(self.items_json)
            except (json.JSONDecodeError, TypeError):
                return []
        if self.comanda:
            return self.comanda.items.filter(cancelado=False)
        return []


class CajaMovimiento(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = "ingreso", "Ingreso"
        GASTO = "gasto", "Gasto"
        RETIRO = "retiro", "Retiro"

    caja = models.ForeignKey(CajaApertura, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    factura = models.ForeignKey(Factura, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_caja")

    class Meta:
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.monto} ({self.descripcion})"
