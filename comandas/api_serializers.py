from rest_framework import serializers
from mesas.models import Mesa
from productos.models import Producto, Categoria
from comandas.models import Comanda, ComandaItem
from facturacion.models import Factura


class MesaSerializer(serializers.ModelSerializer):
    color_estado = serializers.CharField(read_only=True)

    class Meta:
        model = Mesa
        fields = "__all__"


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    margen_ganancia = serializers.FloatField(read_only=True)

    class Meta:
        model = Producto
        fields = "__all__"


class ComandaItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ComandaItem
        fields = "__all__"


class ComandaSerializer(serializers.ModelSerializer):
    mesero_nombre = serializers.CharField(source="mesero.get_full_name", read_only=True)
    mesa_numero = serializers.CharField(source="mesa.numero", read_only=True)
    items = ComandaItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_con_impuestos = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Comanda
        fields = "__all__"


class FacturaSerializer(serializers.ModelSerializer):
    comanda_codigo = serializers.CharField(source="comanda.codigo", read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Factura
        fields = "__all__"
