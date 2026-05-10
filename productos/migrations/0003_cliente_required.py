from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_records(apps, schema_editor):
    """Elimina registros huerfanos sin cliente asignado."""
    Categoria = apps.get_model('productos', 'Categoria')
    Producto = apps.get_model('productos', 'Producto')
    Categoria.objects.filter(cliente__isnull=True).delete()
    Producto.objects.filter(cliente__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0002_categoria_cliente_producto_cliente_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_orphan_records, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='categoria',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias', to='core.cliente'),
        ),
        migrations.AlterField(
            model_name='producto',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='productos', to='core.cliente'),
        ),
    ]
