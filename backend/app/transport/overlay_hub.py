import asyncio
from typing import Set

from fastapi import WebSocket


class OverlayHub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale = []
        async with self._lock:
            clients = list(self._clients)

        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                stale.append(client)

        if stale:
            async with self._lock:
                for client in stale:
                    self._clients.discard(client)


overlay_hub = OverlayHub()
