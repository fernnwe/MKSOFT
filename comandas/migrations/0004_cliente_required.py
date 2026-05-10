from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_records(apps, schema_editor):
    """Elimina registros huerfanos sin cliente asignado."""
    Comanda = apps.get_model('comandas', 'Comanda')
    Comanda.objects.filter(cliente__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('comandas', '0003_comanda_cliente_alter_comanda_codigo_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_orphan_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='comanda',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comandas', to='core.cliente'),
        ),
    ]
