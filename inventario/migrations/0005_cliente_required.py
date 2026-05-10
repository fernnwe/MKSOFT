from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_records(apps, schema_editor):
    """Elimina registros huerfanos sin cliente asignado."""
    Ingrediente = apps.get_model('inventario', 'Ingrediente')
    Compra = apps.get_model('inventario', 'Compra')
    CuentaPorPagar = apps.get_model('inventario', 'CuentaPorPagar')
    Inventario = apps.get_model('inventario', 'Inventario')
    MovimientoInventario = apps.get_model('inventario', 'MovimientoInventario')
    CompraItem = apps.get_model('inventario', 'CompraItem')

    Ingrediente.objects.filter(cliente__isnull=True).delete()
    Compra.objects.filter(cliente__isnull=True).delete()
    CuentaPorPagar.objects.filter(cliente__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0004_ingrediente_activo'),
    ]

    operations = [
        migrations.RunPython(cleanup_orphan_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ingrediente',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredientes', to='core.cliente'),
        ),
        migrations.AlterField(
            model_name='compra',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compras', to='core.cliente'),
        ),
        migrations.AlterField(
            model_name='cuentaporpagar',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cuentas_por_pagar', to='core.cliente'),
        ),
    ]
