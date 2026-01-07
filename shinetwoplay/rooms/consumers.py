from channels.generic.websocket import AsyncWebsocketConsumer
import json

# In-memory state (NO DB needed)
rooms_state = {}
players_state = {}
games_state = {}

class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room = self.scope["url_route"]["kwargs"]["room"]
        
        # Extract username from query string
        query = self.scope["query_string"].decode()
        self.username = query.split("=")[1] if "=" in query else "Guest"

        # Create room state if not exists
        if self.room not in rooms_state:
            rooms_state[self.room] = {
                "owner": self.username,
                "selected_game": None,
                "round": 1,
                "status": "waiting"
            }

        # Create players state if not exists
        if self.room not in players_state:
            players_state[self.room] = {}

        # Add or update player
        players_state[self.room][self.username] = {
            "connected": True,
            "ready": False,
            "socket": self.channel_name
        }

        # Add to group
        await self.channel_layer.group_add(self.room, self.channel_name)

        await self.accept()

        # Notify others
        await self.broadcast("player_join", {
            "user": self.username,
            "players": list(players_state[self.room].keys())
        })

        # Send room state to this user
        await self.send_json("room_state", {
            "room": rooms_state[self.room],
            "players": players_state[self.room]
        })

    async def disconnect(self, close_code):
        # Soft disconnect
        players_state[self.room][self.username]["connected"] = False
        
        await self.broadcast("player_disconnect", {
            "user": self.username
        })

        await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data):
        """Handle all room events here."""
        data = json.loads(text_data)
        event = data.get("event")

        if event == "chat":
            await self.broadcast("chat", {"user": self.username, "msg": data["msg"]})

        elif event == "typing":
            await self.broadcast("typing", {"user": self.username})

        elif event == "ready":
            players_state[self.room][self.username]["ready"] = data["ready"]
            await self.broadcast("ready_state", {
                "user": self.username,
                "ready": data["ready"]
            })

        elif event == "select_game":
            rooms_state[self.room]["selected_game"] = data["game"]
            await self.broadcast("game_selected", {
                "game": data["game"],
                "by": self.username
            })

        elif event == "round_change":
            rooms_state[self.room]["round"] = data["round"]
            await self.broadcast("round_update", {
                "round": data["round"]
            })

        elif event == "start_game":
            await self.broadcast("start_game", {
                "game": rooms_state[self.room]["selected_game"],
                "room": self.room
            })

    async def broadcast(self, event, data):
        await self.channel_layer.group_send(
            self.room,
            {
                "type": "send_message",
                "event": event,
                "data": data
            }
        )

    async def send_message(self, event):
        """Send message to WebSocket."""
        await self.send(text_data=json.dumps({
            "event": event["event"],
            "data": event["data"]
        }))

    async def send_json(self, event, data):
        await self.send(text_data=json.dumps({
            "event": event,
            "data": data
        }))
