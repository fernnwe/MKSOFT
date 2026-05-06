from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/mesas/", consumers.MesaConsumer.as_asgi()),
    path("ws/comandas/", consumers.ComandaConsumer.as_asgi()),
    path("ws/cocina/", consumers.CocinaConsumer.as_asgi()),
]
