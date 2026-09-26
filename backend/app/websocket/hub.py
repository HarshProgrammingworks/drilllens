import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionHub:
    def __init__(self) -> None:
        self.monitoring: dict[str, set[WebSocket]] = defaultdict(set)
        self.notifications: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def join_monitoring(self, well_key: str, socket: WebSocket) -> None:
        async with self.lock:
            self.monitoring[well_key].add(socket)

    async def leave_monitoring(self, well_key: str, socket: WebSocket) -> None:
        async with self.lock:
            self.monitoring[well_key].discard(socket)

    async def join_notifications(self, socket: WebSocket) -> None:
        async with self.lock:
            self.notifications.add(socket)

    async def leave_notifications(self, socket: WebSocket) -> None:
        async with self.lock:
            self.notifications.discard(socket)

    async def broadcast_monitoring(self, well_key: str, payload: dict) -> None:
        async with self.lock:
            sockets = list(self.monitoring.get(well_key, set()))
            sockets += list(self.monitoring.get("*", set()))
        dead = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                dead.append(socket)
        if dead:
            async with self.lock:
                for socket in dead:
                    self.monitoring[well_key].discard(socket)

    async def broadcast_notification(self, payload: dict) -> None:
        async with self.lock:
            sockets = list(self.notifications)
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                async with self.lock:
                    self.notifications.discard(socket)


hub = ConnectionHub()
