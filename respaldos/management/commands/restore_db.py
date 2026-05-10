import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Restaura la base de datos desde un respaldo"

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo",
            type=str,
            help="Ruta del archivo de respaldo",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forzar restauracion sin confirmar",
        )

    def handle(self, *args, **options):
        archivo = options["archivo"]

        if not os.path.exists(archivo):
            raise CommandError(f"El archivo de respaldo no existe: {archivo}")

        if not options["force"]:
            confirm = input("¡ADVERTENCIA! Esto sobrescribira la base de datos actual. ¿Continuar? (y/N): ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Operacion cancelada"))
                return

        db_path = settings.DATABASES["default"]["NAME"]

        if connection.vendor == "sqlite":
            with open(archivo, "rb") as src, open(db_path, "wb") as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    dst.write(chunk)

            self.stdout.write(self.style.SUCCESS(f"Base de datos restaurada desde: {archivo}"))
            self.stdout.write(self.style.SUCCESS("Reinicia el servidor para aplicar los cambios"))
        else:
            from django.core.management import call_command
            with open(archivo, "r") as f:
                call_command("loaddata", f.name)
            self.stdout.write(self.style.SUCCESS(f"Base de datos restaurada desde JSON: {archivo}"))
