from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_records(apps, schema_editor):
    """Elimina registros huerfanos sin cliente asignado."""
    Mesa = apps.get_model('mesas', 'Mesa')
    Mesa.objects.filter(cliente__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mesas', '0002_mesa_cliente_alter_mesa_numero_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_orphan_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='mesa',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mesas', to='core.cliente'),
        ),
    ]
