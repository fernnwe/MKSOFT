from django.db import models


class Mesa(models.Model):
    class Estado(models.TextChoices):
        LIBRE = "libre", "Libre"
        OCUPADA = "ocupada", "Ocupada"
        RESERVADA = "reservada", "Reservada"
        MANTENIMIENTO = "mantenimiento", "Mantenimiento"

    class Zona(models.TextChoices):
        INTERIOR = "interior", "Interior"
        TERRAZA = "terraza", "Terraza"
        BAR = "bar", "Bar"
        VIP = "vip", "VIP"
        JARDIN = "jardin", "Jardín"

    numero = models.CharField(max_length=10, unique=True)
    zona = models.CharField(max_length=20, choices=Zona.choices, default=Zona.INTERIOR)
    capacidad = models.PositiveIntegerField(help_text="Número de personas")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.LIBRE)
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"

    def __str__(self):
        return f"Mesa {self.numero} - {self.get_zona_display()}"

    @property
    def color_estado(self):
        colors = {
            self.Estado.LIBRE: "success",
            self.Estado.OCUPADA: "danger",
            self.Estado.RESERVADA: "warning",
            self.Estado.MANTENIMIENTO: "secondary",
        }
        return colors.get(self.estado, "secondary")
