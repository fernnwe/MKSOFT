from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from meseros.models import Mesero

User = get_user_model()


class Command(BaseCommand):
    help = "Crea perfiles de mesero para usuarios existentes"

    def handle(self, *args, **options):
        for username in ["mesero1", "mesero2"]:
            user = User.objects.filter(username=username).first()
            if user and not hasattr(user, "perfil_mesero"):
                Mesero.objects.create(usuario=user, activo=True)
                self.stdout.write(self.style.SUCCESS(f"Perfil de mesero creado para {username}"))
            else:
                self.stdout.write(f"Usuario {username} no encontrado o ya tiene perfil")
