from django.db import models
from django.conf import settings


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    icono = models.CharField(max_length=50, blank=True, help_text="Emoji o clase de icono")
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class Tipo(models.TextChoices):
        PLATO = "plato", "Plato"
        BEBIDA = "bebida", "Bebida"
        POSTRE = "postre", "Postre"
        EXTRA = "extra", "Extra"

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PLATO)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, related_name="productos"
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    costo = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo de producción")
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    activo = models.BooleanField(default=True)
    disponible = models.BooleanField(default=True)
    tiempo_preparacion = models.PositiveIntegerField(help_text="Minutos estimados", default=15)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria__orden", "nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} - {settings.CURRENCY_SYMBOL}{self.precio}"

    @property
    def margen_ganancia(self):
        if self.costo > 0:
            return round(((self.precio - self.costo) / self.costo) * 100, 2)
        return 0
