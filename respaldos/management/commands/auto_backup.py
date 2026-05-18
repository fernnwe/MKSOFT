import os
import uuid
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.core.management import call_command


class Command(BaseCommand):
    help = "Crea respaldo automatico de la base de datos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Dias a mantener los respaldos (default: 30)",
        )

    def handle(self, *args, **options):
        retention_days = options["retention_days"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        backup_dir = os.path.join(settings.MEDIA_ROOT, "respaldos")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"auto_backup_{timestamp}_{unique_id}.sqlite3")

        self.stdout.write(f"Creando respaldo automatico...")

        if connection.vendor == "sqlite":
            db_path = settings.DATABASES["default"]["NAME"]

            if not os.path.exists(db_path):
                self.stderr.write(self.style.ERROR(f"Archivo de base de datos no encontrado: {db_path}"))
                return

            with open(db_path, "rb") as src, open(backup_path, "wb") as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    dst.write(chunk)
        else:
            with open(backup_path, "w") as f:
                call_command("dumpdata", indent=2, stdout=f)

        file_size = os.path.getsize(backup_path)
        size_mb = file_size / (1024 * 1024)

        with open(backup_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        self.stdout.write(self.style.SUCCESS(f"Respaldo automatico creado ({size_mb:.2f} MB)"))

        from respaldos.models import DatabaseBackup
        backup = DatabaseBackup.objects.create(
            nombre=f"Auto_Respaldo_{timestamp}",
            archivo=f"respaldos/auto_backup_{timestamp}_{unique_id}.sqlite3",
            creado_por=None,
            estado=DatabaseBackup.Estado.EXITOSO,
            tamaño_mb=round(size_mb, 2),
            hash_md5=file_hash,
            notas="Respaldo automatico",
        )

        from django.utils import timezone
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)

        old_backups = DatabaseBackup.objects.filter(
            fecha_creacion__lt=cutoff_date,
            creado_por__isnull=True,
            nombre__startswith="Auto_",
        )

        for old in old_backups:
            try:
                old.eliminar_archivo()
                old.delete()
                self.stdout.write(f"Respaldo antiguo eliminado: {old.nombre}")
            except Exception as e:
                self.stderr.write(f"Error al eliminar {old.nombre}: {e}")

        self.stdout.write(f"Limpieza completada. Eliminados {old_backups.count()} respaldos antiguos.")
