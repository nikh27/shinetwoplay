from channels.generic.websocket import AsyncWebsocketConsumer
import json

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(json.dumps({"message": "WebSocket connected"}))

    async def receive(self, text_data):
        await self.send(json.dumps({"you_sent": text_data}))
