from collections import defaultdict

from fastapi import WebSocket


class RealtimeManager:
    """Single-process demo manager; production fan-out is backed by Redis pub/sub."""

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        self.connections[user_id].discard(websocket)
        if not self.connections[user_id]:
            self.connections.pop(user_id, None)

    async def send(self, user_id: str, event: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in self.connections.get(user_id, set()):
            try:
                await websocket.send_json(event)
            except OSError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(user_id, websocket)

    async def send_many(self, user_ids: set[str], event: dict) -> None:
        for user_id in user_ids:
            await self.send(user_id, event)


realtime_manager = RealtimeManager()
