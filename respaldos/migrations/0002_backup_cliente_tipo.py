from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_configrestaurante_cliente_required'),
        ('respaldos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='databasebackup',
            name='cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='respaldos', to='core.cliente'),
        ),
        migrations.AddField(
            model_name='databasebackup',
            name='tipo',
            field=models.CharField(choices=[('completo', 'Completo (Superadmin)'), ('tenant', 'Por Restaurante')], default='tenant', max_length=20),
        ),
    ]
