from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from .models import Comanda


@receiver(post_save, sender=Comanda)
def deducir_inventario_al_cerrar(sender, instance, created, raw, **kwargs):
    if created or raw:
        return
    if instance.estado != "cerrada":
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        if old.estado == "cerrada":
            return
    except sender.DoesNotExist:
        return

    from comandas.models import ComandaItem
    from inventario.models import Receta, Inventario, MovimientoInventario

    items = ComandaItem.objects.filter(comanda=instance, cancelado=False).select_related("producto")
    for item in items:
        recetas = Receta.objects.filter(producto=item.producto).select_related("ingrediente")
        for receta in recetas:
            try:
                inventario = Inventario.objects.get(ingrediente=receta.ingrediente)
            except Inventario.DoesNotExist:
                continue

            cantidad_deducir = receta.cantidad * item.cantidad
            inventario.cantidad_actual -= cantidad_deducir
            inventario.save()

            MovimientoInventario.objects.create(
                inventario=inventario,
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad=cantidad_deducir,
                motivo=f"Venta: {item.producto.nombre} (Comanda {instance.codigo})",
                usuario=instance.mesero,
            )
