import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class MesaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("mesas", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("mesas", self.channel_name)

    async def mesa_update(self, event):
        await self.send(text_data=json.dumps(event))


class ComandaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("comandas", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("comandas", self.channel_name)

    async def comanda_new(self, event):
        await self.send(text_data=json.dumps(event))

    async def comanda_update(self, event):
        await self.send(text_data=json.dumps(event))


class CocinaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("cocina", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("cocina", self.channel_name)

    async def comanda_cocina(self, event):
        await self.send(text_data=json.dumps(event))
