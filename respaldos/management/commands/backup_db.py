import os
import uuid
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Crea un respaldo completo de la base de datos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Ruta de salida para el archivo de respaldo",
        )
        parser.add_argument(
            "--auto",
            action="store_true",
            help="Modo automatico (sin prompts)",
        )

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        if options["output"]:
            backup_path = options["output"]
        else:
            backup_dir = os.path.join(settings.MEDIA_ROOT, "respaldos")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}_{unique_id}.sqlite3")

        self.stdout.write(f"Creando respaldo de la base de datos...")

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
                from django.core.management import call_command
                call_command("dumpdata", indent=2, stdout=f)

        file_size = os.path.getsize(backup_path)
        size_mb = file_size / (1024 * 1024)

        with open(backup_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        if not options["output"]:
            from respaldos.models import DatabaseBackup
            DatabaseBackup.objects.create(
                nombre=f"Respaldo_Completo_{timestamp}",
                archivo=f"respaldos/backup_{timestamp}_{unique_id}.sqlite3",
                estado=DatabaseBackup.Estado.EXITOSO,
                tamaño_mb=round(size_mb, 2),
                hash_md5=file_hash,
                notas="Respaldo desde CLI",
            )

        self.stdout.write(self.style.SUCCESS(f"Respaldo creado exitosamente"))
        self.stdout.write(f"Ruta: {backup_path}")
        self.stdout.write(f"Tamaño: {size_mb:.2f} MB")
        self.stdout.write(f"Hash MD5: {file_hash}")
