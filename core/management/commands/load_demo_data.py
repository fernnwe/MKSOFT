from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mesas.models import Mesa
from productos.models import Categoria, Producto
from inventario.models import Inventario

User = get_user_model()


class Command(BaseCommand):
    help = "Carga datos de demostracion para el sistema"

    def handle(self, *args, **options):
        self.stdout.write("Cargando datos de demostracion...")

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@restaurante.com", "admin123", role=User.Role.ADMIN)
            self.stdout.write(self.style.SUCCESS("Admin creado: admin / admin123"))

        if not User.objects.filter(username="mesero1").exists():
            u1 = User.objects.create_user("mesero1", "mesero1@restaurante.com", "mesero123", role=User.Role.WAITER, first_name="Juan", last_name="Perez")
            self.stdout.write(self.style.SUCCESS("Mesero creado: mesero1 / mesero123"))

        if not User.objects.filter(username="mesero2").exists():
            u2 = User.objects.create_user("mesero2", "mesero2@restaurante.com", "mesero123", role=User.Role.WAITER, first_name="Maria", last_name="Garcia")
            self.stdout.write(self.style.SUCCESS("Mesero creado: mesero2 / mesero123"))

        if not User.objects.filter(username="cocina").exists():
            User.objects.create_user("cocina", "cocina@restaurante.com", "cocina123", role=User.Role.KITCHEN, first_name="Cocina", last_name="General")
            self.stdout.write(self.style.SUCCESS("Cocina creado: cocina / cocina123"))

        zonas = [
            ("M1", "interior", 4), ("M2", "interior", 4), ("M3", "interior", 6),
            ("M4", "interior", 2), ("M5", "terraza", 4), ("M6", "terraza", 4),
            ("M7", "terraza", 8), ("M8", "bar", 2), ("M9", "bar", 2),
            ("M10", "vip", 6), ("M11", "vip", 8), ("M12", "jardin", 4),
        ]
        for numero, zona, cap in zonas:
            Mesa.objects.get_or_create(numero=numero, defaults={"zona": zona, "capacidad": cap})
        self.stdout.write(self.style.SUCCESS(f"{len(zonas)} mesas creadas"))

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
        self.stdout.write(self.style.SUCCESS(f"{len(categorias_data)} categorias creadas"))

        productos_data = [
            ("ENT001", "Nachos con Guacamole", "entrada", "Entradas", 85.00, 30.00),
            ("ENT002", "Quesadillas (3 pzas)", "entrada", "Entradas", 75.00, 25.00),
            ("ENT003", "Sopa del Dia", "sopa", "Sopas", 65.00, 20.00),
            ("ENT004", "Crema de Elote", "sopa", "Sopas", 60.00, 18.00),
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

        for codigo, nombre, tipo, cat, precio, costo in productos_data:
            Producto.objects.get_or_create(
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
        self.stdout.write(self.style.SUCCESS(f"{len(productos_data)} productos creados"))

        for prod in Producto.objects.all():
            Inventario.objects.get_or_create(
                producto=prod,
                defaults={
                    "cantidad_actual": 100,
                    "stock_minimo": 10,
                    "unidad": "unidad" if prod.tipo != "bebida" else "unidad",
                    "costo_unitario": prod.costo,
                    "proveedor": "Proveedor General",
                }
            )
        self.stdout.write(self.style.SUCCESS("Inventario inicial creado"))

        self.stdout.write(self.style.SUCCESS("\nDatos de demostracion cargados exitosamente!"))
        self.stdout.write("\nCredenciales de prueba:")
        self.stdout.write("  Admin: admin / admin123")
        self.stdout.write("  Mesero 1: mesero1 / mesero123")
        self.stdout.write("  Mesero 2: mesero2 / mesero123")
        self.stdout.write("  Cocina: cocina / cocina123")
