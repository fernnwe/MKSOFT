from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mesas.models import Mesa
from productos.models import Categoria, Producto
from inventario.models import Inventario
from meseros.models import Mesero

User = get_user_model()


class Command(BaseCommand):
    help = "Configuracion inicial completa del sistema"

    def handle(self, *args, **options):
        self.stdout.write("Configurando sistema...")

        users_data = [
            ("admin", "admin123", "admin", "admin@restaurante.com", "Administrador", ""),
            ("mesero1", "mesero123", "waiter", "juan@restaurante.com", "Juan", "Perez"),
            ("mesero2", "mesero123", "waiter", "maria@restaurante.com", "Maria", "Garcia"),
            ("mesero3", "mesero123", "waiter", "carlos@restaurante.com", "Carlos", "Lopez"),
            ("cocina", "cocina123", "kitchen", "cocina@restaurante.com", "Cocina", "General"),
            ("caja", "caja123", "cashier", "caja@restaurante.com", "Ana", "Martinez"),
        ]

        for username, password, role, email, first, last in users_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    role=role,
                    first_name=first,
                    last_name=last,
                )
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username} ({first} {last})"))
            else:
                user = User.objects.get(username=username)
                self.stdout.write(f"Usuario existente: {username}")

        mesero_users = User.objects.filter(role__in=["waiter", "cashier"])
        for user in mesero_users:
            if not hasattr(user, "perfil_mesero"):
                Mesero.objects.create(usuario=user, activo=True)
                self.stdout.write(self.style.SUCCESS(f"Perfil mesero creado para {user.get_full_name()}"))

        zonas = [
            ("1", "interior", 4), ("2", "interior", 4), ("3", "interior", 6),
            ("4", "interior", 2), ("5", "terraza", 4), ("6", "terraza", 4),
            ("7", "terraza", 8), ("8", "bar", 2), ("9", "bar", 2),
            ("10", "vip", 6), ("11", "vip", 8), ("12", "jardin", 4),
        ]
        for numero, zona, cap in zonas:
            Mesa.objects.get_or_create(numero=numero, defaults={"zona": zona, "capacidad": cap})
        self.stdout.write(self.style.SUCCESS(f"{len(zonas)} mesas configuradas"))

        categorias_data = [
            ("Entradas", "Platos para comenzar", "🥗", 1),
            ("Sopas", "Sopas y caldos", "🍲", 2),
            ("Carnes", "Platos de carne", "🥩", 3),
            ("Mariscos", "Platos de mariscos", "🦐", 4),
            ("Pastas", "Pastas italianas", "🍝", 5),
            ("Ensaladas", "Ensaladas frescas", "🥗", 6),
            ("Bebidas", "Bebidas alcoholicas y no alcoholicas", "🥤", 7),
            ("Cervezas", "Cervezas nacionales e importadas", "🍺", 8),
            ("Postres", "Postres deliciosos", "🍰", 9),
            ("Cafe", "Cafes y tés", "☕", 10),
        ]
        categorias = {}
        for nombre, desc, icono, orden in categorias_data:
            cat, _ = Categoria.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc, "icono": icono, "orden": orden})
            categorias[nombre] = cat
        self.stdout.write(self.style.SUCCESS(f"{len(categorias_data)} categorias configuradas"))

        productos_data = [
            ("ENT001", "Nachos con Guacamole", "plato", "Entradas", 85.00, 30.00),
            ("ENT002", "Quesadillas (3 pzas)", "plato", "Entradas", 75.00, 25.00),
            ("ENT003", "Sopa del Dia", "plato", "Sopas", 65.00, 20.00),
            ("ENT004", "Crema de Elote", "plato", "Sopas", 60.00, 18.00),
            ("CAR001", "Filete de Res", "plato", "Carnes", 220.00, 80.00),
            ("CAR002", "Pollo a la Parrilla", "plato", "Carnes", 165.00, 55.00),
            ("CAR003", "Costillas BBQ", "plato", "Carnes", 245.00, 90.00),
            ("CAR004", "Chuleta de Cerdo", "plato", "Carnes", 185.00, 65.00),
            ("MAR001", "Camarones al Ajillo", "plato", "Mariscos", 195.00, 75.00),
            ("MAR002", "Filete de Pescado", "plato", "Mariscos", 175.00, 65.00),
            ("MAR003", "Pulpo a la Parrilla", "plato", "Mariscos", 210.00, 85.00),
            ("PAS001", "Pasta Alfredo", "plato", "Pastas", 145.00, 45.00),
            ("PAS002", "Spaghetti Bolognesa", "plato", "Pastas", 135.00, 40.00),
            ("ENS001", "Ensalada Cesar", "plato", "Ensaladas", 110.00, 35.00),
            ("ENS002", "Ensalada Mixta", "plato", "Ensaladas", 95.00, 30.00),
            ("BEB001", "Agua Natural", "bebida", "Bebidas", 25.00, 5.00),
            ("BEB002", "Refresco", "bebida", "Bebidas", 35.00, 12.00),
            ("BEB003", "Jugo Natural", "bebida", "Bebidas", 45.00, 15.00),
            ("BEB004", "Agua Mineral", "bebida", "Bebidas", 35.00, 10.00),
            ("CER001", "Cerveza Nacional", "bebida", "Cervezas", 55.00, 22.00),
            ("CER002", "Cerveza Importada", "bebida", "Cervezas", 75.00, 35.00),
            ("POS001", "Pastel de Chocolate", "postre", "Postres", 85.00, 30.00),
            ("POS002", "Flan Napolitano", "postre", "Postres", 65.00, 22.00),
            ("POS003", "Helado (2 bolas)", "postre", "Postres", 55.00, 18.00),
            ("CAF001", "Cafe Americano", "bebida", "Cafe", 40.00, 10.00),
            ("CAF002", "Cappuccino", "bebida", "Cafe", 55.00, 15.00),
            ("CAF003", "Latte", "bebida", "Cafe", 60.00, 18.00),
        ]

        creados = 0
        for codigo, nombre, tipo, cat, precio, costo in productos_data:
            _, created = Producto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "tipo": tipo,
                    "categoria": categorias[cat],
                    "precio": precio,
                    "costo": costo,
                    "tiempo_preparacion": 15,
                }
            )
            if created:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f"{creados} nuevos productos configurados"))

        for prod in Producto.objects.all():
            Inventario.objects.get_or_create(
                producto=prod,
                defaults={
                    "cantidad_actual": 100,
                    "stock_minimo": 10,
                    "unidad": "unidad",
                    "costo_unitario": prod.costo,
                    "proveedor": "Proveedor General",
                }
            )
        self.stdout.write(self.style.SUCCESS("Inventario configurado"))

        self.stdout.write(self.style.SUCCESS("\n========================================"))
        self.stdout.write(self.style.SUCCESS("  Sistema configurado exitosamente!"))
        self.stdout.write(self.style.SUCCESS("========================================"))
        self.stdout.write("\nCredenciales:")
        self.stdout.write("  admin / admin123 - Administrador")
        self.stdout.write("  mesero1 / mesero123 - Juan Perez")
        self.stdout.write("  mesero2 / mesero123 - Maria Garcia")
        self.stdout.write("  mesero3 / mesero123 - Carlos Lopez")
        self.stdout.write("  cocina / cocina123 - Cocina General")
        self.stdout.write("  caja / caja123 - Ana Martinez")
