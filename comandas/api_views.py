from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mesas.models import Mesa
from productos.models import Producto, Categoria
from comandas.models import Comanda, ComandaItem
from facturacion.models import Factura
from .api_serializers import (
    MesaSerializer,
    ProductoSerializer,
    CategoriaSerializer,
    ComandaSerializer,
    ComandaItemSerializer,
    FacturaSerializer,
)


class MesaViewSet(viewsets.ModelViewSet):
    serializer_class = MesaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Mesa.objects.all()
        estado = self.request.query_params.get("estado")
        zona = self.request.query_params.get("zona")
        if estado:
            qs = qs.filter(estado=estado)
        if zona:
            qs = qs.filter(zona=zona)
        return qs

    @action(detail=True, methods=["post"])
    def cambiar_estado(self, request, pk=None):
        mesa = self.get_object()
        nuevo_estado = request.data.get("estado")
        if nuevo_estado in dict(Mesa.Estado.choices):
            mesa.estado = nuevo_estado
            mesa.save()
            return Response({"estado": mesa.estado, "color": mesa.color_estado})
        return Response({"error": "Estado invalido"}, status=400)


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    queryset = Categoria.objects.filter(activo=True)


class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Producto.objects.filter(activo=True, disponible=True)
        tipo = self.request.query_params.get("tipo")
        categoria = self.request.query_params.get("categoria")
        if tipo:
            qs = qs.filter(tipo=tipo)
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        return qs


class ComandaViewSet(viewsets.ModelViewSet):
    serializer_class = ComandaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Comanda.objects.select_related("mesa", "mesero").prefetch_related("items")
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    @action(detail=True, methods=["post"])
    def agregar_item(self, request, pk=None):
        comanda = self.get_object()
        if comanda.estado != Comanda.Estado.ABIERTA:
            return Response({"error": "Comanda no esta abierta"}, status=400)
        producto = Producto.objects.get(pk=request.data.get("producto"))
        item = ComandaItem.objects.create(
            comanda=comanda,
            producto=producto,
            cantidad=int(request.data.get("cantidad", 1)),
            precio_unitario=producto.precio,
            notas=request.data.get("notas", ""),
        )
        return Response(ComandaItemSerializer(item).data, status=201)

    @action(detail=True, methods=["post"])
    def enviar_cocina(self, request, pk=None):
        comanda = self.get_object()
        comanda.estado = Comanda.Estado.EN_COCINA
        comanda.save()
        return Response({"estado": comanda.estado})

    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        from django.utils import timezone
        comanda = self.get_object()
        comanda.estado = Comanda.Estado.CERRADA
        comanda.fecha_cierre = timezone.now()
        comanda.save()
        return Response({"estado": comanda.estado})


class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Factura.objects.select_related("comanda")
