def crear_datos_iniciales_cliente(cliente):
    from mesas.models import Mesa
    from productos.models import Categoria
    from inventario.models import Ingrediente, Inventario

    for num in range(1, 11):
        Mesa.objects.create(
            cliente=cliente,
            numero=str(num),
            zona=Mesa.Zona.INTERIOR if num <= 6 else Mesa.Zona.TERRAZA,
            capacidad=4 if num <= 6 else 2,
            estado=Mesa.Estado.LIBRE,
        )

    categorias_data = [
        ("Entradas", "Platos para compartir", "appetizer", 1),
        ("Platos Fuertes", "Platos principales", "main_dish", 2),
        ("Bebidas", "Bebidas frias y calientes", "local_drink", 3),
        ("Postres", "Dulces y postres", "cake", 4),
    ]
    for nombre, desc, icono, orden in categorias_data:
        Categoria.objects.create(
            cliente=cliente,
            nombre=nombre,
            descripcion=desc,
            icono=icono,
            orden=orden,
        )

    ingredientes_data = [
        ("Pollo", "Pechuga de pollo fresca", "Carnes", Ingrediente.Unidad.KILO, 5, 45),
        ("Carne de Res", "Carne de res para platillos", "Carnes", Ingrediente.Unidad.KILO, 5, 120),
        ("Arroz", "Arroz blanco", "Granos", Ingrediente.Unidad.KILO, 10, 25),
        ("Frijoles", "Frijoles negros", "Granos", Ingrediente.Unidad.KILO, 10, 30),
        ("Tortillas", "Tortillas de maiz", "Basicos", Ingrediente.Unidad.PIEZA, 50, 2),
        ("Aceite", "Aceite vegetal", "Basicos", Ingrediente.Unidad.LITRO, 5, 45),
        ("Sal", "Sal de mesa", "Basicos", Ingrediente.Unidad.KILO, 10, 15),
        ("Cebolla", "Cebolla blanca", "Verduras", Ingrediente.Unidad.KILO, 5, 20),
        ("Tomate", "Tomate rojo", "Verduras", Ingrediente.Unidad.KILO, 5, 25),
        ("Chile", "Chile serrano", "Verduras", Ingrediente.Unidad.KILO, 3, 40),
        ("Lechuga", "Lechuga fresca", "Verduras", Ingrediente.Unidad.PIEZA, 10, 12),
        ("Queso", "Queso Oaxaca", "Lacteos", Ingrediente.Unidad.KILO, 3, 150),
        ("Crema", "Crema acida", "Lacteos", Ingrediente.Unidad.LITRO, 5, 55),
        ("Limones", "Limones frescos", "Frutas", Ingrediente.Unidad.KILO, 5, 30),
        ("Agua", "Agua purificada", "Bebidas", Ingrediente.Unidad.LITRO, 20, 5),
    ]
    for nombre, desc, cat, unidad, stock, costo in ingredientes_data:
        ing = Ingrediente.objects.create(
            cliente=cliente,
            nombre=nombre,
            descripcion=desc,
            categoria=cat,
            stock_minimo=stock,
        )
        Inventario.objects.create(
            ingrediente=ing,
            cantidad_actual=stock * 2,
            unidad=unidad,
            costo_unitario=costo,
        )
