from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_records(apps, schema_editor):
    """Elimina registros huerfanos sin cliente asignado."""
    CajaApertura = apps.get_model('facturacion', 'CajaApertura')
    Factura = apps.get_model('facturacion', 'Factura')
    CajaApertura.objects.filter(cliente__isnull=True).delete()
    Factura.objects.filter(cliente__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0003_cajaapertura'),
    ]

    operations = [
        migrations.RunPython(cleanup_orphan_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cajaapertura',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cajas_apertura', to='core.cliente'),
        ),
        migrations.AlterField(
            model_name='factura',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='facturas', to='core.cliente'),
        ),
    ]
