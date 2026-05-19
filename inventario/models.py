from django.db import models


class Ingrediente(models.Model):
    class Unidad(models.TextChoices):
        UNIDAD = "unidad", "Unidad"
        KILO = "kilo", "Kilogramo"
        GRAMO = "gramo", "Gramo"
        LITRO = "litro", "Litro"
        MILILITRO = "ml", "Mililitro"
        CAJA = "caja", "Caja"
        PIEZA = "pieza", "Pieza"
        BOLSA = "bolsa", "Bolsa"
        PAQUETE = "paquete", "Paquete"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="ingredientes")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=100, blank=True, help_text="Ej: Lacteos, Carnes, Verduras")
    activo = models.BooleanField(default=True)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Stock minimo para alerta")

    class Meta:
        ordering = ["categoria", "nombre"]
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"
        constraints = [
            models.UniqueConstraint(fields=["cliente", "nombre"], name="unique_ingrediente_per_cliente"),
        ]

    def __str__(self):
        return f"{self.nombre}"


class Proveedor(models.Model):
    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="proveedores")
    nombre = models.CharField(max_length=200)
    contacto = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        constraints = [
            models.UniqueConstraint(fields=["cliente", "nombre"], name="unique_proveedor_per_cliente"),
        ]

    def __str__(self):
        return self.nombre


class Inventario(models.Model):
    ingrediente = models.OneToOneField(Ingrediente, on_delete=models.CASCADE, related_name="inventario")
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=20, choices=Ingrediente.Unidad.choices, default=Ingrediente.Unidad.UNIDAD)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    proveedor = models.CharField(max_length=200, blank=True)
    proveedor_fk = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventarios")
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventario"
        indexes = [
            models.Index(fields=["ingrediente", "cantidad_actual"], name="inv_ingrediente_cantidad"),
        ]

    def __str__(self):
        return f"{self.ingrediente.nombre}: {self.cantidad_actual} {self.unidad}"

    @property
    def bajo_stock(self):
        return self.cantidad_actual <= self.ingrediente.stock_minimo

    @property
    def valor_total(self):
        return self.cantidad_actual * self.costo_unitario


    def save(self, *args, **kwargs):
        if self.proveedor_fk:
            self.proveedor = self.proveedor_fk.nombre
        super().save(*args, **kwargs)


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"
        AJUSTE = "ajuste", "Ajuste"
        MERMA = "merma", "Merma"
        DEVOLUCION = "devolucion", "Devolucion"

    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    motivo = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.inventario.ingrediente.nombre} ({self.cantidad})"

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario


class Compra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RECIBIDA = "recibida", "Recibida"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="compras")
    proveedor = models.CharField(max_length=200)
    proveedor_fk = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras")
    folio = models.CharField(max_length=50, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        indexes = [
            models.Index(fields=["cliente", "estado", "fecha"], name="compra_cliente_estado_fecha"),
        ]

    def __str__(self):
        return f"Compra {self.folio} - {self.proveedor}"

    def save(self, *args, **kwargs):
        if self.proveedor_fk:
            self.proveedor = self.proveedor_fk.nombre
        if not self.folio:
            import uuid
            self.folio = f"COMP-{uuid.uuid4().hex[:8].upper()}"
            for attempt in range(10):
                if not Compra.objects.filter(cliente=self.cliente, folio=self.folio).exists():
                    break
                self.folio = f"COMP-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class CompraItem(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="items")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Item de Compra"
        verbose_name_plural = "Items de Compra"

    def __str__(self):
        return f"{self.cantidad}x {self.ingrediente.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario


class CuentaPorPagar(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PARCIAL = "parcial", "Pago Parcial"
        PAGADA = "pagada", "Pagada"
        VENCIDA = "vencida", "Vencida"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey("core.Cliente", on_delete=models.CASCADE, related_name="cuentas_por_pagar")
    proveedor = models.CharField(max_length=200)
    proveedor_fk = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="cuentas_por_pagar")
    folio = models.CharField(max_length=50, blank=True)
    compra = models.ForeignKey(Compra, on_delete=models.SET_NULL, null=True, blank=True, related_name="cuentas_por_pagar")
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    fecha_pago = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["fecha_vencimiento"]
        verbose_name = "Cuenta por Pagar"
        verbose_name_plural = "Cuentas por Pagar"

    def __str__(self):
        return f"{self.folio} - {self.proveedor} ({self.monto_total})"

    def save(self, *args, **kwargs):
        if self.proveedor_fk:
            self.proveedor = self.proveedor_fk.nombre
        if not self.folio:
            import uuid
            self.folio = f"CP-{uuid.uuid4().hex[:8].upper()}"
        from datetime import date
        if self.estado not in (self.Estado.PAGADA, self.Estado.CANCELADA) and self.fecha_vencimiento < date.today():
            self.estado = self.Estado.VENCIDA
        super().save(*args, **kwargs)

    @property
    def monto_pendiente(self):
        return self.monto_total - self.monto_pagado

    @property
    def vencida(self):
        from datetime import date
        return self.estado not in (self.Estado.PAGADA, self.Estado.CANCELADA) and self.fecha_vencimiento < date.today()

    def registrar_pago(self, monto, usuario=None):
        if self.estado == self.Estado.PAGADA:
            return
        self.monto_pagado += monto
        if self.monto_pagado >= self.monto_total:
            self.monto_pagado = self.monto_total
            self.estado = self.Estado.PAGADA
            from django.utils import timezone
            self.fecha_pago = timezone.now().date()
        elif self.monto_pagado > 0:
            self.estado = self.Estado.PARCIAL
        self.save()

class Receta(models.Model):
    producto = models.ForeignKey("productos.Producto", on_delete=models.CASCADE, related_name="receta_ingredientes")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE, related_name="recetas")
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=20, choices=Ingrediente.Unidad.choices, default=Ingrediente.Unidad.UNIDAD)

    class Meta:
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"
        unique_together = [["producto", "ingrediente"]]

    def __str__(self):
        return f"{self.cantidad} {self.unidad} de {self.ingrediente.nombre} para {self.producto.nombre}"

