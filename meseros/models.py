from django.db import models
from django.conf import settings


class Mesero(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_mesero",
        limit_choices_to={"role__in": ["waiter", "cashier"]},
    )
    codigo_pin = models.CharField(max_length=6, unique=True, blank=True)
    activo = models.BooleanField(default=True)
    comandas_atendidas = models.PositiveIntegerField(default=0)
    propinas_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mesero"
        verbose_name_plural = "Meseros"

    def __str__(self):
        return str(self.usuario)

    def save(self, *args, **kwargs):
        if not self.codigo_pin:
            import random
            while True:
                pin = str(random.randint(1000, 9999))
                if not Mesero.objects.filter(codigo_pin=pin).exists():
                    self.codigo_pin = pin
                    break
        super().save(*args, **kwargs)
